#!/usr/bin/env python3
"""Self-contained Living Engine backtest runner."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict

try:  # pragma: no cover - optional dependency shim
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback parser
    yaml = None


def read_yaml(path: str | Path) -> Dict[str, Any]:
    """Read a YAML configuration file with a minimal fallback parser."""
    path = Path(path)
    if yaml is None:
        output: Dict[str, Dict[str, Any]] = {}
        section: str | None = None
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if not raw_line.startswith(" "):
                key = raw_line.split(":", 1)[0].strip()
                output[key] = {}
                section = key
                continue
            if section is None:
                continue
            key_value = line.split(":", 1)
            if len(key_value) != 2:
                continue
            key, value = key_value[0], key_value[1].strip()
            lowered = value.lower()
            if lowered in {"true", "false"}:
                parsed: Any = lowered == "true"
            else:
                try:
                    parsed = float(value) if "." in value else int(value)
                except ValueError:
                    parsed = value.strip().strip('"').strip("'")
            output[section][key] = parsed
        return output
    return yaml.safe_load(path.read_text())


def sha256_file(path: str | Path) -> str:
    """Compute the SHA-256 hash of *path*."""
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def ema(previous: float, price: float, period: int) -> float:
    if period <= 1:
        return price
    alpha = 2.0 / (period + 1.0)
    return alpha * price + (1.0 - alpha) * previous


def run_backtest(cfg_path: str | Path, data_path: str | Path, outdir: str | Path) -> Dict[str, str]:
    outdir_path = Path(outdir)
    outdir_path.mkdir(parents=True, exist_ok=True)

    cfg = read_yaml(cfg_path)
    entropy_cfg = cfg.get("entropy", {})
    risk_cfg = cfg.get("risk", {})
    signal_cfg = cfg.get("signals", {})

    p_threshold = float(entropy_cfg.get("P_threshold"))
    np_threshold = float(entropy_cfg.get("NP_threshold"))
    collapse_threshold = float(entropy_cfg.get("CollapseThreshold"))

    risk_percent = float(risk_cfg.get("RiskPercent"))
    ema_fast_period = int(signal_cfg.get("EmaFast"))
    ema_slow_period = int(signal_cfg.get("EmaSlow"))

    rows = []
    with open(data_path, newline="") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            rows.append(
                {
                    "timestamp": record["timestamp"],
                    "symbol": record.get("symbol", ""),
                    "open": float(record["open"]),
                    "high": float(record["high"]),
                    "low": float(record["low"]),
                    "close": float(record["close"]),
                    "volume": float(record["volume"]),
                    "entropy": float(record.get("entropy", "0") or 0.0),
                }
            )

    if not rows:
        raise SystemExit("No data rows.")

    ema_fast = rows[0]["close"]
    ema_slow = rows[0]["close"]

    position = 0
    entry_price = 0.0
    cash = 50_000.0
    equity_curve = []
    trades: list[Dict[str, Any]] = []
    collapse_hits = 0
    open_windows = 0

    for row in rows:
        price = row["close"]
        ema_fast = ema(ema_fast, price, ema_fast_period)
        ema_slow = ema(ema_slow, price, ema_slow_period)

        equity_curve.append(cash + position * price)

        if row["entropy"] >= collapse_threshold:
            collapse_hits += 1
            open_windows += 1
        elif open_windows > 0:
            open_windows = max(0, open_windows - 1)

        if position and row["entropy"] >= np_threshold:
            cash += position * price
            trades.append({"ts": row["timestamp"], "action": "SELL", "px": price, "size": position})
            position = 0
            entry_price = 0.0
            equity_curve[-1] = cash
            continue

        if not position and row["entropy"] < p_threshold and ema_fast > ema_slow:
            stop_distance = price * 0.005
            risk_capital = cash * risk_percent
            size = max(1, int(risk_capital / max(1e-9, stop_distance)))
            cash -= size * price
            position = size
            entry_price = price
            trades.append({"ts": row["timestamp"], "action": "BUY", "px": price, "size": size})

    def sharpe(returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((value - mean) ** 2 for value in returns) / max(1, len(returns) - 1)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0
        return (mean / std_dev * math.sqrt(252)) if std_dev > 0 else 0.0

    returns: list[float] = []
    for idx in range(1, len(equity_curve)):
        previous = equity_curve[idx - 1]
        current = equity_curve[idx]
        returns.append((current - previous) / previous if previous else 0.0)

    peak = equity_curve[0]
    max_drawdown = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak if peak > 0 else 0.0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    metrics = {
        "start_equity": 50_000.0,
        "final_equity": equity_curve[-1],
        "num_trades": sum(1 for trade in trades if trade["action"] == "BUY"),
        "sharpe": sharpe(returns),
        "max_drawdown": max_drawdown,
    }

    blotter_path = outdir_path / "trades_blotter.csv"
    with open(blotter_path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ts", "action", "px", "size"])
        writer.writeheader()
        for trade in trades:
            writer.writerow(trade)

    data_hash = sha256_file(data_path)
    verdict = "OPEN"
    if collapse_hits > 0:
        verdict = "P≠NP (claim)"

    capsule = {
        "schema_version": "capsule-1.1.0",
        "created_utc": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "data_source": str(data_path),
        "data_sha256": data_hash,
        "params": cfg,
        "verdict": verdict,
        "evidence": {
            "collapse_hits": collapse_hits,
            "open_window": open_windows,
            "P_threshold": p_threshold,
            "NP_threshold": np_threshold,
            "collapse_threshold": collapse_threshold,
        },
        "metrics": metrics,
    }

    proof_path = outdir_path / "proof_capsule.json"
    proof_path.write_text(json.dumps(capsule, indent=2))
    (outdir_path / "metrics.json").write_text(json.dumps(metrics, indent=2))

    mood = "confident" if metrics["max_drawdown"] <= 0.15 else "cautious"
    summary_lines = [
        f"Day Summary — The Engine felt {mood}.",
        f"Sharpe: {metrics['sharpe']:.2f}  MaxDD: {metrics['max_drawdown']:.2%}  Trades: {metrics['num_trades']}  FinalEquity: {metrics['final_equity']:.2f}",
        f"Verdict: {verdict} (collapse hits: {collapse_hits})",
    ]
    (outdir_path / "summary.txt").write_text("\n".join(summary_lines) + "\n")

    return {
        "blotter": str(blotter_path),
        "proof_capsule": str(proof_path),
        "metrics": str(outdir_path / "metrics.json"),
        "summary": str(outdir_path / "summary.txt"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--data", default="data/sample_prices.csv")
    parser.add_argument("--out", default="runs/dev")
    args = parser.parse_args()

    paths = run_backtest(args.config, args.data, args.out)
    print(json.dumps(paths, indent=2))


if __name__ == "__main__":
    main()
