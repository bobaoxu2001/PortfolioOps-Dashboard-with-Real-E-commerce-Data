"""Run the full analytics pipeline in one command."""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys


def run_step(command: list[str], cwd: pathlib.Path) -> None:
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, cwd=str(cwd), check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute end-to-end Olist analytics pipeline.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip raw data download (use existing files in data/raw).",
    )
    parser.add_argument(
        "--skip-dashboard",
        action="store_true",
        help="Skip dashboard PNG/PDF asset generation.",
    )
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parents[1]

    if not args.skip_download:
        run_step([sys.executable, "python/download_olist_data.py"], repo_root)
    run_step([sys.executable, "python/build_reporting_layer.py"], repo_root)
    run_step([sys.executable, "python/run_data_contract_tests.py"], repo_root)
    if not args.skip_dashboard:
        run_step([sys.executable, "python/generate_dashboard_assets.py"], repo_root)

    print("Pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
