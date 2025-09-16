"""Simplified IMM Cognitive Core v11 strategy implementation."""
from __future__ import annotations

import math
from collections import deque
from statistics import fmean, pstdev
from typing import Dict, Tuple

from ..strategy_api import Capsule, Order, StrategyBase


class ImmCoreV11(StrategyBase):
    """A lightweight port of the IMM Cognitive Core v11 idea."""

    def __init__(self, params: Dict[str, float]):
        super().__init__(params)

        signals = params.get("signals", {})
        entropy_cfg = params.get("entropy", {})

        self.lookback_fast = int(signals.get("EmaFast", params.get("lookback_fast", 12)))
        self.lookback_slow = int(signals.get("EmaSlow", params.get("lookback_slow", 48)))
        self.atr_period = int(signals.get("AtrPeriod", params.get("atr_period", 14)))
        self.stop_atr_mult = float(signals.get("StopAtrMult", params.get("stop_atr_mult", 0.0)))
        self.trail_mult = float(signals.get("TrailMult", params.get("trail_mult", 1.0)))

        self.entropy_window = int(
            entropy_cfg.get("EntropyLookback", params.get("entropy_window", 20))
        )
        self.entropy_threshold = float(
            entropy_cfg.get("P_threshold", params.get("entropy_threshold", 0.02))
        )
        collapse_default = self.entropy_threshold * 1.5
        self.entropy_exit = float(
            entropy_cfg.get("CollapseThreshold", params.get("entropy_exit", collapse_default))
        )
        self.np_threshold = float(entropy_cfg.get("NP_threshold", self.entropy_exit))
        self.recovery_window = int(entropy_cfg.get("RecoveryWindow", 0))

        self.ma_buffer = float(params.get("ma_buffer", 0.0))
        self.unit_size = float(params.get("unit_size", 1.0))
        maxlen = max(self.lookback_slow, self.entropy_window, self.atr_period) + 1
        self.state.update(
            closes=deque(maxlen=maxlen),
            highs=deque(maxlen=maxlen),
            lows=deque(maxlen=maxlen),
            true_ranges=deque(maxlen=self.atr_period),
            prev_close=None,
            position=0.0,
            in_collapse=False,
            recovery_count=0,
        )

    def on_start(self) -> None:
        self.state["closes"].clear()
        self.state["highs"].clear()
        self.state["lows"].clear()
        self.state["true_ranges"].clear()
        self.state["prev_close"] = None
        self.state["position"] = 0.0
        self.state["in_collapse"] = False
        self.state["recovery_count"] = 0

    def _update_collapse_state(self, entropy_value: float) -> None:
        if self.recovery_window <= 0:
            self.state["in_collapse"] = False
            self.state["recovery_count"] = 0
            return

        if entropy_value >= self.entropy_exit:
            self.state["in_collapse"] = True
            self.state["recovery_count"] = 0
        elif self.state["in_collapse"]:
            if entropy_value < self.np_threshold:
                self.state["recovery_count"] += 1
                if self.state["recovery_count"] >= self.recovery_window:
                    self.state["in_collapse"] = False
            else:
                self.state["recovery_count"] = 0

    def _classify_regime(self, entropy_value: float) -> str:
        if entropy_value >= self.entropy_exit:
            return "COLLAPSE"
        if entropy_value < self.entropy_threshold:
            return "P"
        if entropy_value < self.np_threshold:
            return "NP"
        return "DRIFT"

    def _compute_indicators(self) -> Tuple[float, float, float, float]:
        closes = list(self.state["closes"])
        fast = fmean(closes[-self.lookback_fast:])
        slow = fmean(closes[-self.lookback_slow:])
        atr = fmean(self.state["true_ranges"]) if self.state["true_ranges"] else 0.0
        window = closes[-self.entropy_window :]
        returns = []
        for prev, curr in zip(window, window[1:]):
            if prev != 0:
                returns.append((curr - prev) / prev)
        entropy = pstdev(returns) if len(returns) > 1 else 0.0
        return fast, slow, atr, entropy

    def on_bar(self, bar: Dict[str, float]):
        closes = self.state["closes"]
        highs = self.state["highs"]
        lows = self.state["lows"]
        closes.append(bar["close"])
        highs.append(bar["high"])
        lows.append(bar["low"])

        prev_close = self.state["prev_close"]
        tr = bar["high"] - bar["low"]
        if prev_close is not None:
            tr = max(tr, abs(bar["high"] - prev_close), abs(bar["low"] - prev_close))
        self.state["true_ranges"].append(tr)
        self.state["prev_close"] = bar["close"]

        order: Order = None
        capsule: Capsule = None

        if len(closes) >= self.lookback_slow and len(self.state["true_ranges"]) >= self.atr_period:
            fast, slow, atr, entropy_estimate = self._compute_indicators()
            if "entropy" in bar:
                try:
                    entropy_value = float(bar["entropy"])
                except (TypeError, ValueError):
                    entropy_value = entropy_estimate
                    entropy_source = "derived"
                else:
                    if math.isnan(entropy_value):
                        entropy_value = entropy_estimate
                        entropy_source = "derived"
                    else:
                        entropy_source = "market"
            else:
                entropy_value = entropy_estimate
                entropy_source = "derived"
            self._update_collapse_state(entropy_value)
            glyph = "⧖" if entropy_value <= self.entropy_threshold else "⌛"
            verdict = "LONG" if self.state["position"] else "FLAT"
            regime = self._classify_regime(entropy_value)
            capsule = {
                "glyph": glyph,
                "entropy": entropy_value,
                "atr": atr,
                "fast_ma": fast,
                "slow_ma": slow,
                "verdict": verdict,
                "regime": regime,
                "collapse_guard": self.state["in_collapse"],
                "recovery_count": self.state["recovery_count"],
                "entropy_source": entropy_source,
            }

            enter_condition = (
                self.state["position"] == 0
                and fast > slow * (1 + self.ma_buffer)
                and entropy_value < self.entropy_threshold
                and not self.state["in_collapse"]
            )
            exit_condition = (
                self.state["position"] != 0
                and (
                    fast < slow * (1 - self.ma_buffer)
                    or entropy_value > self.entropy_exit
                    or self.state["in_collapse"]
                )
            )

            if enter_condition:
                order = {
                    "side": "long",
                    "size": self.unit_size,
                    "price": bar["close"],
                }
                self.state["position"] = self.unit_size
                capsule["verdict"] = "LONG"
            elif exit_condition:
                order = {
                    "side": "flat",
                    "size": self.state["position"],
                    "price": bar["close"],
                }
                self.state["position"] = 0.0
                capsule["verdict"] = "FLAT"

        return order, capsule

    def on_finish(self) -> None:
        self.state["position"] = 0.0


__all__ = ["ImmCoreV11"]
