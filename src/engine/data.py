"""Utility helpers for loading OHLCV market data."""
from __future__ import annotations

from numbers import Number
from pathlib import Path
from typing import List, MutableMapping

import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}
_ALIAS_MAP = {
    "time": "timestamp",
    "date": "timestamp",
    "o": "open",
    "h": "high",
    "l": "low",
    "c": "close",
    "v": "volume",
}
_COLUMN_ORDER = ["timestamp", "open", "high", "low", "close", "volume"]


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {col: _ALIAS_MAP.get(col.lower(), col.lower()) for col in df.columns}
    df = df.rename(columns=renamed)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    ordered = _COLUMN_ORDER + [col for col in df.columns if col not in _COLUMN_ORDER]
    return df[ordered]


def load_ohlcv(path: Path | str, resample: str | None = None) -> List[MutableMapping[str, float]]:
    """Load OHLCV data from ``path``.

    Parameters
    ----------
    path:
        Input CSV or Parquet file.
    resample:
        Optional pandas resample rule (e.g. ``"5T"``) if data should be
        aggregated to a different timeframe.
    """

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file extension: {path.suffix}")

    df = _normalise_columns(df)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if df["timestamp"].isna().any():
        raise ValueError("Invalid timestamps encountered in OHLCV data")

    df = df.sort_values("timestamp").reset_index(drop=True)

    extra_columns = [col for col in df.columns if col not in _COLUMN_ORDER]

    if resample:
        agg = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
        df = (
            df.set_index("timestamp")
            .resample(resample)
            .agg(agg)
            .dropna()
            .reset_index()
        )

    records: List[MutableMapping[str, float]] = []
    for row in df.itertuples(index=False):
        record = {
            "timestamp": row.timestamp.isoformat(),
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
            "volume": float(row.volume),
        }

        for column in extra_columns:
            value = getattr(row, column)
            if isinstance(value, Number):
                record[column] = float(value)
            else:
                record[column] = value

        records.append(record)

    return records


__all__ = ["load_ohlcv"]
