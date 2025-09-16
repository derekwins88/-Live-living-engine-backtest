from pathlib import Path

import yaml

from runner.backtest import run_backtest


def test_strategy_smoke(tmp_path):
    params = yaml.safe_load(Path("configs/default.yaml").read_text())
    metrics = run_backtest("data/sample_prices.csv", params, tmp_path)

    assert "final_equity" in metrics
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "summary.txt").exists()

    logging_cfg = params.get("logging", {})
    assert (tmp_path / logging_cfg.get("BlotterFile", "trades.csv")).exists()

    if logging_cfg.get("EnableProofBridge", True):
        assert (tmp_path / logging_cfg.get("ProofCapsuleFile", "capsules.jsonl")).exists()
        assert (tmp_path / logging_cfg.get("ProofLedgerFile", "proof_ledger.csv")).exists()
