"""Performance metric helpers for the Living Engine backtester."""
from __future__ import annotations

import math
from typing import Sequence


def summarize_equity(equity: Sequence[float], bars: Sequence[dict]) -> dict:
    """Create a dictionary of headline performance metrics."""

    if not equity:
        raise ValueError("equity series cannot be empty")
    if not bars:
        raise ValueError("bars cannot be empty")

    returns = []
    for idx in range(1, len(equity)):
        prev = equity[idx - 1]
        if prev == 0:
            continue
        change = (equity[idx] - prev) / prev
        returns.append(change)

    mean_return = sum(returns) / len(returns) if returns else 0.0
    variance = (
        sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        if len(returns) > 1
        else 0.0
    )
    std_dev = math.sqrt(variance) if variance > 0 else 0.0
    sharpe = 0.0
    if std_dev > 0:
        sharpe = (mean_return / std_dev) * math.sqrt(252)
    elif mean_return != 0:
        sharpe = math.copysign(float("inf"), mean_return)

    peak = equity[0]
    max_drawdown = 0.0
    for value in equity:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)

    starting = equity[0]
    ending = equity[-1]
    bar_count = len(bars)
    if bar_count > 252 and starting > 0:
        cagr = (ending / starting) ** (252 / bar_count) - 1
    elif starting > 0:
        cagr = ending / starting - 1
    else:
        cagr = 0.0

    return {
        "final_equity": ending,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "cagr_est": cagr,
        "return": ending / starting - 1 if starting else 0.0,
        "bars_processed": bar_count,
    }


__all__ = ["summarize_equity"]
