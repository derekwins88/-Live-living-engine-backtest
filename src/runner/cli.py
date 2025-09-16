"""Command line interface for running backtests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .backtest import run_backtest


def main() -> None:
    parser = argparse.ArgumentParser(description="Living Engine backtest runner")
    parser.add_argument("--data", required=True, help="Path to OHLCV data (CSV or Parquet)")
    parser.add_argument(
        "--params",
        default="configs/default.yaml",
        help="Path to YAML or JSON parameter file",
    )
    parser.add_argument("--out", default="runs/latest", help="Output directory for run artefacts")
    args = parser.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    params_path = Path(args.params)
    if not params_path.exists():
        raise FileNotFoundError(params_path)

    if params_path.suffix.lower() in {".yaml", ".yml"}:
        params = yaml.safe_load(params_path.read_text()) or {}
    elif params_path.suffix.lower() == ".json":
        params = json.loads(params_path.read_text())
    else:
        raise ValueError("Unsupported params file type")

    metrics = run_backtest(args.data, params, outdir)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
