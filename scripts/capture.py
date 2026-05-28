#!/usr/bin/env python3
"""Fetch the current Hacker News top stories and append a snapshot.

Run locally or on a schedule (see .github/workflows/capture.yml) to build
up the history that powers the risers board.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radar import storage  # noqa: E402
from radar.sources import fetch_top_stories  # noqa: E402


def main(limit: int = 50) -> None:
    df = pd.DataFrame(fetch_top_stories(limit=limit))
    captured_at = storage.save_snapshot(df)
    print(
        f"Captured {len(df)} stories at {captured_at} "
        f"(total snapshots: {storage.snapshot_count()})"
    )


if __name__ == "__main__":
    main()
