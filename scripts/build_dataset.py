#!/usr/bin/env python3
"""Build one-minute research data from WRDS TAQ quote/trade extracts.

Default configuration is the final project dataset:

    data/finaldata/*.csv.gz
    2025-05-01 <= DATE < 2026-05-01
    XLK + top 20 XLK holdings from data/0501_holdings-daily-us-en-xlk.xlsx

The raw TAQ files are too large for pandas.  DuckDB scans the gzipped CSVs,
filters to the requested universe and regular hours, and writes compact minute
parquet files.  Pandas is used only after aggregation.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROCESSED = DATA / "processed"
OUTPUT = ROOT / "output"
ETF = "XLK"
MINUTES_PER_DAY = 390
MAX_MINUTE_SPREAD_BPS = 100.0
MAX_ROLLING_PRICE_DEVIATION_BPS = 500.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build minute panel for XLK TAQ study")
    parser.add_argument("--raw-dir", type=Path, default=DATA / "finaldata")
    parser.add_argument("--holdings", type=Path, default=DATA / "0501_holdings-daily-us-en-xlk.xlsx")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--start", type=str, default="2025-05-01")
    parser.add_argument("--end", type=str, default="2026-05-01")
    parser.add_argument("--train-end", type=str, default="2026-02-01")
    parser.add_argument("--validation-end", type=str, default="2026-03-01")
    parser.add_argument("--test-end", type=str, default="2026-05-01")
    parser.add_argument("--force", action="store_true", help="Rebuild existing minute parquet and panel")
    return parser.parse_args()


def ensure_dirs() -> None:
    for path in [PROCESSED, OUTPUT, OUTPUT / "tables", OUTPUT / "figures", OUTPUT / "duckdb_tmp"]:
        path.mkdir(parents=True, exist_ok=True)


def load_holdings(holdings_file: Path, top_n: int) -> pd.DataFrame:
    raw = pd.read_excel(holdings_file, sheet_name="holdings", header=None)
    header_idx = raw.index[raw.iloc[:, 0].eq("Name")][0]
    df = pd.read_excel(holdings_file, sheet_name="holdings", header=header_idx)
    df = df.rename(columns=str.lower).rename(columns={"ticker": "symbol", "weight": "official_weight_pct"})
    df = df[df["symbol"].notna()].copy()
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    df = df[df["symbol"] != ETF].head(top_n).copy()
    df["official_weight"] = df["official_weight_pct"].astype(float) / 100.0
    coverage = float(df["official_weight"].sum())
    df["basket_weight"] = df["official_weight"] / coverage
    out = df[["symbol", "name", "official_weight_pct", "official_weight", "basket_weight"]].reset_index(drop=True)
    out.to_csv(OUTPUT / "tables" / "selected_xlk_holdings.csv", index=False)
    print(f"[holdings] top {top_n} coverage of XLK file: {coverage:.2%}")
    return out


def find_raw_files(raw_dir: Path) -> tuple[Path, Path]:
    gz_files = sorted(raw_dir.glob("*.csv.gz"))
    if not gz_files:
        raise FileNotFoundError(f"No gzipped CSV files found in {raw_dir}")
    quote_file = None
    trade_file = None
    for path in gz_files:
        with os.popen(f"gzip -cd {path.as_posix()} | head -1") as fh:
            header = fh.read().strip().upper()
        if "BID" in header and "ASK" in header and "QU_SEQNUM" in header:
            quote_file = path
        elif "PRICE" in header and "SIZE" in header and "TR_SEQNUM" in header:
            trade_file = path
    if quote_file is None or trade_file is None:
        raise FileNotFoundError(f"Could not identify quote/trade files in {raw_dir}")
    print(f"[raw] quotes={quote_file.relative_to(ROOT)}")
    print(f"[raw] trades={trade_file.relative_to(ROOT)}")
    return quote_file, trade_file


def duckdb_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"PRAGMA threads={max(2, min(8, os.cpu_count() or 4))}")
    con.execute("PRAGMA memory_limit='8GB'")
    con.execute(f"PRAGMA temp_directory='{(OUTPUT / 'duckdb_tmp').as_posix()}'")
    return con


def quote_sql(infile: Path, symbols: list[str], start: str, end: str, outfile: Path) -> str:
    symbol_sql = ", ".join(f"'{s}'" for s in symbols)
    return f"""
    COPY (
      WITH clean AS (
        SELECT
          SYM_ROOT::VARCHAR AS symbol,
          date_trunc('minute', try_cast(DATE || ' ' || TIME_M AS TIMESTAMP_NS)) AS minute,
          try_cast(DATE || ' ' || TIME_M AS TIMESTAMP_NS) AS ts,
          try_cast(BID AS DOUBLE) AS bid,
          try_cast(BIDSIZ AS DOUBLE) AS bidsiz,
          try_cast(ASK AS DOUBLE) AS ask,
          try_cast(ASKSIZ AS DOUBLE) AS asksiz,
          try_cast(QU_SEQNUM AS UBIGINT) AS seqnum
        FROM read_csv('{infile.as_posix()}', header=true, auto_detect=true, union_by_name=true, all_varchar=true)
        WHERE
          DATE >= '{start}'
          AND DATE < '{end}'
          AND SYM_ROOT IN ({symbol_sql})
          AND try_cast(TIME_M AS TIME) >= TIME '09:30:00'
          AND try_cast(TIME_M AS TIME) < TIME '16:00:00'
          AND (QU_CANCEL IS NULL OR QU_CANCEL = '')
          AND try_cast(BID AS DOUBLE) > 0
          AND try_cast(ASK AS DOUBLE) > 0
          AND try_cast(ASK AS DOUBLE) > try_cast(BID AS DOUBLE)
          AND try_cast(BIDSIZ AS DOUBLE) > 0
          AND try_cast(ASKSIZ AS DOUBLE) > 0
      )
      SELECT
        symbol,
        minute,
        arg_max(bid, ts) AS bid,
        arg_max(ask, ts) AS ask,
        arg_max(bidsiz, ts) AS bidsiz,
        arg_max(asksiz, ts) AS asksiz,
        count(*) AS quote_updates
      FROM clean
      GROUP BY symbol, minute
      ORDER BY symbol, minute
    ) TO '{outfile.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """


def trade_sql(infile: Path, symbols: list[str], start: str, end: str, outfile: Path) -> str:
    symbol_sql = ", ".join(f"'{s}'" for s in symbols)
    return f"""
    COPY (
      WITH clean AS (
        SELECT
          SYM_ROOT::VARCHAR AS symbol,
          date_trunc('minute', try_cast(DATE || ' ' || TIME_M AS TIMESTAMP_NS)) AS minute,
          try_cast(DATE || ' ' || TIME_M AS TIMESTAMP_NS) AS ts,
          try_cast(PRICE AS DOUBLE) AS price,
          try_cast(SIZE AS DOUBLE) AS size
        FROM read_csv('{infile.as_posix()}', header=true, auto_detect=true, union_by_name=true, all_varchar=true)
        WHERE
          DATE >= '{start}'
          AND DATE < '{end}'
          AND SYM_ROOT IN ({symbol_sql})
          AND try_cast(TIME_M AS TIME) >= TIME '09:30:00'
          AND try_cast(TIME_M AS TIME) < TIME '16:00:00'
          AND TR_CORR = '00'
          AND try_cast(PRICE AS DOUBLE) > 0
          AND try_cast(SIZE AS DOUBLE) > 0
      )
      SELECT
        symbol,
        minute,
        arg_max(price, ts) AS last_trade_price,
        sum(size) AS volume,
        count(*) AS trade_count
      FROM clean
      GROUP BY symbol, minute
      ORDER BY symbol, minute
    ) TO '{outfile.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """


def aggregate_raw(
    quote_file: Path,
    trade_file: Path,
    symbols: list[str],
    start: str,
    end: str,
    force: bool,
) -> tuple[Path, Path]:
    tag = raw_dir_tag(quote_file.parent)
    quote_out = PROCESSED / f"minute_quotes_{tag}.parquet"
    trade_out = PROCESSED / f"minute_trades_{tag}.parquet"
    con = duckdb_connection()
    if force or not quote_out.exists():
        if quote_out.exists():
            quote_out.unlink()
        print(f"[build] {quote_file.relative_to(ROOT)} -> {quote_out.relative_to(ROOT)}")
        con.execute(quote_sql(quote_file, symbols, start, end, quote_out))
    else:
        print(f"[skip] {quote_out.relative_to(ROOT)} exists")
    if force or not trade_out.exists():
        if trade_out.exists():
            trade_out.unlink()
        print(f"[build] {trade_file.relative_to(ROOT)} -> {trade_out.relative_to(ROOT)}")
        con.execute(trade_sql(trade_file, symbols, start, end, trade_out))
    else:
        print(f"[skip] {trade_out.relative_to(ROOT)} exists")
    return quote_out, trade_out


def raw_dir_tag(raw_dir: Path) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in raw_dir.name).strip("_") or "raw"


def metadata_mismatch(args: argparse.Namespace) -> bool:
    path = PROCESSED / "dataset_metadata.json"
    if not path.exists():
        return False
    try:
        old = json.loads(path.read_text())
    except Exception:
        return True
    return any(
        [
            old.get("dataset") != args.raw_dir.name,
            old.get("raw_dir") != args.raw_dir.as_posix(),
            old.get("start") != args.start,
            old.get("end") != args.end,
            old.get("train_end") != args.train_end,
            old.get("validation_end") != args.validation_end,
            old.get("test_end") != args.test_end,
        ]
    )


def build_panel(quote_file: Path, trade_file: Path, symbols: list[str], force: bool) -> None:
    panel_file = PROCESSED / "research_panel.parquet"
    if panel_file.exists() and not force:
        print(f"[skip] {panel_file.relative_to(ROOT)} exists")
        return

    quotes = pd.read_parquet(quote_file)
    trades = pd.read_parquet(trade_file)
    quotes["minute"] = pd.to_datetime(quotes["minute"])
    trades["minute"] = pd.to_datetime(trades["minute"])

    q = quotes[quotes["symbol"].isin(symbols)].sort_values(["symbol", "minute"]).copy()
    q["mid"] = (q["bid"] + q["ask"]) / 2.0
    q["spread"] = q["ask"] - q["bid"]
    q["spread_bps"] = 1e4 * q["spread"] / q["mid"]
    q["imbalance"] = (q["bidsiz"] - q["asksiz"]) / (q["bidsiz"] + q["asksiz"])
    q["microprice"] = (q["ask"] * q["bidsiz"] + q["bid"] * q["asksiz"]) / (q["bidsiz"] + q["asksiz"])
    q["micro_gap_bps"] = 1e4 * (q["microprice"] - q["mid"]) / q["mid"]
    before = len(q)
    q = q[(q["spread_bps"] > 0) & (q["spread_bps"] <= MAX_MINUTE_SPREAD_BPS)].copy()
    print(f"[quotes] dropped {before - len(q):,} minute quotes with spread > {MAX_MINUTE_SPREAD_BPS:.0f} bps")

    before = len(q)
    rolling_median = q.groupby("symbol")["mid"].transform(lambda s: s.rolling(61, min_periods=10, center=True).median())
    deviation_bps = 1e4 * (np.log(q["mid"]) - np.log(rolling_median)).abs()
    q = q[(rolling_median.isna()) | (deviation_bps <= MAX_ROLLING_PRICE_DEVIATION_BPS)].copy()
    print(f"[quotes] dropped {before - len(q):,} minute quotes with price deviation > {MAX_ROLLING_PRICE_DEVIATION_BPS:.0f} bps")

    panel = q.merge(trades, on=["symbol", "minute"], how="left")
    panel["volume"] = panel["volume"].fillna(0.0)
    panel["trade_count"] = panel["trade_count"].fillna(0).astype(int)
    panel = panel.sort_values(["symbol", "minute"])
    for col in ["mid", "microprice", "last_trade_price"]:
        panel[f"log_{col}"] = np.log(panel[col].where(panel[col] > 0))
        panel[f"ret_{col}"] = panel.groupby("symbol")[f"log_{col}"].diff()

    # Keep the distributable processed panel below GitHub's single-file limit.
    # The raw TAQ inputs remain the source of truth; float32 precision is ample
    # for one-minute bps-level diagnostics and keeps the final panel laptop-safe.
    for col in panel.select_dtypes(include=["float64"]).columns:
        panel[col] = panel[col].astype("float32")
    for col in ["quote_updates", "trade_count"]:
        if col in panel:
            panel[col] = panel[col].fillna(0).astype("int32")
    panel["symbol"] = panel["symbol"].astype("category")
    panel.to_parquet(panel_file, index=False)
    diag = (
        panel.groupby("symbol")
        .agg(
            start=("minute", "min"),
            end=("minute", "max"),
            minutes=("minute", "count"),
            avg_spread_bps=("spread_bps", "mean"),
            median_spread_bps=("spread_bps", "median"),
            avg_volume=("volume", "mean"),
            quote_updates=("quote_updates", "sum"),
            trade_count=("trade_count", "sum"),
        )
        .reset_index()
    )
    diag.to_csv(OUTPUT / "tables" / "minute_data_diagnostics.csv", index=False)
    print(f"[panel] wrote {panel_file.relative_to(ROOT)} with {len(panel):,} rows")


def write_metadata(args: argparse.Namespace, symbols: list[str], quote_file: Path, trade_file: Path) -> None:
    panel_symbols = symbols
    panel_file = PROCESSED / "research_panel.parquet"
    if panel_file.exists():
        available = set(pd.read_parquet(panel_file, columns=["symbol"])["symbol"].astype(str).unique())
        panel_symbols = [s for s in symbols if s in available]
        holdings_path = OUTPUT / "tables" / "selected_xlk_holdings.csv"
        if holdings_path.exists():
            holdings = pd.read_csv(holdings_path)
            holdings["used_in_clean_panel"] = holdings["symbol"].astype(str).isin(available)
            holdings.to_csv(holdings_path, index=False)
    meta = {
        "dataset": args.raw_dir.name,
        "raw_dir": args.raw_dir.as_posix(),
        "quote_file": quote_file.as_posix(),
        "trade_file": trade_file.as_posix(),
        "etf": ETF,
        "requested_symbols": symbols,
        "symbols": panel_symbols,
        "constituents": [s for s in panel_symbols if s != ETF],
        "dropped_requested_symbols": [s for s in symbols if s not in panel_symbols],
        "start": args.start,
        "end": args.end,
        "train_end": args.train_end,
        "validation_end": args.validation_end,
        "test_end": args.test_end,
        "minute_frequency": "1min regular trading hours",
    }
    (PROCESSED / "dataset_metadata.json").write_text(json.dumps(meta, indent=2))


def main() -> None:
    args = parse_args()
    ensure_dirs()
    dataset_changed = metadata_mismatch(args)
    if dataset_changed and not args.force:
        print("[metadata] existing processed panel belongs to a different raw window; rebuilding affected outputs")
    holdings = load_holdings(args.holdings, args.top_n)
    symbols = [ETF] + holdings["symbol"].tolist()
    quote_file, trade_file = find_raw_files(args.raw_dir)
    quote_out, trade_out = aggregate_raw(quote_file, trade_file, symbols, args.start, args.end, args.force or dataset_changed)
    build_panel(quote_out, trade_out, symbols, args.force or dataset_changed)
    write_metadata(args, symbols, quote_file, trade_file)


if __name__ == "__main__":
    main()
