#!/usr/bin/env python3
"""Dedicated market-neutral z-score heatmap entrypoint.

Runs the pair/spread z-score grid with smaller entry z thresholds and writes the
validation/test net-bps heatmaps plus trade-count heatmap.
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
    print("[zscore-heatmap] wrote output/figures/heatmap_validation_net_bps.png")
    print("[zscore-heatmap] wrote output/figures/heatmap_test_net_bps.png")
    print("[zscore-heatmap] wrote output/figures/heatmap_trade_count.png")


if __name__ == "__main__":
    main()
