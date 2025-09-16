"""Strategy interface definitions for the Living Engine backtester."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


BarData = Dict[str, Any]
Order = Optional[Dict[str, Any]]
Capsule = Optional[Dict[str, Any]]


class StrategyBase:
    """Base class that trading strategies should inherit from.

    Subclasses must implement :meth:`on_bar` and can optionally override
    :meth:`on_start` and :meth:`on_finish` hooks to set up and tear down state.
    """

    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.state: Dict[str, Any] = {}

    def on_start(self) -> None:
        """Called once before the backtest begins."""

    def on_finish(self) -> None:
        """Called once after the backtest ends."""

    def on_bar(self, bar: BarData) -> Tuple[Order, Capsule]:
        """Handle an incoming bar.

        Implementations should return a tuple ``(order, capsule)`` where:

        * ``order`` is ``None`` or a dictionary with the desired action.
        * ``capsule`` is ``None`` or a dictionary to persist via ProofBridge.
        """

        raise NotImplementedError


__all__ = ["StrategyBase", "BarData", "Order", "Capsule"]
