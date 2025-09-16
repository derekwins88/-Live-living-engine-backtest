from pathlib import Path

import yaml

from runner.backtest import run_backtest


def test_strategy_smoke(tmp_path):
    params = yaml.safe_load(Path("configs/default.yaml").read_text())
    metrics = run_backtest("data/sample/sample_ohlcv.csv", params, tmp_path)

    assert "final_equity" in metrics
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "trades.csv").exists()
    assert (tmp_path / "summary.txt").exists()
    assert (tmp_path / "proof_ledger.csv").exists()
    assert (tmp_path / "capsules.jsonl").exists()
