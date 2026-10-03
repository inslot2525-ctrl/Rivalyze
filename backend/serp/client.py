"""SerpApi access for Rivalyze: one place for caching, budgeting and tracing.

Every search goes through `SerpClient.search`. Responses are cached on disk by a
hash of (engine, params), so repeating a scan costs nothing, and each call is
recorded so the UI can show exactly what was searched.
"""
import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import serpapi

from config import settings

# Hours a cached response stays fresh, per engine. Slow-moving data lives longer.
TTL_HOURS = {
    "google_news": 12,
    "google_jobs": 24,
    "google_finance": 6,
    "google_ai_mode": 72,
    "google_trends": 72,
    "google_patents": 24 * 14,
    "google_autocomplete": 24 * 14,
}
DEFAULT_TTL_HOURS = 48

DROP_KEYS = ("search_metadata", "search_parameters", "pagination", "serpapi_pagination")
# Bulky fields nothing reads (inline base64 images, chart points). Dropped before caching.
HEAVY_KEYS = {"thumbnail", "thumbnail_small", "favicon", "source_icon", "serpapi_link", "redirect_link",
              "figures", "graph", "job_id", "about_this_result", "about_page_link",
              "about_page_serpapi_link", "serpapi_details_link", "icon"}
# SerpApi reports an empty result page as an error. It is an answer, and worth caching.
EMPTY_RESULT = "hasn't returned any results"


def prune(node):
    """Strip heavy fields from a response, recursively."""
    if isinstance(node, dict):
        return {k: prune(v) for k, v in node.items() if k not in HEAVY_KEYS}
    if isinstance(node, list):
        return [prune(v) for v in node]
    return node


class BudgetExceeded(Exception):
    pass


class SearchUnavailable(Exception):
    """No cached response and no API key to fetch a live one."""


@dataclass
class CallMeta:
    engine: str
    params: dict
    cached: bool
    ms: int
    fetched_at: str
    error: Optional[str] = None


def cache_key(engine: str, params: dict) -> str:
    blob = json.dumps({"engine": engine, **params}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


class SerpClient:
    def __init__(self, budget: Optional[int] = None, cache_dir: Optional[Path] = None,
                 api_key: Optional[str] = None):
        self.budget = settings.scan_search_budget if budget is None else budget
        self.cache_dir = Path(cache_dir or settings.cache_dir)
        self.api_key = settings.serpapi_api_key if api_key is None else api_key
        self.live_calls = 0
        self.cache_hits = 0
        self.calls: list[CallMeta] = []
        self._locks: dict[str, asyncio.Lock] = {}

    @property
    def remaining(self) -> int:
        return max(self.budget - self.live_calls, 0)

    def _path(self, engine: str, key: str) -> Path:
        return self.cache_dir / engine / f"{key}.json"

    def _read_cache(self, engine: str, key: str) -> Optional[dict]:
        path = self._path(engine, key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _is_fresh(self, engine: str, entry: dict) -> bool:
        fetched = datetime.fromisoformat(entry["fetched_at"])
        age_h = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
        return age_h < TTL_HOURS.get(engine, DEFAULT_TTL_HOURS)

    def _fetch(self, engine: str, params: dict) -> dict:
        client = serpapi.Client(api_key=self.api_key, timeout=40)
        try:
            results = client.search({"engine": engine, **params})
        except serpapi.SerpApiError as e:
            return {"error": str(e)[:300]}
        data = results.as_dict() if hasattr(results, "as_dict") else dict(results)
        for k in DROP_KEYS:
            data.pop(k, None)
        return prune(data)

    async def search(self, engine: str, **params) -> tuple[dict, CallMeta]:
        """Return (response, meta). Serves cache when fresh; otherwise spends one search."""
        params = {k: v for k, v in params.items() if v is not None}
        key = cache_key(engine, params)
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            start = time.perf_counter()
            entry = self._read_cache(engine, key)
            can_fetch = bool(self.api_key) and self.remaining > 0

            # A stale entry is still better than nothing when we cannot fetch.
            if entry and (self._is_fresh(engine, entry) or not can_fetch):
                self.cache_hits += 1
                meta = CallMeta(engine, params, True, int((time.perf_counter() - start) * 1000),
                                entry["fetched_at"])
                self.calls.append(meta)
                return entry["data"], meta

            if not self.api_key:
                raise SearchUnavailable(f"No SERPAPI_API_KEY set and no cached {engine} result")
            if self.remaining <= 0:
                raise BudgetExceeded(f"Scan search budget of {self.budget} is spent")

            self.live_calls += 1
            data = await asyncio.to_thread(self._fetch, engine, params)
            fetched_at = datetime.now(timezone.utc).isoformat()
            if EMPTY_RESULT in (data.get("error") or ""):
                data = {"empty": True}
            if not data.get("error"):
                path = self._path(engine, key)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(
                    {"engine": engine, "params": params, "fetched_at": fetched_at, "data": data},
                    ensure_ascii=False), encoding="utf-8")
            meta = CallMeta(engine, params, False, int((time.perf_counter() - start) * 1000),
                            fetched_at, error=data.get("error"))
            self.calls.append(meta)
            return data, meta


async def account_usage() -> dict:
    """Plan and remaining searches. This endpoint is free and does not spend a search."""
    if not settings.serpapi_api_key:
        return {"live": False}
    try:
        info = await asyncio.to_thread(lambda: dict(serpapi.Client(
            api_key=settings.serpapi_api_key, timeout=15).account()))
        return {
            "live": True,
            "plan": info.get("plan_name"),
            "searches_left": info.get("total_searches_left"),
            "searches_per_month": info.get("searches_per_month"),
            "this_month_usage": info.get("this_month_usage"),
        }
    except Exception as e:  # account lookup is cosmetic; never fail a request over it
        return {"live": True, "error": str(e)[:200]}
