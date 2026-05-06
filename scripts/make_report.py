#!/usr/bin/env python3
"""Generate the current new-data research report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from project_config import FIGURES, OUTPUT, TABLES, metadata

ROOT = Path(__file__).resolve().parents[1]


def read_optional(name: str) -> pd.DataFrame | None:
    path = TABLES / name
    return pd.read_csv(path) if path.exists() else None


def md_table(df: pd.DataFrame | None, cols: list[str] | None = None, max_rows: int = 12) -> str:
    if df is None or df.empty:
        return "_Not available yet._"
    view = df.head(max_rows) if cols is None else df.loc[:, [c for c in cols if c in df.columns]].head(max_rows)
    return view.to_markdown(index=False)


def fmt_table(df: pd.DataFrame, cols: list[str], digits: int = 2, max_rows: int = 12) -> list[list[str]]:
    cols = [c for c in cols if c in df.columns]
    out = [cols]
    for _, row in df[cols].head(max_rows).iterrows():
        vals = []
        for value in row:
            if isinstance(value, float):
                vals.append("" if pd.isna(value) else f"{value:.{digits}f}")
            else:
                vals.append("" if pd.isna(value) else str(value))
        out.append(vals)
    return out


def table_story(story, title: str, df: pd.DataFrame | None, cols: list[str], styles, digits: int = 2, max_rows: int = 12) -> None:
    if df is None or df.empty:
        return
    story.append(Paragraph(title, styles["Heading2"]))
    table = Table(fmt_table(df, cols, digits, max_rows=max_rows), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.15 * inch))


def markdown_report() -> Path:
    meta = metadata()
    holdings = read_optional("selected_xlk_holdings.csv")
    diagnostics = read_optional("minute_data_diagnostics.csv")
    sparse = read_optional("enhanced_backtest_summary.csv")
    sparse_bidask = read_optional("enhanced_sparse_bidask_comparison.csv")
    candidates = read_optional("enhanced_sparse_candidates.csv")
    professor = read_optional("professor_test_leaderboard.csv")
    professor_cost = read_optional("professor_cost_scenario_results.csv")
    professor_ou = read_optional("professor_ou_spread_diagnostics.csv")
    robust_selection = read_optional("robust_alpha_selection.csv")
    robust_controls = read_optional("robust_alpha_controls.csv")
    robust_cost = read_optional("robust_alpha_cost_sensitivity.csv")
    timing = read_optional("timing_extension_summary.csv")
    timing_bidask = read_optional("timing_extension_bidask_comparison.csv")

    text = f"""# XLK Microstructure Statistical Arbitrage: New-Data Progress Report

## Dataset

- Raw data: `{meta.get('raw_dir', 'data/newdata')}`
- Sample: `{meta.get('start')}` to `{meta.get('end')}`
- Universe: `{meta.get('etf', 'XLK')}` + {len(meta.get('constituents', []))} constituents
- Requested-but-dropped symbols after quote/trade cleaning: `{', '.join(meta.get('dropped_requested_symbols', [])) or 'none'}`
- Split: train before `{meta.get('train_end')}`, validation before `{meta.get('validation_end')}`, test before `{meta.get('test_end')}`

## Main Research Position

The project now separates two claims:

1. **Market-neutral XLK-vs-basket arbitrage.** This remains the hard claim.  It must survive alternative spread definitions, explicit transaction-cost scenarios, and out-of-sample testing.
2. **Sparse-basket fair-value timing.** This is a different claim: the constituent basket is used as a signal, while only XLK is traded.

This language directly addresses the professor's concern that price definition, spread construction, and execution assumptions can dominate high-frequency results.

## Top Holdings Used

{md_table(holdings, ['symbol', 'name', 'official_weight_pct', 'basket_weight', 'used_in_clean_panel'], 25)}

## Data Diagnostics

{md_table(diagnostics, ['symbol', 'start', 'end', 'minutes', 'median_spread_bps', 'avg_volume', 'trade_count'], 25)}

## Professor Feedback Checks

The new `run_professor_robustness.py` module answers the main methodology questions:

- `r_XLK,t` is explicitly one-minute log return, not price.
- Cumulative residual-return spreads are compared against direct log-price spreads and log-price regression residuals.
- Gross/no-cost P&L is separated from 0.25-spread, 0.50-spread, and clipped last-trade execution proxies.
- OU / Avellaneda-Lee style diagnostics are reported for each spread.

Best validation-selected test rows:

{md_table(professor, max_rows=15)}

OU and stationarity diagnostics:

{md_table(professor_ou, ['pair', 'spread_type', 'train_adf_p', 'train_half_life_minutes', 'ou_half_life_minutes', 'train_spread_std_bps'], 15)}

## Sparse Market-Neutral Basket

{md_table(candidates, ['subset', 'k', 'betas', 'train_adf_p', 'train_half_life_minutes', 'train_avg_oneway_cost_bps', 'score'], 10)}

{md_table(sparse, ['strategy', 'sample', 'trades', 'gross_bps', 'cost_bps', 'net_bps', 'max_drawdown_bps'], 10)}

Bid/ask boundary audit:

{md_table(sparse_bidask)}

## Robust Alpha Suite

The robust alpha suite jointly tests XLK-only timing and partial/full hedge rules.  If the selected rule has `hedge_fraction = 0`, it is a timing strategy, not market-neutral arbitrage.

{md_table(robust_selection)}

Controls:

{md_table(robust_controls)}

Cost sensitivity:

{md_table(robust_cost)}

## XLK-Only Timing Extension

{md_table(timing, ['period', 'gross_bps', 'cost_bps', 'net_bps', 'trades', 'avg_abs_position', 'xlk_buyhold_bps'])}

Bid/ask boundary audit:

{md_table(timing_bidask)}

## Interpretation

The next report should avoid saying "ETF arbitrage is profitable" unless a market-neutral rule survives the new spread-construction and execution-cost checks.  The defensible framing is:

> Market-neutral XLK-vs-basket arbitrage is fragile under realistic TAQ execution assumptions.  The more promising direction is to use the sparse/top-holdings basket as a fair-value signal and trade XLK only, but the first new-data quick run does not yet prove a stable positive active strategy.  Report gross/no-cost, 0.25-spread, 0.50-spread, and last-trade proxy economics separately.

## Next Steps

1. Finish the full-grid alpha suite after verifying quick-run results.
2. Add passive maker/taker fill probabilities instead of fixed spread fractions.
3. Extend OU/s-score trading from diagnostics into rule selection.
4. Add dynamic hedge beta, likely Kalman-filter or rolling regression.
5. Add portfolio-level drawdown / VaR constraints for correlated constituent losses.

## Reproducibility

```bash
python3 scripts/build_dataset.py --force
python3 scripts/run_newdata_pipeline.py --quick
```
"""
    out = OUTPUT / "research_report.md"
    out.write_text(text)
    return out


def pdf_report() -> Path:
    holdings = read_optional("selected_xlk_holdings.csv")
    diagnostics = read_optional("minute_data_diagnostics.csv")
    professor = read_optional("professor_test_leaderboard.csv")
    robust_selection = read_optional("robust_alpha_selection.csv")
    robust_controls = read_optional("robust_alpha_controls.csv")
    timing = read_optional("timing_extension_summary.csv")
    sparse_bidask = read_optional("enhanced_sparse_bidask_comparison.csv")

    styles = getSampleStyleSheet()
    out = OUTPUT / "research_report.pdf"
    doc = SimpleDocTemplate(out.as_posix(), pagesize=letter, rightMargin=0.5 * inch, leftMargin=0.5 * inch)
    story = [
        Paragraph("XLK Microstructure Statistical Arbitrage: New-Data Progress Report", styles["Title"]),
        Paragraph(
            "Market-neutral XLK-vs-basket arbitrage is audited separately from XLK-only sparse-basket fair-value timing.  The report emphasizes spread construction, gross/no-cost economics, transaction-cost scenarios, and last-trade execution proxies.",
            styles["BodyText"],
        ),
        Spacer(1, 0.18 * inch),
    ]
    table_story(story, "Top Holdings", holdings, ["symbol", "official_weight_pct", "basket_weight"], styles, 4, 25)
    table_story(story, "Data Diagnostics", diagnostics, ["symbol", "minutes", "median_spread_bps", "trade_count"], styles, 2, 25)
    table_story(story, "Professor Cost/Spread Leaderboard", professor, ["pair", "spread_type", "no_cost_midpoint", "quarter_spread_cost", "half_spread_taker_cost", "clipped_last_trade_proxy"], styles, 2, 12)
    table_story(story, "Sparse Bid/Ask Audit", sparse_bidask, ["sample", "old_net_bps", "new_bidask_cost_bps", "new_bidask_net_bps"], styles, 2, 8)
    table_story(story, "Robust Alpha Selection", robust_selection, ["decision", "economic_label", "selected_strategy", "train_net_bps", "test_net_bps"], styles, 2, 5)
    table_story(story, "Robust Alpha Controls", robust_controls, ["control", "train_net_bps", "test_net_bps", "test_trades"], styles, 2, 8)
    table_story(story, "XLK-Only Timing", timing, ["period", "gross_bps", "cost_bps", "net_bps", "trades"], styles, 2, 8)
    for fig_name in ["professor_cost_scenario_leaderboard.png", "robust_alpha_selected_cumulative.png", "timing_extension_cumulative_net.png"]:
        fig = FIGURES / fig_name
        if fig.exists():
            story.append(Image(fig.as_posix(), width=6.8 * inch, height=3.8 * inch))
            story.append(Spacer(1, 0.15 * inch))
    doc.build(story)
    return out


def main() -> None:
    md = markdown_report()
    pdf = pdf_report()
    print(f"[report] wrote {md.relative_to(ROOT)}")
    print(f"[report] wrote {pdf.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
