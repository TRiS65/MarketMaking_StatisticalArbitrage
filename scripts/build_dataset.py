#!/usr/bin/env python3
"""Build one-minute research data from WRDS TAQ quote/trade extracts.

The raw TAQ files are large gzipped CSVs.  This script uses DuckDB to scan and
aggregate them directly into compact Parquet files, then uses pandas on the
small minute-level data to create the final research panel.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
OUTPUT = ROOT / "output"

ETF = "XLK"
CONSTITUENTS = ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "CSCO"]
SYMBOLS = [ETF] + CONSTITUENTS
MAX_MINUTE_SPREAD_BPS = 100.0
MAX_ROLLING_PRICE_DEVIATION_BPS = 500.0

RAW_NAME_MAP = {
    "qvwbapngjmj79pdm.csv.gz": "quotes_2026_01.csv.gz",
    "fe8opojie0btzuiq.csv.gz": "quotes_2026_02.csv.gz",
    "a7or8sbvdkx8x817.csv.gz": "quotes_2026_03.csv.gz",
    "ckjq5hqw80a1bjen.csv.gz": "trades_2026_01.csv.gz",
    "ikb9cztcv8gzv7gc.csv.gz": "trades_2026_02.csv.gz",
    "fqbe063ciznxudqg.csv.gz": "trades_2026_03.csv.gz",
}


def ensure_dirs() -> None:
    for path in [RAW, PROCESSED, OUTPUT, OUTPUT / "tables", OUTPUT / "figures"]:
        path.mkdir(parents=True, exist_ok=True)


def normalize_raw_names() -> None:
    """Make raw file names meaningful and idempotent."""
    ensure_dirs()
    for old, new in RAW_NAME_MAP.items():
        old_path = DATA / old
        new_path = RAW / new
        if new_path.exists():
            continue
        if old_path.exists():
            old_path.rename(new_path)


def duckdb_connection() -> duckdb.DuckDBPyConnection:
    temp_dir = OUTPUT / "duckdb_tmp"
    temp_dir.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute(f"PRAGMA threads={max(2, min(8, os.cpu_count() or 4))}")
    con.execute("PRAGMA memory_limit='8GB'")
    con.execute(f"PRAGMA temp_directory='{temp_dir.as_posix()}'")
    return con


def quote_sql(infile: Path) -> str:
    symbols = ", ".join(f"'{s}'" for s in SYMBOLS)
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
          SYM_ROOT IN ({symbols})
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
    ) TO '{{outfile}}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """


def trade_sql(infile: Path) -> str:
    symbols = ", ".join(f"'{s}'" for s in SYMBOLS)
    return f"""
    COPY (
      WITH clean AS (
        SELECT
          SYM_ROOT::VARCHAR AS symbol,
          date_trunc('minute', try_cast(DATE || ' ' || TIME_M AS TIMESTAMP_NS)) AS minute,
          try_cast(DATE || ' ' || TIME_M AS TIMESTAMP_NS) AS ts,
          PRICE::DOUBLE AS price,
          SIZE::DOUBLE AS size
        FROM read_csv('{infile.as_posix()}', header=true, auto_detect=true, union_by_name=true, all_varchar=true)
        WHERE
          SYM_ROOT IN ({symbols})
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
    ) TO '{{outfile}}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """


def aggregate_raw(force: bool) -> None:
    con = duckdb_connection()
    jobs = []
    for infile in sorted(RAW.glob("quotes_2026_*.csv.gz")):
        month = infile.stem.split("_")[-1].replace(".csv", "")
        jobs.append((infile, PROCESSED / f"minute_quotes_2026_{month}.parquet", quote_sql(infile)))
    for infile in sorted(RAW.glob("trades_2026_*.csv.gz")):
        month = infile.stem.split("_")[-1].replace(".csv", "")
        jobs.append((infile, PROCESSED / f"minute_trades_2026_{month}.parquet", trade_sql(infile)))

    for infile, outfile, sql_template in jobs:
        if outfile.exists() and not force:
            print(f"[skip] {outfile.relative_to(ROOT)} exists")
            continue
        print(f"[build] {infile.relative_to(ROOT)} -> {outfile.relative_to(ROOT)}")
        if outfile.exists():
            outfile.unlink()
        con.execute(sql_template.format(outfile=outfile.as_posix()))


def load_holdings() -> pd.DataFrame:
    holdings_file = DATA / "0422_holdings-daily-us-en-xlk.xlsx"
    raw = pd.read_excel(holdings_file, sheet_name="holdings", header=None)
    header_idx = raw.index[raw.iloc[:, 0].eq("Name")][0]
    df = pd.read_excel(holdings_file, sheet_name="holdings", header=header_idx)
    df = df.rename(columns=str.lower)
    df = df.rename(columns={"ticker": "symbol", "weight": "official_weight_pct"})
    df = df[df["symbol"].isin(CONSTITUENTS)].copy()
    df["official_weight"] = df["official_weight_pct"] / 100.0
    coverage = df["official_weight"].sum()
    df["basket_weight"] = df["official_weight"] / coverage
    df = df[["symbol", "name", "official_weight_pct", "official_weight", "basket_weight"]]
    df = df.sort_values("basket_weight", ascending=False).reset_index(drop=True)
    df.to_csv(OUTPUT / "tables" / "selected_xlk_holdings.csv", index=False)
    print(f"[holdings] selected coverage of XLK file: {coverage:.2%}")
    return df


def build_panel(force: bool) -> None:
    panel_file = PROCESSED / "research_panel.parquet"
    if panel_file.exists() and not force:
        print(f"[skip] {panel_file.relative_to(ROOT)} exists")
        return

    quote_files = sorted(PROCESSED.glob("minute_quotes_2026_*.parquet"))
    trade_files = sorted(PROCESSED.glob("minute_trades_2026_*.parquet"))
    if not quote_files or not trade_files:
        raise FileNotFoundError("Minute quote/trade Parquet files are missing. Run raw aggregation first.")

    quotes = pd.concat([pd.read_parquet(f) for f in quote_files], ignore_index=True)
    trades = pd.concat([pd.read_parquet(f) for f in trade_files], ignore_index=True)
    quotes["minute"] = pd.to_datetime(quotes["minute"])
    trades["minute"] = pd.to_datetime(trades["minute"])

    q = quotes.sort_values(["symbol", "minute"]).copy()
    q["mid"] = (q["bid"] + q["ask"]) / 2.0
    q["spread"] = q["ask"] - q["bid"]
    q["spread_bps"] = 1e4 * q["spread"] / q["mid"]
    q["imbalance"] = (q["bidsiz"] - q["asksiz"]) / (q["bidsiz"] + q["asksiz"])
    q["microprice"] = (q["ask"] * q["bidsiz"] + q["bid"] * q["asksiz"]) / (q["bidsiz"] + q["asksiz"])
    q["micro_gap_bps"] = 1e4 * (q["microprice"] - q["mid"]) / q["mid"]
    q["date"] = q["minute"].dt.date.astype(str)
    before = len(q)
    q = q[(q["spread_bps"] > 0) & (q["spread_bps"] <= MAX_MINUTE_SPREAD_BPS)].copy()
    print(f"[quotes] dropped {before - len(q):,} minute quotes with spread > {MAX_MINUTE_SPREAD_BPS:.0f} bps")
    before = len(q)
    q = q.sort_values(["symbol", "minute"])
    rolling_median = q.groupby("symbol")["mid"].transform(
        lambda s: s.rolling(61, min_periods=10, center=True).median()
    )
    deviation_bps = 1e4 * (np.log(q["mid"]) - np.log(rolling_median)).abs()
    q = q[(rolling_median.isna()) | (deviation_bps <= MAX_ROLLING_PRICE_DEVIATION_BPS)].copy()
    print(
        f"[quotes] dropped {before - len(q):,} minute quotes with price deviation > "
        f"{MAX_ROLLING_PRICE_DEVIATION_BPS:.0f} bps from rolling median"
    )

    panel = q.merge(trades, on=["symbol", "minute"], how="left")
    panel["volume"] = panel["volume"].fillna(0.0)
    panel["trade_count"] = panel["trade_count"].fillna(0).astype(int)
    panel = panel.sort_values(["symbol", "minute"])
    for col in ["mid", "microprice", "last_trade_price"]:
        panel[f"log_{col}"] = np.log(panel[col].where(panel[col] > 0))
        panel[f"ret_{col}"] = panel.groupby("symbol")[f"log_{col}"].diff()

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Rebuild existing outputs.")
    args = parser.parse_args()

    normalize_raw_names()
    aggregate_raw(force=args.force)
    load_holdings()
    build_panel(force=args.force)


if __name__ == "__main__":
    main()
