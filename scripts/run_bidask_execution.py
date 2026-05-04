#!/usr/bin/env python3
"""Dedicated actual bid/ask execution diagnostic entrypoint.

Runs the shared old-data upgrade engine and highlights the output that compares
midpoint P&L, half-spread cost approximation, and actual entry/exit bid/ask
fills.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "run_old_data_method_upgrade.py")]
    if "--quick" in sys.argv:
        cmd.append("--quick")
    subprocess.run(cmd, check=True)
    print("[bidask-execution] wrote output/tables/midpoint_vs_bidask_execution_comparison.csv")
    print("[bidask-execution] wrote output/figures/midpoint_vs_bidask_execution_comparison.png")


if __name__ == "__main__":
    main()
