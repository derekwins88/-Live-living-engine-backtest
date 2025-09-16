"""Helpers for working with NinjaTrader 8 exports."""
from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


def load_nt8_signals(path: Path | str) -> List[dict]:
    """Load NinjaTrader 8 signal exports into a uniform structure."""

    df = pd.read_csv(path)
    required = {"Time", "Signal", "Price"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise ValueError(f"missing columns in NT8 export: {sorted(missing)}")

    df["Time"] = pd.to_datetime(df["Time"], utc=True)
    df = df.sort_values("Time")
    return [
        {"timestamp": row.Time.isoformat(), "signal": row.Signal, "price": float(row.Price)}
        for row in df.itertuples(index=False)
    ]


__all__ = ["load_nt8_signals"]
