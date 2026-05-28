"""Compute trending 'risers' by diffing two snapshots."""
from __future__ import annotations

import pandas as pd


def compute_risers(
    current: pd.DataFrame, previous: pd.DataFrame, top_n: int = 8
) -> pd.DataFrame:
    """Rank stories by score gained since the previous snapshot.

    Stories absent from the previous snapshot are marked as new entries,
    using their current score as the gain so they surface in the board.
    """
    if current.empty or previous.empty:
        return pd.DataFrame()

    cur = current.rename(columns={"id": "story_id"})[
        ["story_id", "rank", "title", "score", "comments"]
    ].copy()
    prev = previous[["story_id", "rank", "score"]].rename(
        columns={"rank": "prev_rank", "score": "prev_score"}
    )

    merged = cur.merge(prev, on="story_id", how="left")
    is_new = merged["prev_score"].isna()
    merged["score_delta"] = (merged["score"] - merged["prev_score"]).fillna(
        merged["score"]
    )
    merged["rank_delta"] = merged["prev_rank"] - merged["rank"]
    merged["status"] = "📈 上升"
    merged.loc[is_new, "status"] = "🆕 新进榜"

    return merged.sort_values("score_delta", ascending=False).head(top_n)
