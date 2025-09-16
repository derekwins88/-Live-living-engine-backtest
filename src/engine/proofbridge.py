"""Simple ProofBridge ledger writers."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict


class ProofBridge:
    """Persist strategy capsules to CSV and JSONL ledgers."""

    def __init__(self, csv_path: Path, jsonl_path: Path):
        self.csv_path = Path(csv_path)
        self.jsonl_path = Path(jsonl_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

        self._csv_file = self.csv_path.open("w", newline="")
        self._writer = csv.DictWriter(
            self._csv_file, fieldnames=["ts", "glyph", "entropy", "verdict"]
        )
        self._writer.writeheader()

        self._jsonl_file = self.jsonl_path.open("w")
        self._count = 0

    def write_capsule(self, ts: str, capsule: Dict[str, object]) -> None:
        row = {
            "ts": ts,
            "glyph": capsule.get("glyph"),
            "entropy": capsule.get("entropy"),
            "verdict": capsule.get("verdict", "OPEN"),
        }
        self._writer.writerow(row)
        payload = {"ts": ts, **capsule}
        self._jsonl_file.write(json.dumps(payload) + "\n")
        self._count += 1

    def stats(self) -> Dict[str, int]:
        return {"capsules_written": self._count}

    def close(self) -> None:
        try:
            self._csv_file.close()
        finally:
            self._jsonl_file.close()

    def __enter__(self) -> "ProofBridge":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - guard for GC finaliser
        try:
            self.close()
        except Exception:
            pass


__all__ = ["ProofBridge"]
