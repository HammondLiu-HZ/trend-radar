"""Snapshot persistence for Trend Radar (CSV).

Each fetch is appended as a timestamped snapshot to a single CSV file.
A CSV (rather than a binary DB) keeps history diff-friendly so the
scheduled GitHub Action can commit it, and the deployed app reads the
same file to compute risers across restarts.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_CSV_PATH = os.path.join(_DATA_DIR, "snapshots.csv")
_COLS = ["captured_at", "story_id", "rank", "title", "score", "comments"]


def _read_all() -> pd.DataFrame:
    if not os.path.exists(_CSV_PATH):
        return pd.DataFrame(columns=_COLS)
    return pd.read_csv(_CSV_PATH)


def save_snapshot(df: pd.DataFrame, captured_at: str | None = None) -> str:
    """Append a ranked snapshot. Returns the capture timestamp used."""
    if df.empty:
        return ""
    captured_at = captured_at or datetime.now(timezone.utc).isoformat()
    rows = df[["id", "rank", "title", "score", "comments"]].rename(
        columns={"id": "story_id"}
    )
    rows.insert(0, "captured_at", captured_at)
    os.makedirs(_DATA_DIR, exist_ok=True)
    rows.to_csv(_CSV_PATH, mode="a", header=not os.path.exists(_CSV_PATH), index=False)
    return captured_at


def load_previous_snapshot() -> pd.DataFrame:
    """Return the most recent stored snapshot (read before saving a new one)."""
    data = _read_all()
    if data.empty:
        return pd.DataFrame()
    latest = data["captured_at"].max()
    return data[data["captured_at"] == latest].copy()


def snapshot_count() -> int:
    data = _read_all()
    return 0 if data.empty else int(data["captured_at"].nunique())
