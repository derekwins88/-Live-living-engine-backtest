"""Backtest runner for the Living Engine."""
from __future__ import annotations

import json
from contextlib import nullcontext
from pathlib import Path
from typing import Dict

from engine.data import load_ohlcv
from engine.metrics import summarize_equity
from engine.narrative import make_day_summary
from engine.proofbridge import ProofBridge
from engine.strategies.imm_core_v11 import ImmCoreV11


def run_backtest(data_path: Path | str, params: Dict, outdir: Path | str):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    bars = load_ohlcv(data_path, params.get("resample"))
    strategy = ImmCoreV11(params)
    cash = float(params.get("starting_cash", 50_000.0))
    position = 0.0
    equity_curve = [cash]
    trades: list[dict] = []

    logging_cfg = params.get("logging", {})
    blotter_name = logging_cfg.get("BlotterFile", "trades.csv")
    proof_capsule_name = logging_cfg.get("ProofCapsuleFile", "capsules.jsonl")
    proof_enabled = bool(logging_cfg.get("EnableProofBridge", True))
    proof_ledger_name = logging_cfg.get("ProofLedgerFile", "proof_ledger.csv")

    strategy.on_start()
    bridge_ctx = (
        ProofBridge(outdir / proof_ledger_name, outdir / proof_capsule_name)
        if proof_enabled
        else nullcontext(None)
    )

    with bridge_ctx as pb:
        for bar in bars:
            order, capsule = strategy.on_bar(bar)
            if capsule and pb:
                pb.write_capsule(bar["timestamp"], capsule)

            if order:
                if order.get("side") == "long" and position == 0:
                    price = float(order.get("price", bar["close"]))
                    size = float(order.get("size", 1.0))
                    position = size
                    cash -= size * price
                    trades.append({"ts": bar["timestamp"], "action": "BUY", "px": price})
                elif order.get("side") == "flat" and position != 0:
                    price = float(order.get("price", bar["close"]))
                    cash += position * price
                    trades.append({"ts": bar["timestamp"], "action": "SELL", "px": price})
                    position = 0.0

            equity_curve.append(cash + position * bar["close"])

        strategy.on_finish()
        metrics = summarize_equity(equity_curve, bars)

        (outdir / "metrics.json").write_text(json.dumps(metrics, indent=2))
        trades_lines = ["ts,action,px"] + [f"{t['ts']},{t['action']},{t['px']}" for t in trades]
        (outdir / blotter_name).write_text("\n".join(trades_lines))
        pb_stats = pb.stats() if pb else {"capsules_written": 0}
        summary = make_day_summary(metrics, pb_stats)
        (outdir / "summary.txt").write_text(summary)

    return metrics


__all__ = ["run_backtest"]
