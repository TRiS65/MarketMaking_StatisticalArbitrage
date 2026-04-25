#!/usr/bin/env python3
"""Generate the final report from the final-version outputs only."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
TABLES = OUTPUT / "tables"
FIGURES = OUTPUT / "figures"


def read_table(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / name)


def table_md(df: pd.DataFrame, cols: list[str] | None = None) -> str:
    view = df if cols is None else df[cols]
    return view.to_markdown(index=False)


def fmt_table(df: pd.DataFrame, cols: list[str], digits: int = 3) -> list[list[str]]:
    out = [cols]
    for _, row in df[cols].iterrows():
        vals = []
        for value in row:
            if isinstance(value, float):
                vals.append("" if pd.isna(value) else f"{value:.{digits}f}")
            else:
                vals.append("" if pd.isna(value) else str(value))
        out.append(vals)
    return out


def markdown_report() -> Path:
    holdings = read_table("selected_xlk_holdings.csv")
    diagnostics = read_table("minute_data_diagnostics.csv")
    candidates = read_table("enhanced_sparse_candidates.csv").head(8)
    backtest = read_table("enhanced_backtest_summary.csv")
    comparison = read_table("model_comparison.csv")
    audit = read_table("selection_audit.csv")
    timing_summary = read_table("timing_extension_summary.csv")
    timing_controls = read_table("timing_extension_controls.csv")
    timing_cost = read_table("timing_extension_cost_sensitivity.csv")

    active_test = backtest[(backtest["strategy"] != "literature_no_trade") & (backtest["sample"] == "test")].iloc[0]
    active_train = backtest[(backtest["strategy"] != "literature_no_trade") & (backtest["sample"] == "train")].iloc[0]

    text = f"""# Microstructure-Based Fair Value and Intraday Statistical Arbitrage in XLK

## Executive Summary

This final version implements a literature-grounded diagnostic test of ETF-basket intraday statistical arbitrage using WRDS TAQ quotes/trades for January-March 2026 and the supplied XLK holdings file.  It now reports two strategy classes side by side.

The original market-neutral ETF-basket arbitrage conclusion is negative.  The active sparse microprice-signal hedge strategy is positive in the January-February selection period, with {active_train['net_bps']:.2f} bps net P&L, but fails out of sample in March, with {active_test['net_bps']:.2f} bps net P&L.  The no-trade benchmark therefore dominates the active market-neutral rule in the honest March test.

However, a second strategy class does produce a positive result: use the sparse basket microprice premium as a fair-value timing signal, but execute only XLK.  This XLK-only timing extension earns {timing_summary.loc[timing_summary['period'].eq('mar'), 'net_bps'].iloc[0]:.2f} bps net in March and {timing_summary.loc[timing_summary['period'].eq('all'), 'net_bps'].iloc[0]:.2f} bps net over the sample.  This is not market-neutral ETF arbitrage; it is a sparse-basket fair-value signal for intraday XLK timing.

## Data Construction

Raw WRDS TAQ files were scanned with DuckDB and aggregated to one-minute parquet files.  Quotes were filtered to regular hours, valid positive bid/ask prices and sizes, non-cancelled quotes, quoted spreads below 100 bps, and prices within 500 bps of a centered rolling median to remove narrow-spread bad ticks.  Trades were filtered to regular hours, positive price/size, and `TR_CORR = 00`.

The eight-name selected basket covers {holdings['official_weight'].sum():.2%} of the XLK holdings file and is therefore treated as an incomplete risk proxy rather than a literal NAV replication basket.

## Selected Holdings

{table_md(holdings, ['symbol', 'name', 'official_weight_pct', 'basket_weight'])}

## Minute Data Diagnostics

{table_md(diagnostics, ['symbol', 'minutes', 'median_spread_bps', 'avg_volume', 'trade_count'])}

## Final Method

The final experiment uses the literature in the project folder as design constraints:

- d'Aspremont: search sparse mean-reverting baskets rather than forcing a dense normalized holdings basket.
- Kanamura, Rachev, and Fabozzi: evaluate spread trading as a first-passage / mean-reversion problem.
- Leung and Li: use entry/exit bands instead of continuous trading around zero.
- Martin: include proportional-cost no-trade logic and compare against no-trade.
- Gueant, Lehalle, Fernandez-Tapia; Ghoshal and Roberts: account for inventory, turnover, spread costs, and adverse-selection-style execution friction.
- Almgren: use time-varying liquidity costs rather than a constant fee.
- Dare: use a train/test statistical-arbitrage workflow.

Microprice is used only as a fair-value signal.  Executable gross P&L is computed from midpoint residual returns, with bid-ask costs charged separately.  Candidate selection and threshold choice use January-February 2026; March 2026 is the out-of-sample test.

## Sparse Candidate Ranking

{table_md(candidates, ['subset', 'betas', 'train_adf_p', 'train_half_life_minutes', 'train_avg_oneway_cost_bps', 'score'])}

## Final Backtest

{table_md(backtest, ['strategy', 'sample', 'trades', 'avg_abs_position', 'gross_bps', 'cost_bps', 'net_bps', 'sharpe_minute_ann', 'max_drawdown_bps'])}

## Positive Timing Extension

The positive extension follows a different economic claim.  The basket is no longer traded as a hedge.  Instead, the sparse basket supplies a microprice fair-value premium signal for trading XLK only:

- signal basket: `MSFT NVDA ORCL CRM AMD`;
- signal: microprice premium minus five-day rolling premium mean;
- traded instrument: XLK only;
- entry: premium above/below 50 bps;
- exit: premium reverts inside 25 bps;
- max hold: intraday.

{table_md(timing_summary, ['period', 'gross_bps', 'cost_bps', 'net_bps', 'trades', 'avg_abs_position', 'long_gross_bps', 'short_gross_bps', 'xlk_buyhold_bps'])}

Controls show that the result is not explained by simple long exposure or by flipping the signal:

{table_md(timing_controls, ['control', 'train_net_bps', 'mar_net_bps', 'avg_pos_mar'])}

Cost sensitivity:

{table_md(timing_cost.pivot(index='cost_multiplier', columns='period', values='net_bps').reset_index())}

## Model Comparison

{table_md(comparison, ['model', 'selection_rule', 'train_net_bps', 'march_net_bps', 'full_net_bps', 'verdict'])}

## Selection Audit

The `v2_best_march_diagnostic` row is not selected because it sorts the grid by March P&L after observing March.  March is the test set, so choosing that row is selection-on-test / look-ahead bias.  It remains useful as a post-mortem diagnostic, but it cannot be reported as an honest tradable strategy.

{table_md(audit, ['model', 'selection_protocol', 'train_net_bps', 'march_net_bps', 'bias_flag', 'final_use'])}

## Interpretation

The initial holdings-weight basket result was not a tradable positive result: it lost before costs and then lost more after costs.  The v2 diagnostic improved methodology by treating microprice as signal-only and using rolling residual signals, but strict January-February selection did not find a train-positive active strategy.  The final hybrid sparse specification found a train-positive microprice signal, but midpoint-executable March P&L was negative.

The most defensible conclusion is therefore two-part: **the proposed market-neutral ETF-basket arbitrage fails under this incomplete-basket implementation, but the same sparse-basket microprice premium can be repurposed into a profitable XLK-only timing signal in this sample.**

## Reproducibility

```bash
python3 scripts/build_dataset.py
python3 scripts/run_final_analysis.py
python3 scripts/make_report.py
```
"""
    out = OUTPUT / "research_report.md"
    out.write_text(text)
    return out


def add_table(story, title: str, df: pd.DataFrame, cols: list[str], styles, digits: int = 3) -> None:
    story.append(Paragraph(title, styles["Heading2"]))
    table = Table(fmt_table(df, cols, digits), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.15 * inch))


def pdf_report() -> Path:
    holdings = read_table("selected_xlk_holdings.csv")
    diagnostics = read_table("minute_data_diagnostics.csv")
    candidates = read_table("enhanced_sparse_candidates.csv").head(5)
    backtest = read_table("enhanced_backtest_summary.csv")
    comparison = read_table("model_comparison.csv")
    audit = read_table("selection_audit.csv")
    timing_summary = read_table("timing_extension_summary.csv")
    timing_controls = read_table("timing_extension_controls.csv")
    timing_cost = read_table("timing_extension_cost_sensitivity.csv")

    styles = getSampleStyleSheet()
    out = OUTPUT / "research_report.pdf"
    doc = SimpleDocTemplate(out.as_posix(), pagesize=letter, rightMargin=0.5 * inch, leftMargin=0.5 * inch)
    story = [
        Paragraph("Microstructure-Based Fair Value and Intraday Statistical Arbitrage in XLK", styles["Title"]),
        Paragraph("Final report: negative tradable result under incomplete-basket implementation", styles["Normal"]),
        Spacer(1, 0.2 * inch),
        Paragraph(
            "The market-neutral sparse microprice-signal strategy is positive in the January-February selection period but fails in the March out-of-sample period.  A separate XLK-only timing extension using the same sparse-basket premium signal is profitable in Jan, Feb, and March.",
            styles["BodyText"],
        ),
        Spacer(1, 0.15 * inch),
    ]

    add_table(story, "Selected Holdings", holdings, ["symbol", "official_weight_pct", "basket_weight"], styles, 4)
    add_table(story, "Minute Data Diagnostics", diagnostics, ["symbol", "minutes", "median_spread_bps", "trade_count"], styles, 2)
    add_table(story, "Sparse Candidate Ranking", candidates, ["subset", "train_adf_p", "train_half_life_minutes", "train_avg_oneway_cost_bps"], styles, 4)
    add_table(story, "Final Backtest", backtest, ["strategy", "sample", "trades", "gross_bps", "cost_bps", "net_bps"], styles, 3)
    add_table(story, "Model Comparison", comparison, ["model", "train_net_bps", "march_net_bps", "full_net_bps"], styles, 3)
    add_table(story, "Selection Audit", audit, ["model", "train_net_bps", "march_net_bps", "bias_flag"], styles, 3)
    add_table(story, "Positive Timing Extension", timing_summary, ["period", "gross_bps", "cost_bps", "net_bps", "trades", "xlk_buyhold_bps"], styles, 3)
    add_table(story, "Timing Controls", timing_controls, ["control", "train_net_bps", "mar_net_bps", "avg_pos_mar"], styles, 3)

    fig = FIGURES / "enhanced_sparse_cumulative_net.png"
    if fig.exists():
        story.append(Image(fig.as_posix(), width=6.8 * inch, height=3.8 * inch))
        story.append(Spacer(1, 0.15 * inch))
    for fig_name in ["timing_extension_cumulative_net.png", "timing_extension_signal_march.png"]:
        fig = FIGURES / fig_name
        if fig.exists():
            story.append(Image(fig.as_posix(), width=6.8 * inch, height=3.8 * inch))
            story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Conclusion", styles["Heading2"]))
    story.append(
        Paragraph(
            "The proposed market-neutral ETF-basket arbitrage fails under the available eight-name proxy basket.  Microprice is nevertheless useful as a fair-value signal: when the noisy hedge leg is removed, the sparse-basket premium produces a profitable XLK-only timing strategy in this sample.",
            styles["BodyText"],
        )
    )
    doc.build(story)
    return out


def main() -> None:
    md = markdown_report()
    pdf = pdf_report()
    print(f"[report] wrote {md.relative_to(ROOT)}")
    print(f"[report] wrote {pdf.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
