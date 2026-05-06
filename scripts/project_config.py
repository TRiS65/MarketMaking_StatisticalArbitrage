"""Shared configuration helpers for the XLK TAQ project scripts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROCESSED = DATA / "processed"
OUTPUT = ROOT / "output"
TABLES = OUTPUT / "tables"
FIGURES = OUTPUT / "figures"
ETF = "XLK"
MINUTES_PER_DAY = 390
ANN_FACTOR = 252 * MINUTES_PER_DAY


def ensure_output_dirs() -> None:
    for path in [PROCESSED, OUTPUT, TABLES, FIGURES]:
        path.mkdir(parents=True, exist_ok=True)


def metadata() -> dict:
    path = PROCESSED / "dataset_metadata.json"
    if path.exists():
        return json.loads(path.read_text())
    return {
        "dataset": "legacy",
        "etf": ETF,
        "symbols": [ETF, "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "CSCO"],
        "constituents": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "CSCO"],
        "start": "2026-01-01",
        "end": "2026-04-01",
        "train_end": "2026-02-01",
        "validation_end": "2026-03-01",
        "test_end": "2026-04-01",
    }


def constituents() -> list[str]:
    meta = metadata()
    if "constituents" in meta:
        names = [str(s) for s in meta["constituents"]]
        panel_path = PROCESSED / "research_panel.parquet"
        if panel_path.exists():
            try:
                available = set(pd.read_parquet(panel_path, columns=["symbol"])["symbol"].astype(str).unique())
                names = [s for s in names if s in available]
            except Exception:
                pass
        return names
    holdings = TABLES / "selected_xlk_holdings.csv"
    if holdings.exists():
        return pd.read_csv(holdings)["symbol"].astype(str).tolist()
    return ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "CSCO"]


def symbols() -> list[str]:
    return [ETF] + constituents()


def split_dates() -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    meta = metadata()
    return (
        pd.Timestamp(meta.get("train_end", "2026-02-01")),
        pd.Timestamp(meta.get("validation_end", "2026-03-01")),
        pd.Timestamp(meta.get("test_end", meta.get("end", "2026-04-01"))),
    )


def project_window() -> tuple[pd.Timestamp, pd.Timestamp]:
    meta = metadata()
    return pd.Timestamp(meta.get("start", "2026-01-01")), pd.Timestamp(meta.get("end", "2026-04-01"))
