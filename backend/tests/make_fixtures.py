"""Copy the cached responses the tests rely on into tests/fixtures (pruned).

Run from backend/ after a live Notion scan:  python -m tests.make_fixtures
"""
import json
from pathlib import Path

from config import settings
from serp.client import cache_key, prune

FIXTURES = Path(__file__).parent / "fixtures"

WANTED = [
    ("google_autocomplete", {"q": "Notion vs "}),
    ("google", {"q": "Notion company", "hl": "en", "gl": "us"}),
    ("google_jobs", {"q": "Notion", "hl": "en", "gl": "us"}),
    ("google_jobs", {"q": "Atlassian", "hl": "en", "gl": "us"}),
    ("google_news", {"q": '"Notion Labs" OR "Notion workspace" OR "Ivan Zhao"', "hl": "en", "gl": "us"}),
    ("google_trends", {"q": "Notion,Confluence,Coda,Airtable,ClickUp", "data_type": "TIMESERIES",
                       "date": "today 12-m"}),
    ("google_patents", {"assignee": "Notion Labs", "sort": "new",
                        "q": "(system OR method OR device OR apparatus OR composition)"}),
    ("google_ads_transparency_center", {"text": "notion.so"}),
    ("google_finance", {"q": "TSLA:NASDAQ", "hl": "en"}),
    ("google_ai_mode", {"q": "What are the main criticisms of Notion AI and its pricing?"}),
]

if __name__ == "__main__":
    for engine, params in WANTED:
        key = cache_key(engine, params)
        src = settings.cache_dir / engine / f"{key}.json"
        entry = json.loads(src.read_text(encoding="utf-8"))
        entry["data"] = prune(entry["data"])
        dst = FIXTURES / engine / f"{key}.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        print(f"{dst.stat().st_size // 1024:>4} KB  {engine}  {params}")
