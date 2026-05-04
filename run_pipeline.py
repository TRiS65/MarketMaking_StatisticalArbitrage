#!/usr/bin/env python3
"""
Pipeline driver for the XLK microstructure stat-arb research project.

Execution order:
    1. build_dataset.py          -- raw TAQ -> minute parquet -> research_panel
    2. run_final_analysis.py     -- sparse hedge backtest (train/test)
    3. run_experiment_suite.py   -- full walk-forward grid search
    4. run_timing_extension.py   -- XLK-only timing strategy (fixed 50/25 bps)
    5. run_timing_robustness.py  -- robustness grid over timing parameters
    6. run_old_data_method_upgrade.py -- pair trading, z heatmaps, cost audit
    7. make_report.py            -- assemble markdown + PDF report

Usage:
    # Run the full pipeline
    python3 run_pipeline.py

    # Start from a specific step (skips earlier steps)
    python3 run_pipeline.py --from-step 3

    # Run only specific steps
    python3 run_pipeline.py --only 4 5

    # Dry run: print commands without executing
    python3 run_pipeline.py --dry-run

    # Force rebuild of dataset even if panel already exists
    python3 run_pipeline.py --force-rebuild

    # Use quick mode for experiment suite (smaller grid, faster iteration)
    python3 run_pipeline.py --quick
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependency manifest
# ---------------------------------------------------------------------------

# Each entry: (import_name, pip_install_name, min_version_or_None)
# import_name      : the name used in `import <name>`
# pip_install_name : the name passed to `pip install <name>`
# min_version      : checked via pkg_resources if not None; use None to skip
REQUIRED_PACKAGES: list[tuple[str, str, str | None]] = [
    # Core numerics
    ("numpy",           "numpy",            "1.23"),
    ("pandas",          "pandas",           "1.5"),
    ("scipy",           "scipy",            None),
    # Statistics / time-series
    ("statsmodels",     "statsmodels",      "0.13"),
    # Data storage
    ("pyarrow",         "pyarrow",          "10.0"),
    ("duckdb",          "duckdb",           "0.9"),
    # Excel reading (for holdings file)
    ("openpyxl",        "openpyxl",         None),
    # Plotting
    ("matplotlib",      "matplotlib",       "3.5"),
    # Report generation
    ("reportlab",       "reportlab",        None),
    # Markdown tables (used by make_report.py via DataFrame.to_markdown)
    ("tabulate",        "tabulate",         None),
]

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT    = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"

# Each step: (step_number, script_name, extra_args, description)
PIPELINE: list[tuple[int, str, list[str], str]] = [
    (
        1,
        "build_dataset.py",
        [],
        "Aggregate raw TAQ quote/trade CSVs into minute-level parquet files "
        "and build the research panel.",
    ),
    (
        2,
        "run_final_analysis.py",
        [],
        "Sparse-basket hedge backtest with literature-grounded methodology "
        "(Jan-Feb train / March OOS).",
    ),
    (
        3,
        "run_experiment_suite.py",
        [],
        "Full walk-forward grid search over candidate baskets, signal views, "
        "thresholds, and cost gates.",
    ),
    (
        4,
        "run_timing_extension.py",
        [],
        "XLK-only timing strategy using sparse-basket microprice premium "
        "as a fair-value signal (fixed 50/25 bps rule).",
    ),
    (
        5,
        "run_timing_robustness.py",
        [],
        "Robustness grid over microprice shrinkage, rolling-center horizon, "
        "entry/exit bands, and max hold time for the XLK timing rule.",
    ),
    (
        6,
        "run_old_data_method_upgrade.py",
        [],
        "Old-data method upgrade: pair trading, validation/test z-score "
        "heatmaps, max-holding exits, bid/ask-aware execution diagnostics, "
        "trade logs, and selection audit.",
    ),
    (
        7,
        "make_report.py",
        [],
        "Assemble all CSV tables and figures into the final markdown and PDF report.",
    ),
]


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

def check_dependencies(python: str, auto_install: bool) -> bool:
    """
    Verify that every package in REQUIRED_PACKAGES is importable and meets
    the minimum version requirement (when specified).

    Parameters
    ----------
    python : str
        Path to the Python interpreter (used to run pip install when
        auto_install is True).
    auto_install : bool
        If True, attempt `pip install <package>` for any missing package
        before re-checking.  If False, just report and return False.

    Returns
    -------
    bool
        True if all packages are present and satisfy version constraints,
        False if any package is still missing or too old after the optional
        install attempt.
    """
    import importlib.metadata as meta

    print(separator("="))
    print("  DEPENDENCY CHECK")
    print(separator("-"))

    missing:      list[str] = []   # packages not importable at all
    version_fail: list[str] = []   # packages importable but below min version
    ok:           list[str] = []   # packages that pass

    for import_name, pip_name, min_version in REQUIRED_PACKAGES:
        # Check importability
        found = importlib.util.find_spec(import_name) is not None

        if not found:
            missing.append(pip_name)
            print(f"  [MISSING ] {import_name:<20} (pip install {pip_name})")
            continue

        # Check version when a minimum is specified
        if min_version is not None:
            try:
                installed = meta.version(pip_name)
                # Compare tuples of ints for robustness
                inst_tuple = tuple(int(x) for x in installed.split(".")[:3] if x.isdigit())
                min_tuple  = tuple(int(x) for x in min_version.split(".")[:3] if x.isdigit())
                if inst_tuple < min_tuple:
                    version_fail.append(pip_name)
                    print(
                        f"  [OLD VER ] {import_name:<20}  installed={installed}  "
                        f"required>={min_version}  (pip install --upgrade {pip_name})"
                    )
                    continue
                else:
                    print(f"  [OK      ] {import_name:<20}  {installed}")
            except meta.PackageNotFoundError:
                # Package importable but metadata not available; treat as ok
                print(f"  [OK      ] {import_name:<20}  (version unknown)")
        else:
            print(f"  [OK      ] {import_name:<20}")

        ok.append(import_name)

    needs_action = missing + version_fail

    if not needs_action:
        print(separator("-"))
        print(f"  All {len(ok)} required packages are present.\n")
        return True

    # Attempt auto-install when requested
    if auto_install and needs_action:
        print(separator("-"))
        print(f"  Auto-installing {len(needs_action)} package(s) ...")
        print(separator("-"))
        cmd = [python, "-m", "pip", "install", "--upgrade"] + needs_action
        print(f"  Running: {' '.join(cmd)}\n")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print("\n  [ERROR] pip install failed. Fix manually and re-run.")
            return False

        # Re-check after install
        print(separator("-"))
        print("  Re-checking after install ...")
        still_bad: list[str] = []
        for import_name, pip_name, _ in REQUIRED_PACKAGES:
            # Invalidate the import cache so newly installed packages are found
            if import_name in sys.modules:
                del sys.modules[import_name]
            found = importlib.util.find_spec(import_name) is not None
            if not found:
                still_bad.append(pip_name)
                print(f"  [STILL MISSING] {import_name}")
            else:
                print(f"  [OK      ] {import_name}")

        if still_bad:
            print(f"\n  [ERROR] Could not install: {', '.join(still_bad)}")
            return False

        print(separator("-"))
        print("  All packages installed successfully.\n")
        return True

    # No auto-install: report and fail
    print(separator("-"))
    print(
        f"  {len(needs_action)} issue(s) found. "
        "Re-run with --auto-install to fix automatically, or install manually:"
    )
    for pkg in needs_action:
        print(f"    pip install --upgrade {pkg}")
    print()
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full XLK stat-arb research pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--from-step",
        type=int,
        default=1,
        metavar="N",
        help="Start execution from step N (default: 1, i.e. run everything).",
    )
    parser.add_argument(
        "--only",
        type=int,
        nargs="+",
        metavar="N",
        help="Run only the listed step numbers, e.g. --only 4 5.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Pass --force to build_dataset.py so it rebuilds existing outputs.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Pass --quick to run_experiment_suite.py for a smaller grid.",
    )
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Automatically pip-install any missing or outdated packages before running.",
    )
    parser.add_argument(
        "--skip-dep-check",
        action="store_true",
        help="Skip the dependency check entirely (useful if you know env is correct).",
    )
    parser.add_argument(
        "--python",
        type=str,
        default=sys.executable,
        help="Python interpreter to use (default: current interpreter).",
    )
    return parser.parse_args()


def separator(char: str = "-", width: int = 70) -> str:
    return char * width


def format_elapsed(seconds: float) -> str:
    """Return a human-readable elapsed time string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m {secs:02d}s"


def build_command(
    step: int,
    script: str,
    extra_args: list[str],
    python: str,
    force_rebuild: bool,
    quick: bool,
) -> list[str]:
    """Construct the subprocess command for a given pipeline step."""
    script_path = SCRIPTS / script
    cmd = [python, str(script_path)] + extra_args

    # Step-specific flag injection
    if step == 1 and force_rebuild:
        cmd.append("--force")
    if step == 3 and quick:
        cmd.append("--quick")

    return cmd


def run_step(
    step: int,
    script: str,
    description: str,
    cmd: list[str],
    dry_run: bool,
) -> bool:
    """
    Execute a single pipeline step.

    Returns True on success, False on failure.
    """
    print(separator("="))
    print(f"  STEP {step}: {script}")
    print(f"  {description}")
    print(separator("-"))
    print(f"  Command: {' '.join(cmd)}")
    print(separator("="))

    if dry_run:
        print("  [dry-run] Skipping execution.\n")
        return True

    start = time.time()
    result = subprocess.run(cmd, cwd=ROOT)
    elapsed = time.time() - start

    if result.returncode == 0:
        print(f"\n  [OK] Step {step} completed in {format_elapsed(elapsed)}.\n")
        return True
    else:
        print(
            f"\n  [FAILED] Step {step} exited with code {result.returncode} "
            f"after {format_elapsed(elapsed)}.\n"
        )
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    # Determine which steps to run
    if args.only:
        steps_to_run = set(args.only)
    else:
        steps_to_run = {s for s, *_ in PIPELINE if s >= args.from_step}

    print(separator("="))
    print("  XLK STAT-ARB RESEARCH PIPELINE")
    print(separator("="))
    if args.dry_run:
        print("  Mode      : DRY RUN (no scripts will be executed)")
    print(f"  Root      : {ROOT}")
    print(f"  Python    : {args.python}")
    print(f"  Steps     : {sorted(steps_to_run)}")
    if args.force_rebuild:
        print("  Flags     : --force-rebuild active for step 1")
    if args.quick:
        print("  Flags     : --quick active for step 3")
    print(separator("="))
    print()

    # ------------------------------------------------------------------
    # Dependency check (runs before any pipeline step)
    # ------------------------------------------------------------------
    if args.skip_dep_check:
        print("  [skip] Dependency check skipped (--skip-dep-check).\n")
    else:
        deps_ok = check_dependencies(
            python=args.python,
            auto_install=args.auto_install,
        )
        if not deps_ok:
            print(separator("!"))
            print("  Dependency check failed. Pipeline will not start.")
            print("  Use --auto-install to fix automatically, or")
            print("  use --skip-dep-check to bypass this check.")
            print(separator("!"))
            sys.exit(1)

    pipeline_start = time.time()
    results: dict[int, bool] = {}

    for step, script, extra_args, description in PIPELINE:
        if step not in steps_to_run:
            print(f"  [skip] Step {step}: {script}")
            continue

        cmd = build_command(step, script, extra_args, args.python, args.force_rebuild, args.quick)
        success = run_step(step, script, description, cmd, args.dry_run)
        results[step] = success

        if not success:
            # Abort on failure: downstream steps depend on earlier outputs
            print(separator("!"))
            print(f"  Pipeline aborted at step {step}.")
            print("  Fix the error above and re-run with --from-step {step}.")
            print(separator("!"))
            sys.exit(1)

    # Final summary
    total_elapsed = time.time() - pipeline_start
    print(separator("="))
    print("  PIPELINE COMPLETE")
    print(separator("-"))
    for step, script, *_ in PIPELINE:
        if step in results:
            status = "OK     " if results[step] else "FAILED "
            print(f"  [{status}] Step {step}: {script}")
        else:
            print(f"  [skip  ] Step {step}: {script}")
    print(separator("-"))
    print(f"  Total elapsed: {format_elapsed(total_elapsed)}")
    print(separator("="))


if __name__ == "__main__":
    main()
