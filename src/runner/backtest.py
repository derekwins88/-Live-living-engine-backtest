"""Backtest runner for the Living Engine."""
from __future__ import annotations

import json
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

    strategy.on_start()
    with ProofBridge(outdir / "proof_ledger.csv", outdir / "capsules.jsonl") as pb:
        for bar in bars:
            order, capsule = strategy.on_bar(bar)
            if capsule:
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
        (outdir / "trades.csv").write_text("\n".join(trades_lines))
        summary = make_day_summary(metrics, pb.stats())
        (outdir / "summary.txt").write_text(summary)

    return metrics


__all__ = ["run_backtest"]
