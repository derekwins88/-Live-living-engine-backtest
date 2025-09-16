# Living Engine Backtest

A lightweight, reproducible harness for running IMM Cognitive Core v11 inspired backtests. The toolchain loads OHLCV data, streams it through the strategy, captures ProofBridge capsules, and produces human readable day summaries.

## Features

- Simple strategy interface (`StrategyBase`) for plug-and-play strategy experimentation.
- CSV/Parquet data loading with optional resampling utilities.
- ProofBridge CSV + JSONL ledger writers for glyph/entropy capsules.
- Headline metrics (Sharpe, CAGR estimate, drawdown) and Book Builder narrative summary.
- Command line entry point (`leb`) for reproducible runs.

## Quickstart

```bash
pip install -e .
leb --data data/sample_prices.csv --out runs/dev
```

Outputs are written to the specified `--out` directory:

- `metrics.json` — Summary statistics for the equity curve.
- `trades_blotter.csv` — Executed trades from the naive fill model.
- `summary.txt` — Book Builder style narrative.
- `proof_ledger.csv` / `proof_capsule.json` — ProofBridge capsule archives.

The bundled `data/sample_prices.csv` stream includes synthetic entropy readings so you can validate the collapse/P/NP regime
classifier without wiring in a full market data feed.

Default strategy parameters live in [`configs/default.yaml`](configs/default.yaml) and now mirror the structured `risk`, `entropy`, and `signals` blocks used by production IMM harnesses. Symbol metadata and session information can be extended in [`configs/symbols.yaml`](configs/symbols.yaml).

## Development

Install dev dependencies and run the tests:

```bash
pip install -e .[dev]
pytest
```

CI runs a smoke backtest on the bundled sample data via GitHub Actions.
