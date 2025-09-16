import math

import pytest

from engine.metrics import summarize_equity


def test_summarize_equity_basic():
    equity = [100_000, 101_000, 99_000, 103_000]
    bars = [
        {"timestamp": f"2023-01-0{i}T00:00:00+00:00", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}
        for i in range(1, 4)
    ]

    metrics = summarize_equity(equity, bars)
    assert metrics["final_equity"] == 103_000
    assert metrics["max_drawdown"] == pytest.approx(0.0198019, rel=1e-4)
    assert math.isfinite(metrics["sharpe"])
    assert metrics["bars_processed"] == 3


def test_summarize_equity_requires_data():
    bars = [{"timestamp": "2023-01-01T00:00:00+00:00", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
    with pytest.raises(ValueError):
        summarize_equity([], bars)

    with pytest.raises(ValueError):
        summarize_equity([100], [])
