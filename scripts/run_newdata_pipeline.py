#!/usr/bin/env python3
"""Run the new-data research pipeline in dependency order.

The raw build step is intentionally optional because scanning 90GB+ of gzipped
TAQ data can take a while.  Use `--rebuild-data` when the minute parquet/panel
needs to be regenerated from `data/newdata`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("[pipeline]", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run new-data XLK robustness pipeline")
    parser.add_argument("--rebuild-data", action="store_true")
    parser.add_argument("--quick", action="store_true", help="Use quick grids for alpha optimizer")
    args = parser.parse_args()

    py = sys.executable
    if args.rebuild_data:
        run([py, "scripts/build_dataset.py", "--force"])
    run([py, "scripts/run_final_analysis.py"])
    run([py, "scripts/run_professor_robustness.py"])
    run([py, "scripts/run_top20_method_diagnostics.py"])
    run([py, "scripts/run_empirical_execution_model.py", "--root", "."])
    robust = [py, "scripts/run_robust_alpha_suite.py", "--root", ".", "--max-subset-size", "5", "--top-candidates", "12", "--n-shifts", "150"]
    if args.quick:
        robust.append("--quick")
    run(robust)
    run([py, "scripts/run_execution_optimized_backtest.py", "--root", ".", "--quick"])
    run([py, "scripts/run_fixed_bps_timing_controls.py", "--root", ".", "--n-shifts", "200"])
    run([py, "scripts/run_timing_extension.py"])
    run([py, "scripts/run_timing_bidask_execution.py"])
    run([py, "scripts/run_loss_streamline.py", "--root", "."])
    run([py, "scripts/make_report.py"])


if __name__ == "__main__":
    main()
