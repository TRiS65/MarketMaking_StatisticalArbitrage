#!/usr/bin/env python3
"""Empirical execution-cost calibration for the XLK/stat-arb project.

This script replaces hard-coded 0.25/0.50-spread assumptions with quantities
estimated from the cleaned one-minute TAQ panel:

1. Quote-boundary taker cost: actual contemporaneous bid/ask for each symbol.
2. Latency taker cost: bid/ask after 1/2/5 minutes, not a spread multiplier.
3. Last-trade effective/realized-spread proxy: uses minute last trade relative to
   midquote and future midpoint markouts.
4. Passive-touch fill proxy: a buy limit at bid fills if subsequent last-trade
   price trades at/below the entry bid; a sell limit at ask fills if it trades
   at/above the entry ask. Fill probability and adverse-selection markout are
   estimated by symbol, time bucket, spread bucket, and imbalance bucket.
5. Capacity/impact diagnostic: compares proposed notional to minute dollar volume
   and estimates a square-root impact proxy.

It is intentionally conservative about what minute bars can identify. It does
not claim true queue position or depth-aware fills; it reports these as proxies.

Usage from repo root:
    python3 scripts/run_empirical_execution_model.py --root .

Outputs:
    output/tables/empirical_symbol_costs.csv
    output/tables/empirical_taker_latency_costs.csv
    output/tables/empirical_passive_fill_model.csv
    output/tables/empirical_capacity_curve.csv
    output/empirical_execution_model.md
"""
from __future__ import annotations

import argparse
from pathlib import Path
import math
import numpy as np
import pandas as pd


def _find_col(df: pd.DataFrame, choices: list[str]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for c in choices:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def load_panel(root: Path) -> pd.DataFrame:
    path = root / "data" / "processed" / "research_panel.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Build data first.")
    df = pd.read_parquet(path)
    df.columns = [str(c) for c in df.columns]

    # Accept either long format (symbol/minute rows) or a wide panel.
    sym_col = _find_col(df, ["symbol", "sym", "ticker"])
    time_col = _find_col(df, ["minute", "ts", "timestamp", "datetime", "time"])
    if sym_col and time_col:
        out = df.rename(columns={sym_col: "symbol", time_col: "minute"}).copy()
        out["minute"] = pd.to_datetime(out["minute"])
        for need in ["bid", "ask", "mid"]:
            if need not in out.columns:
                # Try common aliases.
                alias = _find_col(out, [need, f"{need}_price", f"best_{need}"])
                if alias:
                    out = out.rename(columns={alias: need})
        if "mid" not in out.columns and {"bid", "ask"}.issubset(out.columns):
            out["mid"] = 0.5 * (out["bid"].astype(float) + out["ask"].astype(float))
        if "last_trade_price" not in out.columns:
            alias = _find_col(out, ["last_trade", "price", "trade_price", "last"])
            if alias:
                out = out.rename(columns={alias: "last_trade_price"})
        return out.sort_values(["symbol", "minute"])

    # Wide format: columns like bid_XLK, ask_XLK, mid_XLK.
    time_col = time_col or (df.index.name if isinstance(df.index, pd.DatetimeIndex) else None)
    if time_col and time_col in df.columns:
        minute = pd.to_datetime(df[time_col])
    elif isinstance(df.index, pd.DatetimeIndex):
        minute = pd.to_datetime(df.index)
    else:
        raise RuntimeError("Could not identify long or wide panel schema.")
    records = []
    syms = sorted({c.split("_", 1)[1] for c in df.columns if c.lower().startswith(("bid_", "ask_", "mid_")) and "_" in c})
    for sym in syms:
        cols = {k: f"{k}_{sym}" for k in ["bid", "ask", "mid", "last_trade_price", "volume", "trade_count", "bidsiz", "asksiz"] if f"{k}_{sym}" in df.columns}
        if not {"bid", "ask"}.issubset(cols):
            continue
        sub = pd.DataFrame({"minute": minute, "symbol": sym})
        for k, c in cols.items():
            sub[k] = df[c].values
        if "mid" not in sub.columns:
            sub["mid"] = 0.5 * (sub["bid"] + sub["ask"])
        records.append(sub)
    if not records:
        raise RuntimeError("Wide panel detected but no bid_/ask_ symbol columns found.")
    return pd.concat(records, ignore_index=True).sort_values(["symbol", "minute"])


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in ["bid", "ask", "mid"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["symbol", "minute", "bid", "ask", "mid"])
    out = out[(out["bid"] > 0) & (out["ask"] > out["bid"]) & (out["mid"] > 0)]
    out["spread_bps"] = 1e4 * (out["ask"] - out["bid"]) / out["mid"]
    out["halfspread_bps"] = out["spread_bps"] / 2.0
    out["tod_minute"] = out["minute"].dt.hour * 60 + out["minute"].dt.minute - (9 * 60 + 30)
    out["time_bucket"] = pd.cut(out["tod_minute"], [-1, 30, 120, 300, 390], labels=["open30", "mid_morning", "midday", "close90"])
    if {"bidsiz", "asksiz"}.issubset(out.columns):
        bid_sz = pd.to_numeric(out["bidsiz"], errors="coerce")
        ask_sz = pd.to_numeric(out["asksiz"], errors="coerce")
        out["imbalance"] = (bid_sz - ask_sz) / (bid_sz + ask_sz).replace(0, np.nan)
    else:
        out["imbalance"] = np.nan
    out["spread_bucket"] = out.groupby("symbol")["spread_bps"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 4, labels=["s_q1", "s_q2", "s_q3", "s_q4"])
    )
    if out["imbalance"].notna().sum() > 100:
        out["imb_bucket"] = pd.cut(out["imbalance"], [-1, -0.25, 0.25, 1], labels=["ask_heavy", "balanced", "bid_heavy"])
    else:
        out["imb_bucket"] = "unknown"
    return out


def symbol_costs(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sym, g in df.groupby("symbol"):
        rows.append({
            "symbol": sym,
            "minutes": int(len(g)),
            "median_spread_bps": float(g["spread_bps"].median()),
            "p90_spread_bps": float(g["spread_bps"].quantile(0.90)),
            "median_halfspread_bps": float(g["halfspread_bps"].median()),
            "mean_halfspread_bps": float(g["halfspread_bps"].mean()),
            "median_volume": float(pd.to_numeric(g.get("volume", pd.Series(index=g.index, dtype=float)), errors="coerce").median()) if "volume" in g else np.nan,
            "median_trade_count": float(pd.to_numeric(g.get("trade_count", pd.Series(index=g.index, dtype=float)), errors="coerce").median()) if "trade_count" in g else np.nan,
        })
    return pd.DataFrame(rows).sort_values("median_spread_bps")


def taker_latency_costs(df: pd.DataFrame, lags=(0, 1, 2, 5)) -> pd.DataFrame:
    rows = []
    for sym, g0 in df.groupby("symbol"):
        g = g0.sort_values("minute").reset_index(drop=True).copy()
        for lag in lags:
            bid_l = g["bid"].shift(-lag)
            ask_l = g["ask"].shift(-lag)
            mid0 = g["mid"]
            # Cost versus entry-time midpoint for market buy/sell after lag.
            buy_cost = 1e4 * (ask_l - mid0) / mid0
            sell_cost = 1e4 * (mid0 - bid_l) / mid0
            rows.append({
                "symbol": sym,
                "latency_min": lag,
                "buy_taker_cost_bps_median": float(buy_cost.median()),
                "sell_taker_cost_bps_median": float(sell_cost.median()),
                "roundtrip_two_leg_cost_bps_median": float((buy_cost + sell_cost).median()),
                "buy_taker_cost_bps_p90": float(buy_cost.quantile(0.90)),
                "sell_taker_cost_bps_p90": float(sell_cost.quantile(0.90)),
            })
    return pd.DataFrame(rows)


def last_trade_markouts(df: pd.DataFrame, horizons=(1, 5, 10)) -> pd.DataFrame:
    if "last_trade_price" not in df.columns:
        return pd.DataFrame()
    rows = []
    d = df.copy()
    d["last_trade_price"] = pd.to_numeric(d["last_trade_price"], errors="coerce")
    for sym, g0 in d.dropna(subset=["last_trade_price"]).groupby("symbol"):
        g = g0.sort_values("minute").reset_index(drop=True).copy()
        # Lee-Ready style coarse sign: last trade above mid = buyer initiated; below mid = seller initiated.
        side = np.sign(g["last_trade_price"] - g["mid"]).replace(0, np.nan)
        eff = 2 * side * 1e4 * (g["last_trade_price"] - g["mid"]) / g["mid"]
        for h in horizons:
            fut_mid = g["mid"].shift(-h)
            realized_provider = 2 * side * 1e4 * (g["last_trade_price"] - fut_mid) / g["mid"]
            adverse_provider = eff - realized_provider
            rows.append({
                "symbol": sym,
                "horizon_min": h,
                "signed_trade_obs": int(side.notna().sum()),
                "effective_spread_bps_median": float(eff.median()),
                "realized_spread_provider_bps_median": float(realized_provider.median()),
                "adverse_selection_provider_bps_median": float(adverse_provider.median()),
            })
    return pd.DataFrame(rows)


def passive_fill_model(df: pd.DataFrame, horizon: int = 5, markout_horizon: int = 10) -> pd.DataFrame:
    if "last_trade_price" not in df.columns:
        return pd.DataFrame()
    rows = []
    d = df.copy()
    d["last_trade_price"] = pd.to_numeric(d["last_trade_price"], errors="coerce")
    enriched = []
    for sym, g0 in d.dropna(subset=["last_trade_price"]).groupby("symbol"):
        g = g0.sort_values("minute").reset_index(drop=True).copy()
        if len(g) < 50:
            continue
        # Rolling future min/max of last trade over fill horizon.
        future_trades = pd.concat([g["last_trade_price"].shift(-k) for k in range(1, horizon + 1)], axis=1)
        g["passive_buy_fill"] = future_trades.min(axis=1) <= g["bid"]
        g["passive_sell_fill"] = future_trades.max(axis=1) >= g["ask"]
        fut_mid = g["mid"].shift(-markout_horizon)
        # For an alpha trader: buy passive at bid is good if future mid rises; cost is negative if price improvement beats markout.
        g["buy_passive_markout_cost_bps"] = 1e4 * (g["bid"] - fut_mid) / g["mid"]
        g["sell_passive_markout_cost_bps"] = 1e4 * (fut_mid - g["ask"]) / g["mid"]
        enriched.append(g)
    if not enriched:
        return pd.DataFrame()
    d2 = pd.concat(enriched, ignore_index=True)
    group_cols = ["symbol", "time_bucket", "spread_bucket", "imb_bucket"]
    for keys, g in d2.groupby(group_cols, observed=False):
        if len(g) < 50:
            continue
        buy_fill = g["passive_buy_fill"]
        sell_fill = g["passive_sell_fill"]
        buy_markout_bps = g["buy_passive_markout_cost_bps"]
        sell_markout_bps = g["sell_passive_markout_cost_bps"]
        rows.append({
            "symbol": keys[0],
            "time_bucket": str(keys[1]),
            "spread_bucket": str(keys[2]),
            "imb_bucket": str(keys[3]),
            "obs": int(len(g)),
            "buy_bid_fill_prob": float(buy_fill.mean()),
            "sell_ask_fill_prob": float(sell_fill.mean()),
            "buy_passive_markout_cost_bps_median_if_filled": float(buy_markout_bps[buy_fill].median()),
            "sell_passive_markout_cost_bps_median_if_filled": float(sell_markout_bps[sell_fill].median()),
            "buy_passive_markout_cost_bps_p75_if_filled": float(buy_markout_bps[buy_fill].quantile(0.75)),
            "sell_passive_markout_cost_bps_p75_if_filled": float(sell_markout_bps[sell_fill].quantile(0.75)),
        })
    return pd.DataFrame(rows)


def capacity_curve(df: pd.DataFrame, notionals=(1e5, 5e5, 1e6, 5e6), impact_coeff_bps=10.0) -> pd.DataFrame:
    if "volume" not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    d["volume"] = pd.to_numeric(d["volume"], errors="coerce")
    d["dollar_volume"] = d["volume"] * d["mid"]
    rows = []
    for sym, g in d.dropna(subset=["dollar_volume"]).groupby("symbol"):
        med_dv = float(g["dollar_volume"].median())
        p25_dv = float(g["dollar_volume"].quantile(0.25))
        half = float(g["halfspread_bps"].median())
        for notional in notionals:
            pov_med = notional / med_dv if med_dv > 0 else np.nan
            pov_p25 = notional / p25_dv if p25_dv > 0 else np.nan
            # Simple square-root impact proxy. Coefficient is configurable; output is a stress diagnostic.
            impact_med = impact_coeff_bps * math.sqrt(max(pov_med, 0)) if np.isfinite(pov_med) else np.nan
            rows.append({
                "symbol": sym,
                "notional_usd": notional,
                "median_minute_dollar_volume": med_dv,
                "p25_minute_dollar_volume": p25_dv,
                "participation_median_minute": pov_med,
                "participation_p25_minute": pov_p25,
                "median_halfspread_bps": half,
                "sqrt_impact_proxy_bps": impact_med,
                "all_in_oneway_cost_proxy_bps": half + impact_med if np.isfinite(impact_med) else np.nan,
            })
    return pd.DataFrame(rows)


def write_report(root: Path, symbol_df: pd.DataFrame, latency_df: pd.DataFrame, passive_df: pd.DataFrame, capacity_df: pd.DataFrame) -> Path:
    out = root / "output" / "empirical_execution_model.md"
    lines = []
    lines.append("# Empirical Execution-Cost Model\n")
    lines.append("This report replaces hard-coded spread fractions with costs estimated from the cleaned TAQ minute panel. It should be used as an execution diagnostic, not as a claim of true queue-level fills.\n")
    if not symbol_df.empty:
        lines.append("## Symbol-level quoted spread\n")
        lines.append(symbol_df.head(25).to_markdown(index=False))
        lines.append("\n")
    if not latency_df.empty:
        lines.append("## Taker cost under latency\n")
        lines.append("Costs are computed from actual bid/ask quotes after the latency delay, measured against the signal-time midpoint.\n")
        lines.append(latency_df.groupby("latency_min")[["buy_taker_cost_bps_median", "sell_taker_cost_bps_median"]].median().reset_index().to_markdown(index=False))
        lines.append("\n")
    if not passive_df.empty:
        lines.append("## Passive touch-fill proxy\n")
        lines.append("A buy-at-bid order is counted as filled when subsequent last-trade price trades at or below the entry bid within the fill horizon; sell-at-ask is analogous. Markout is measured after the markout horizon.\n")
        lines.append(passive_df.groupby("symbol")[["buy_bid_fill_prob", "sell_ask_fill_prob", "buy_passive_markout_cost_bps_median_if_filled", "sell_passive_markout_cost_bps_median_if_filled"]].median().reset_index().to_markdown(index=False))
        lines.append("\n")
    if not capacity_df.empty:
        lines.append("## Capacity / impact proxy\n")
        lines.append("This is a stress curve using minute dollar volume and a configurable square-root impact coefficient. It is not a fitted impact model unless calibrated to child-order execution logs.\n")
        lines.append(capacity_df.head(40).to_markdown(index=False))
        lines.append("\n")
    lines.append("## Recommended use in backtests\n")
    lines.append("1. Use direct bid/ask boundary fills as the conservative baseline for marketable orders.\n")
    lines.append("2. Use latency quote fills, not spread multipliers, for latency stress.\n")
    lines.append("3. For passive entry, use estimated fill probability and markout by bucket; unfilled orders should not magically become midpoint fills.\n")
    lines.append("4. Reject any trade whose expected reversion is below predicted all-in cost plus an adverse-selection buffer.\n")
    out.write_text("\n".join(lines))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--impact-coeff-bps", type=float, default=10.0)
    args = ap.parse_args()
    root = args.root.resolve()
    tables = root / "output" / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    df = add_features(load_panel(root))
    symbol_df = symbol_costs(df)
    latency_df = taker_latency_costs(df)
    last_trade_df = last_trade_markouts(df)
    passive_df = passive_fill_model(df)
    capacity_df = capacity_curve(df, impact_coeff_bps=args.impact_coeff_bps)

    symbol_df.to_csv(tables / "empirical_symbol_costs.csv", index=False)
    latency_df.to_csv(tables / "empirical_taker_latency_costs.csv", index=False)
    if not last_trade_df.empty:
        last_trade_df.to_csv(tables / "empirical_last_trade_markouts.csv", index=False)
    if not passive_df.empty:
        passive_df.to_csv(tables / "empirical_passive_fill_model.csv", index=False)
    if not capacity_df.empty:
        capacity_df.to_csv(tables / "empirical_capacity_curve.csv", index=False)
    report = write_report(root, symbol_df, latency_df, passive_df, capacity_df)
    print(f"[ok] wrote empirical execution tables to {tables}")
    print(f"[ok] wrote {report}")


if __name__ == "__main__":
    main()
