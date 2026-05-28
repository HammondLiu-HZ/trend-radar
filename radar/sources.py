"""Data sources for Trend Radar.

Currently supports Hacker News via its public Firebase API
(no API key required): https://github.com/HackerNews/API
"""
from __future__ import annotations

import concurrent.futures as cf
from typing import Any

import httpx

HN_BASE = "https://hacker-news.firebaseio.com/v0"
_TIMEOUT = httpx.Timeout(10.0)


def _get_json(client: httpx.Client, url: str) -> Any:
    resp = client.get(url)
    resp.raise_for_status()
    return resp.json()


def fetch_top_story_ids(client: httpx.Client, limit: int) -> list[int]:
    ids = _get_json(client, f"{HN_BASE}/topstories.json")
    return ids[:limit]


def fetch_item(client: httpx.Client, item_id: int) -> dict[str, Any] | None:
    return _get_json(client, f"{HN_BASE}/item/{item_id}.json")


def fetch_top_stories(limit: int = 30, max_workers: int = 16) -> list[dict[str, Any]]:
    """Return the current HN top stories with details, in ranked order."""
    with httpx.Client(timeout=_TIMEOUT) as client:
        ids = fetch_top_story_ids(client, limit)
        with cf.ThreadPoolExecutor(max_workers=max_workers) as pool:
            items = list(pool.map(lambda i: fetch_item(client, i), ids))

    stories: list[dict[str, Any]] = []
    for rank, item in enumerate(items, start=1):
        if not item or item.get("type") != "story":
            continue
        item_id = item["id"]
        stories.append(
            {
                "rank": rank,
                "id": item_id,
                "title": item.get("title", ""),
                "score": item.get("score", 0),
                "comments": item.get("descendants", 0),
                "by": item.get("by", ""),
                "time": item.get("time", 0),
                "url": item.get("url") or f"https://news.ycombinator.com/item?id={item_id}",
                "hn_url": f"https://news.ycombinator.com/item?id={item_id}",
            }
        )
    return stories
