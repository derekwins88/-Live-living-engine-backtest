"""Narrative helper for the "Book Builder" summary."""
from __future__ import annotations

from typing import Dict


def make_day_summary(metrics: Dict[str, float], pb_stats: Dict[str, int]) -> str:
    verdict = "cautious" if metrics.get("max_drawdown", 0) > 0.15 else "confident"
    return (
        f"Day Summary — The Engine felt {verdict}.\n"
        f"CAGR(est): {metrics.get('cagr_est', 0.0):.2%}, "
        f"Sharpe: {metrics.get('sharpe', 0.0):.2f}, "
        f"MaxDD: {metrics.get('max_drawdown', 0.0):.2%}\n"
        f"Capsules generated: {pb_stats.get('capsules_written', 0)}.\n"
        f"Translation: complexity spikes were"
        f"{' not' if verdict == 'confident' else ''} frequent; risk posture "
        f"{'remained measured' if verdict == 'cautious' else 'opened selectively'}.\n"
    )


__all__ = ["make_day_summary"]
