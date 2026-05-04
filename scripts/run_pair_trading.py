#!/usr/bin/env python3
"""Dedicated high-frequency pair-trading entrypoint.

This is a thin, named wrapper around run_old_data_method_upgrade.py.  The shared
engine estimates XLK-stock hedge ratios, runs the pair z-score grid, applies
actual bid/ask fills, and writes the pair leaderboard.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "run_old_data_method_upgrade.py")]
    if "--quick" in sys.argv:
        cmd.append("--quick")
    subprocess.run(cmd, check=True)
    src = ROOT / "output" / "tables" / "old_pair_leaderboard.csv"
    dst = ROOT / "output" / "tables" / "pair_trading_leaderboard.csv"
    if src.exists():
        shutil.copyfile(src, dst)
        print(f"[pair-trading] wrote {dst.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
