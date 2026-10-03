"""Offline tests: everything here runs against recorded SerpApi responses."""
from datetime import datetime, timezone

import pytest

import analytics
import storage
from agents.grounding import ground, scrub
from agents.pipeline import Scan
from battlecard import battlecard
from serp.client import BudgetExceeded, SearchUnavailable, SerpClient, cache_key, prune
from serp.collectors import same_company

pytestmark = pytest.mark.asyncio


# ---- client ------------------------------------------------------------------

async def test_cache_hit_spends_nothing(serp):
    data, meta = await serp.search("google_autocomplete", q="Notion vs ")
    assert meta.cached and data["suggestions"]
    assert serp.live_calls == 0 and serp.cache_hits == 1


async def test_no_key_and_no_cache_raises(serp):
    with pytest.raises(SearchUnavailable):
        await serp.search("google", q="a query nobody recorded")


async def test_budget_is_enforced(tmp_path):
    client = SerpClient(budget=0, cache_dir=tmp_path, api_key="not-a-real-key")
    with pytest.raises(BudgetExceeded):
        await client.search("google", q="anything")


async def test_cache_key_ignores_param_order():
    assert cache_key("google", {"q": "x", "hl": "en"}) == cache_key("google", {"hl": "en", "q": "x"})


async def test_prune_drops_heavy_fields():
    assert prune({"a": [{"thumbnail": "data:...", "title": "t"}]}) == {"a": [{"title": "t"}]}


# ---- collectors --------------------------------------------------------------

async def test_rivals_come_from_autocomplete(collect, store):
    names = await collect.rivals("Notion")
    assert "obsidian" in names and "notion" not in names
    assert all(e.engine == "google_autocomplete" for e in store.by_signal("rivals"))


async def test_web_search_yields_three_signals(collect, store):
    await collect.web("Notion")
    assert store.by_signal("web") and store.by_signal("doubts") and store.by_signal("ai_view")


async def test_jobs_keeps_only_the_employer(collect, store):
    result = await collect.jobs("Notion")
    assert result["roles"] and len(result["roles"]) < result["returned"]  # the Upwork gig is dropped
    assert all(e.link for e in store.by_signal("hiring"))


async def test_rival_jobs_are_filed_under_the_rival(collect, store):
    await collect.jobs("Atlassian", subject="Confluence")
    assert store.by_signal("hiring", "Confluence")


async def test_patents_and_ads_and_finance(collect, store):
    patents = await collect.patents("Notion", "Notion Labs, Inc.")  # suffix must be stripped
    assert patents["filings"] and patents["cpc"] and patents["single_owner"]
    ads = await collect.ads("Notion", "notion.so")
    assert ads["ads"] and ads["others_targeting_domain"] > 0
    assert all("Notion" in a["advertiser"] for a in ads["ads"])
    finance = await collect.finance("Tesla", "TSLA:NASDAQ")
    assert finance["price"] and finance["market_cap"]


async def test_same_company_matching():
    assert same_company("Notion Labs, Inc.", "Notion")
    assert same_company("Notion Labs Japan合同会社", "Notion")
    assert not same_company("Upwork", "Notion")
    assert not same_company("Notional Finance", "Notion")


# ---- analytics ---------------------------------------------------------------

async def test_job_functions():
    assert analytics.job_function("Payroll Analyst - Accounting") == "Finance / Legal"
    assert analytics.job_function("Software Engineer, Mobile Core (Android)") == "Engineering"
    assert analytics.job_function("Enterprise Outcomes Architect (Customer Success)") == "Customer"
    assert analytics.job_function("Senior AI Research Scientist") == "AI / ML"


async def test_trend_stats_measure_recent_change():
    series = [{"date": f"w{i}", "A": 80} for i in range(48)] + [{"date": f"r{i}", "A": 60} for i in range(4)]
    (s,) = analytics.trend_stats(series, ["A"])
    assert s["baseline_average"] == 80 and s["recent_average"] == 60 and s["change_pct"] == -25.0


async def test_scorecard_ranks_only_what_it_can_compare():
    compare = [{"name": "A", "trend_average": 50, "patents_total": 10},
               {"name": "B", "trend_average": 80},
               {"name": "C", "trend_average": 50, "patents_total": 40}]
    card = analytics.scorecard(compare, "A")
    demand, patents = card["rows"]
    assert (demand["leader"], demand["target_rank"], demand["of"]) == ("B", 2, 3)  # tie shares rank 2
    assert (patents["leader"], patents["target_rank"], patents["of"]) == ("C", 2, 2)  # B is left out
    assert card["leads"] == 0 and card["measures"] == 2

    ahead, behind = analytics.standing_points(card, "A")
    assert ahead == [] and [b["versus"] for b in behind] == ["B", "C"]
    assert behind[0]["point"] == "Search demand: B leads at 80. A is 2nd of 3 at 50."
    ahead, _ = analytics.standing_points(analytics.scorecard(compare, "B"), "B")
    assert ahead[0]["point"] == "Search demand: B leads at 80, ahead of A at 50."


async def test_thin_trends_have_no_momentum():
    series = [{"date": f"w{i}", "A": 1} for i in range(52)]
    assert analytics.trend_stats(series, ["A"])[0]["change_pct"] is None


async def test_news_velocity():
    now = datetime(2026, 10, 3, tzinfo=timezone.utc)
    stats = analytics.news_stats(["2026-10-02T00:00:00Z", "2026-09-24T00:00:00Z", "2026-07-01T00:00:00Z"],
                                 ["A", "A", "B"], now=now)
    assert (stats["last_7_days"], stats["previous_7_days"], stats["last_30_days"]) == (1, 1, 2)
    assert stats["top_sources"][0] == {"name": "A", "count": 2}


# ---- grounding ---------------------------------------------------------------

async def _evidence(collect):
    await collect.web("Notion")
    await collect.jobs("Notion")
    await collect.patents("Notion", "Notion Labs")
    await collect.news("Notion", '"Notion Labs" OR "Notion workspace" OR "Ivan Zhao"')


async def test_claims_without_receipts_are_dropped(collect, store, analysis):
    await _evidence(collect)
    grounded, stats = ground(analysis, store)
    assert [t["headline"] for t in grounded["tells"]] == ["Mobile core hiring"]
    assert grounded["tells"][0]["evidence_ids"] == ["J1"]  # the invented J999 is removed
    assert stats["claims_dropped"] >= 2 and stats["citations_removed"] >= 2
    assert grounded["rivals"] == []  # T2 was never collected


async def test_say_vs_do_needs_an_involuntary_signal(collect, store, analysis):
    await _evidence(collect)
    grounded, _ = ground(analysis, store)
    assert [s["topic"] for s in grounded["say_vs_do"]] == ["AI"]


async def test_confidence_is_capped_by_corroboration(collect, store, analysis):
    await _evidence(collect)
    grounded, stats = ground(analysis, store)
    by_name = {f["prediction"]: f for f in grounded["forecasts"]}
    assert by_name["Rebuilt Android app"]["confidence"] == 75      # two signals
    assert by_name["Single-signal guess"]["confidence"] == 55      # one signal
    assert stats["confidence_capped"] == 2


async def test_inline_citations_are_scrubbed(collect, store):
    await _evidence(collect)
    assert scrub("Real [J1, Z9] and fake [Z9] and [METRICS, P1].", store) == "Real [J1] and fake and [P1]."


# ---- pipeline, storage, export -----------------------------------------------

async def test_scan_runs_offline_end_to_end(serp, fake_llm):
    events = []

    async def emit(event):
        events.append(event)

    report = await Scan("Notion", emit=emit, serp=serp, llm=fake_llm, plan_cache=False).run()

    assert report["usage"]["live_searches"] == 0
    assert {"google", "google_autocomplete", "google_jobs", "google_news", "google_trends",
            "google_patents", "google_ads_transparency_center", "google_ai_mode"} <= set(report["usage"]["engines"])
    assert [e["stage"] for e in events if e["type"] == "stage"] == [
        "scout", "plan", "collect", "critique", "followup", "analyse", "ground"]
    # Coda's postings were never recorded: the scan notes it and carries on.
    assert any(e["type"] == "note" and "jobs:Coda" in e["text"] for e in events)

    # Every citation that survives points at evidence in the report.
    a = report["analysis"]
    cited = [i for t in a["tells"] for i in t["evidence_ids"]] + \
            [i for f in a["forecasts"] for i in f["evidence_ids"]] + \
            [i for r in a["rivals"] for i in r["evidence_ids"]]
    assert cited and all(i in report["evidence"] for i in cited)
    assert a["rivals"][0]["name"] == "Confluence"  # T2 exists now that trends ran

    trends = report["metrics"]["trends"]
    assert trends["terms"][0] == "Notion" and len(trends["series"]) > 40
    assert report["metrics"]["ads"]["own_creatives"] > 0
    assert report["metrics"]["compare"][1]["name"] == "Confluence"
    assert report["metrics"]["compare"][1]["hiring_sample"] > 0

    card = report["metrics"]["scorecard"]
    assert card["rows"][0]["label"] == "Search demand" and card["rows"][0]["leader"] == "Notion"
    standing = a["standing"]
    assert standing["verdict"].endswith("fresh postings.")  # the invented [Z9] is scrubbed
    assert standing["ahead"][0]["point"].startswith("Search demand: Notion leads at")
    points = standing["ahead"] + standing["behind"]
    assert all(p["evidence_ids"] and all(i in report["evidence"] for i in p["evidence_ids"]) for p in points)
    assert report["metrics"]["compare"][1]["employer"] == "Atlassian"
    assert "## Where it stands" in battlecard(report)

    card = battlecard(report)
    assert "## What they will do next" in card and "## Receipts" in card and "**J1**" in card


async def test_diff_reports_finds_new_evidence():
    def report(titles, recent):
        return {"company": "Notion", "query": "Notion",
                "evidence": {f"J{i}": {"id": f"J{i}", "signal": "hiring", "subject": "Notion", "title": t,
                                       "link": f"https://jobs/{t}"} for i, t in enumerate(titles, 1)},
                "metrics": {"trends": {"stats": [{"term": "Notion", "recent_average": recent}]}},
                "analysis": {"forecasts": [{"prediction": "Same forecast", "evidence_ids": ["J1"]}]}}

    changes = storage.diff_reports(report(["Engineer"], 70), report(["Engineer", "Tokyo Sales Lead"], 80))
    assert [c["kind"] for c in changes] == ["New role", "Search demand moved"]
    assert changes[0]["title"] == "Tokyo Sales Lead"
