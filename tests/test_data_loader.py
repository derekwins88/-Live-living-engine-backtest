from engine.data import load_ohlcv


def test_load_ohlcv_preserves_optional_columns():
    bars = load_ohlcv("data/sample_prices.csv")

    assert bars, "Expected sample prices to yield at least one bar"
    first = bars[0]
    assert "entropy" in first and "symbol" in first
    assert isinstance(first["entropy"], float)
    assert first["symbol"] == "CL"
