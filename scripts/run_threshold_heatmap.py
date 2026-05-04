#!/usr/bin/env python3
"""
Heatmap grid for XLK-only timing strategy across entry x exit thresholds.

This script is a standalone addition to the pipeline (step 4.5 — runs after
run_timing_extension.py, before make_report.py).  It re-runs the same backtest
logic from run_timing_extension.py across a grid of entry/exit threshold pairs
and produces three heatmaps (one per period: Jan, Feb, Mar) showing net bps.

Outputs
-------
Tables (CSV):
    output/tables/heatmap_grid_jan.csv   -- entry x exit net bps, January
    output/tables/heatmap_grid_feb.csv   -- entry x exit net bps, February
    output/tables/heatmap_grid_mar.csv   -- entry x exit net bps, March
    output/tables/heatmap_grid_full.csv  -- full long-format grid (all periods)

Figures (PNG):
    output/figures/heatmap_net_bps_jan.png
    output/figures/heatmap_net_bps_feb.png
    output/figures/heatmap_net_bps_mar.png

How to run
----------
    python3 scripts/run_threshold_heatmap.py

Or via the pipeline driver:
    python3 run_pipeline.py --only 7
(after adding step 7 to run_pipeline.py — see instructions at bottom of file)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT      = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT    = ROOT / "output"
TABLES    = OUTPUT / "tables"
FIGURES   = OUTPUT / "figures"

ETF = "XLK"
SPARSE_WEIGHTS = pd.Series({
    "MSFT": 0.0797,
    "NVDA": 0.2257,
    "ORCL": 0.0745,
    "CRM":  0.0602,
    "AMD":  0.1074,
})

# Period definitions: (label, start_inclusive, end_exclusive)
PERIODS: list[tuple[str, str, str]] = [
    ("jan", "2026-01-01", "2026-02-01"),
    ("feb", "2026-02-01", "2026-03-01"),
    ("mar", "2026-03-01", "2026-04-01"),
]

# Threshold grid
# Entry thresholds (bps): signal must exceed this to open a position
ENTRY_VALUES: list[float] = [20, 30, 40, 50, 60, 75, 100, 125, 150]

# Exit thresholds (bps): position is closed when |signal| falls below this.
# Only combinations where exit < entry are evaluated; others are set to NaN.
EXIT_VALUES:  list[float] = [0, 10, 15, 20, 25, 30, 40, 50, 60]

# Max hold time (minutes): hard intraday stop, same as the base strategy
MAX_HOLD_MINUTES = 390

# ---------------------------------------------------------------------------
# Data loading (reuses logic from run_timing_extension.py)
# ---------------------------------------------------------------------------

def align_panel() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load research_panel.parquet and align to a full intraday minute grid.

    Forward-fills within each trading day (limit=5 minutes) and restricts
    to minutes where all required symbols have valid mid, microprice, bid,
    and ask data.

    Returns
    -------
    mid, micro, spread_bps, bid, ask : pd.DataFrame
    """
    panel = pd.read_parquet(PROCESSED / "research_panel.parquet")
    panel["minute"] = pd.to_datetime(panel["minute"])

    required = [ETF] + list(SPARSE_WEIGHTS.index)

    def pivot(col: str) -> pd.DataFrame:
        return panel.pivot(index="minute", columns="symbol", values=col).sort_index()

    mid        = pivot("mid")
    micro      = pivot("microprice")
    spread_bps = pivot("spread_bps")
    bid        = pivot("bid")
    ask        = pivot("ask")

    dates = sorted(pd.Series(mid.index.date.astype(str)).unique())
    full_index = []
    for day in dates:
        full_index.append(pd.date_range(f"{day} 09:30:00", periods=390, freq="min"))
    full_index = full_index[0].append(full_index[1:])

    def fill(frame: pd.DataFrame) -> pd.DataFrame:
        """Forward-fill within each trading day, up to 5 minutes."""
        aligned = frame.reindex(full_index)
        key = pd.Series(aligned.index.date.astype(str), index=aligned.index)
        return aligned.groupby(key, group_keys=False).ffill(limit=5)

    mid        = fill(mid)
    micro      = fill(micro)
    spread_bps = fill(spread_bps)
    bid        = fill(bid)
    ask        = fill(ask)

    common = mid.dropna(subset=required).index
    common = common.intersection(micro.dropna(subset=required).index)
    common = common.intersection(spread_bps.dropna(subset=[ETF]).index)
    common = common.intersection(bid.dropna(subset=required).index)
    common = common.intersection(ask.dropna(subset=required).index)

    return (
        mid.loc[common].astype(float),
        micro.loc[common].astype(float),
        spread_bps.loc[common].astype(float),
        bid.loc[common].astype(float),
        ask.loc[common].astype(float),
    )


# ---------------------------------------------------------------------------
# Signal construction (identical to run_timing_extension.py)
# ---------------------------------------------------------------------------

def log_returns(px: pd.DataFrame) -> pd.DataFrame:
    """
    Compute log returns, zeroing out overnight gaps and clipping at ±5%.
    """
    ret = np.log(px).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    idx = px.index.to_series()
    continuous = (
        (idx.diff() == pd.Timedelta(minutes=1))
        & (idx.dt.date == idx.shift(1).dt.date)
    )
    ret.loc[~continuous.values, :] = 0.0
    return ret.clip(-0.05, 0.05)


def build_signal(mid: pd.DataFrame, micro: pd.DataFrame) -> pd.Series:
    """
    Build the sparse-basket microprice premium signal for XLK.

    Signal = (log microprice of XLK) - (log basket value reconstructed from
    constituent microprices) - (5-day rolling mean of the above premium),
    expressed in basis points.

    Returns
    -------
    pd.Series
        Signal in basis points, indexed by minute.
    """
    ret_micro   = log_returns(micro)
    basket_ret  = (ret_micro[list(SPARSE_WEIGHTS.index)] * SPARSE_WEIGHTS).sum(axis=1)
    basket_log  = np.log(float(micro[ETF].iloc[0])) + basket_ret.cumsum()
    raw_premium = np.log(micro[ETF]) - basket_log
    center      = raw_premium.rolling(390 * 5, min_periods=390).mean().shift(1)
    return 1e4 * (raw_premium - center)  # in bps


# ---------------------------------------------------------------------------
# Tick-adjusted execution prices (from updated cost model)
# ---------------------------------------------------------------------------

TICK_SIZE = 0.01

def execution_prices(
    mid: pd.DataFrame,
    bid: pd.DataFrame,
    ask: pd.DataFrame,
) -> tuple[pd.Series, pd.Series]:
    """
    Compute tick-adjusted execution prices for XLK only.

    Buy  fills at ask + 1 tick.
    Sell fills at bid - 1 tick.
    Falls back to mid when bid/ask are missing.

    Returns
    -------
    buy_px, sell_px : pd.Series
    """
    bid_ticked = (bid[ETF] / TICK_SIZE).round() * TICK_SIZE
    ask_ticked = (ask[ETF] / TICK_SIZE).round() * TICK_SIZE

    buy_px  = (ask_ticked + TICK_SIZE).where(ask[ETF].notna(), mid[ETF])
    sell_px = (bid_ticked - TICK_SIZE).where(bid[ETF].notna(), mid[ETF])

    return buy_px.astype(float), sell_px.astype(float)


# ---------------------------------------------------------------------------
# Position logic
# ---------------------------------------------------------------------------

def compute_positions(
    signal_bps: pd.Series,
    entry_bps: float,
    exit_bps: float,
    max_hold: int,
) -> pd.Series:
    """
    Generate a position series (+1 long, -1 short, 0 flat) from the signal.

    Entry  : |signal| > entry_bps  -> open position against the premium
    Exit   : |signal| <= exit_bps  OR hold >= max_hold minutes -> flatten
    Day end: always flatten at the last minute of each trading day

    Parameters
    ----------
    signal_bps : pd.Series
        Signal in basis points.
    entry_bps : float
        Minimum signal magnitude to open a new position.
    exit_bps : float
        Signal magnitude below which an open position is closed.
    max_hold : int
        Maximum number of minutes to hold a position intraday.

    Returns
    -------
    pd.Series
        Integer position series indexed like signal_bps.
    """
    vals    = signal_bps.to_numpy()
    dates   = pd.Series(signal_bps.index.date.astype(str), index=signal_bps.index).to_numpy()
    pos     = np.zeros(len(signal_bps))
    current = 0.0
    hold    = 0

    for i, x in enumerate(vals):
        # Reset at start of new trading day
        if i > 0 and dates[i] != dates[i - 1]:
            current = 0.0
            hold    = 0

        if np.isfinite(x):
            if current == 0.0:
                if x > entry_bps:
                    current = -1.0   # short XLK: premium too high
                    hold    = 0
                elif x < -entry_bps:
                    current = 1.0    # long XLK: premium too low
                    hold    = 0
            else:
                hold += 1
                if abs(x) <= exit_bps or hold >= max_hold:
                    current = 0.0
                    hold    = 0

        # Force flatten at end of trading day
        if i < len(vals) - 1 and dates[i + 1] != dates[i]:
            current = 0.0
            hold    = 0

        pos[i] = current

    return pd.Series(pos, index=signal_bps.index)


# ---------------------------------------------------------------------------
# P&L calculation
# ---------------------------------------------------------------------------

def compute_pnl(
    position: pd.Series,
    buy_px: pd.Series,
    sell_px: pd.Series,
    mid_etf: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Compute gross, cost, and net returns from tick-adjusted execution prices.

    Gross P&L : mid log return * lagged position (mark-to-mid while holding)
    Cost      : (ask+tick - mid)/mid on buys; (mid - bid+tick)/mid on sells
    Net       : gross - cost

    Parameters
    ----------
    position : pd.Series
        Position series from compute_positions().
    buy_px : pd.Series
        Tick-adjusted buy execution price for XLK.
    sell_px : pd.Series
        Tick-adjusted sell execution price for XLK.
    mid_etf : pd.Series
        Mid price series for XLK (used for mark-to-mid P&L).

    Returns
    -------
    gross_ret, cost_ret, net_ret : pd.Series
    """
    pos_prev = position.shift(1).fillna(0.0)
    delta    = position - pos_prev  # +1 = bought, -1 = sold

    # Mark-to-mid log return while holding
    mid_ret = np.log(mid_etf).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    idx = mid_etf.index.to_series()
    continuous = (
        (idx.diff() == pd.Timedelta(minutes=1))
        & (idx.dt.date == idx.shift(1).dt.date)
    )
    mid_ret.loc[~continuous.values] = 0.0
    mid_ret = mid_ret.clip(-0.05, 0.05)

    gross_ret = pos_prev * mid_ret

    # Approximate mid from execution prices for slippage calculation
    mid_exec  = (buy_px + sell_px) / 2.0
    buy_slip  = ((buy_px  - mid_exec) / mid_exec).clip(lower=0.0)
    sell_slip = ((mid_exec - sell_px) / mid_exec).clip(lower=0.0)

    cost_ret  = pd.Series(0.0, index=position.index)
    cost_ret += buy_slip.where(delta  > 0, 0.0)
    cost_ret += sell_slip.where(delta < 0, 0.0)

    return gross_ret, cost_ret, gross_ret - cost_ret


# ---------------------------------------------------------------------------
# Grid runner
# ---------------------------------------------------------------------------

def run_grid(
    signal_bps: pd.Series,
    buy_px: pd.Series,
    sell_px: pd.Series,
    mid_etf: pd.Series,
) -> pd.DataFrame:
    """
    Evaluate all valid (entry, exit) threshold combinations and return
    a long-format DataFrame of period-level net bps.

    A combination is skipped (NaN) when exit_bps >= entry_bps, since
    that would mean the position never exits before the max-hold timer.

    Parameters
    ----------
    signal_bps : pd.Series
        Pre-built signal in basis points.
    buy_px, sell_px : pd.Series
        Tick-adjusted execution prices for XLK.
    mid_etf : pd.Series
        XLK mid prices.

    Returns
    -------
    pd.DataFrame
        Columns: entry_bps, exit_bps, period, gross_bps, cost_bps, net_bps, trades
    """
    rows: list[dict] = []
    total = sum(1 for e in ENTRY_VALUES for x in EXIT_VALUES if x < e)
    done  = 0

    for entry in ENTRY_VALUES:
        for exit_ in EXIT_VALUES:
            # Skip invalid combinations
            if exit_ >= entry:
                for label, start, end in PERIODS:
                    rows.append({
                        "entry_bps": entry,
                        "exit_bps":  exit_,
                        "period":    label,
                        "gross_bps": np.nan,
                        "cost_bps":  np.nan,
                        "net_bps":   np.nan,
                        "trades":    np.nan,
                    })
                continue

            position = compute_positions(signal_bps, entry, exit_, MAX_HOLD_MINUTES)
            gross, cost, net = compute_pnl(position, buy_px, sell_px, mid_etf)
            turnover = position.diff().abs().fillna(position.abs())

            for label, start, end in PERIODS:
                mask = (signal_bps.index >= start) & (signal_bps.index < end)
                rows.append({
                    "entry_bps": entry,
                    "exit_bps":  exit_,
                    "period":    label,
                    "gross_bps": float(1e4 * gross[mask].sum()),
                    "cost_bps":  float(1e4 * cost[mask].sum()),
                    "net_bps":   float(1e4 * net[mask].sum()),
                    "trades":    int((turnover[mask] > 0).sum()),
                })

            done += 1
            if done % 10 == 0 or done == total:
                print(f"  [grid] {done}/{total} combinations evaluated ...")

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_heatmap(
    pivot: pd.DataFrame,
    title: str,
    out_path: Path,
    base_entry: float = 50.0,
    base_exit:  float = 25.0,
) -> None:
    """
    Save a single net-bps heatmap for one time period.

    The colormap is diverging (RdYlGn): red = negative net bps, green =
    positive.  The baseline combination (50/25 bps) is highlighted with a
    white border box.  Invalid cells (exit >= entry) are shown in light grey.

    Parameters
    ----------
    pivot : pd.DataFrame
        Wide-format DataFrame with entry_bps as index, exit_bps as columns,
        and net_bps as values.
    title : str
        Plot title.
    out_path : Path
        Destination PNG file path.
    base_entry : float
        Entry threshold of the baseline rule to highlight.
    base_exit : float
        Exit threshold of the baseline rule to highlight.
    """
    fig, ax = plt.subplots(figsize=(10, 7))

    # Mask NaN cells (invalid combinations)
    data    = pivot.values.astype(float)
    masked  = np.ma.masked_invalid(data)

    # Symmetric color scale centred at zero
    vmax = np.nanmax(np.abs(data))
    vmax = max(vmax, 1.0)   # avoid zero-range colormap

    cmap = plt.cm.RdYlGn.copy()
    cmap.set_bad(color="#DCDCDC")   # grey for invalid cells

    im = ax.imshow(masked, cmap=cmap, vmin=-vmax, vmax=vmax, aspect="auto")

    # Axis labels
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{v:.0f}" for v in pivot.columns], fontsize=9)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{v:.0f}" for v in pivot.index], fontsize=9)
    ax.set_xlabel("Exit threshold (bps)", fontsize=11, labelpad=8)
    ax.set_ylabel("Entry threshold (bps)", fontsize=11, labelpad=8)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)

    # Annotate each cell with its net bps value
    for r, entry_val in enumerate(pivot.index):
        for c, exit_val in enumerate(pivot.columns):
            val = pivot.iloc[r, c]
            if np.isnan(val):
                # Mark invalid cells with an 'x'
                ax.text(c, r, "✕", ha="center", va="center",
                        fontsize=9, color="#AAAAAA")
            else:
                color = "white" if abs(val) > vmax * 0.65 else "black"
                ax.text(c, r, f"{val:.0f}", ha="center", va="center",
                        fontsize=8, color=color, fontweight="normal")

    # Highlight the baseline (50/25 bps) cell with a white border
    if base_entry in pivot.index and base_exit in pivot.columns:
        r_base = list(pivot.index).index(base_entry)
        c_base = list(pivot.columns).index(base_exit)
        rect = plt.Rectangle(
            (c_base - 0.5, r_base - 0.5), 1, 1,
            linewidth=2.5, edgecolor="white", facecolor="none",
        )
        ax.add_patch(rect)
        ax.text(
            c_base, r_base - 0.62,
            "baseline", ha="center", va="center",
            fontsize=7, color="white", fontweight="bold",
        )

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.03)
    cbar.set_label("Net P&L (bps)", fontsize=10)
    cbar.ax.tick_params(labelsize=8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"  [plot] saved {out_path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    print("[heatmap] loading and aligning panel ...")
    mid, micro, spread_bps, bid, ask = align_panel()

    print("[heatmap] building signal ...")
    signal_bps = build_signal(mid, micro)

    print("[heatmap] computing tick-adjusted execution prices ...")
    buy_px, sell_px = execution_prices(mid, bid, ask)

    print(f"[heatmap] running {len(ENTRY_VALUES)} x {len(EXIT_VALUES)} threshold grid ...")
    grid = run_grid(signal_bps, buy_px, sell_px, mid[ETF])

    # ------------------------------------------------------------------
    # Save outputs
    # ------------------------------------------------------------------

    # Full long-format grid (all periods, all combinations)
    grid_path = TABLES / "heatmap_grid_full.csv"
    grid.to_csv(grid_path, index=False)
    print(f"  [save] {grid_path.relative_to(ROOT)}")

    period_labels = {
        "jan": "January 2026 (in-sample)",
        "feb": "February 2026 (in-sample)",
        "mar": "March 2026 (out-of-sample)",
    }

    for period_key, period_title in period_labels.items():
        # Wide-format pivot: rows = entry, columns = exit
        sub = grid[grid["period"] == period_key]
        wide = sub.pivot(index="entry_bps", columns="exit_bps", values="net_bps")
        wide.index.name   = "entry_bps"
        wide.columns.name = "exit_bps"

        # Save wide-format CSV
        csv_path = TABLES / f"heatmap_grid_{period_key}.csv"
        wide.to_csv(csv_path)
        print(f"  [save] {csv_path.relative_to(ROOT)}")

        # Save heatmap PNG
        png_path = FIGURES / f"heatmap_net_bps_{period_key}.png"
        plot_heatmap(
            pivot=wide,
            title=f"XLK Timing Strategy — Net P&L by Entry/Exit Threshold\n{period_title}",
            out_path=png_path,
        )

    print("\n[heatmap] done.")
    print("\nOutput summary:")
    print(f"  Tables  -> {(TABLES).relative_to(ROOT)}/")
    print(f"             heatmap_grid_full.csv      (long-format, all periods)")
    print(f"             heatmap_grid_jan.csv        (wide pivot, January)")
    print(f"             heatmap_grid_feb.csv        (wide pivot, February)")
    print(f"             heatmap_grid_mar.csv        (wide pivot, March)")
    print(f"  Figures -> {(FIGURES).relative_to(ROOT)}/")
    print(f"             heatmap_net_bps_jan.png")
    print(f"             heatmap_net_bps_feb.png")
    print(f"             heatmap_net_bps_mar.png")
    print()
    print("To add this as step 7 in run_pipeline.py, insert the following")
    print("entry into the PIPELINE list:")
    print("""
    (
        7,
        "run_threshold_heatmap.py",
        [],
        "Entry/exit threshold heatmap grid for XLK timing strategy "
        "(3 heatmaps: Jan, Feb, Mar net bps).",
    ),
""")


if __name__ == "__main__":
    main()