"""The scan pipeline.

    scout -> plan -> collect -> critique -> follow up -> analyse -> ground

Scout and collect are SerpApi searches. Plan, critique and analyse are LLM steps.
Ground is plain code that deletes any claim the evidence does not support. Every
step emits events, which the API streams to the browser as the scan runs.
"""
import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional

import analytics
from agents.grounding import ground
from agents.llm import LLM
from agents.schemas import Analysis, Critique, EvidenceStore, FollowUp, Plan
from config import settings
from serp.client import BudgetExceeded, CallMeta, SearchUnavailable, SerpClient
from serp.collectors import Collectors

Emit = Callable[[dict], Awaitable[None]]

PLAN_SYSTEM = """You resolve a company name into a research plan for a competitive-intelligence scan.
Use the search results provided to identify the right company. Pick rivals from the autocomplete
candidates when they are real direct competitors (same buyer, same budget); otherwise use your own
knowledge. Write rival names with their proper capitalisation. If the company name is also a common
word, make news_query unambiguous with quotes and distinguishing terms."""

CRITIC_SYSTEM = """You are the critic in a competitive-intelligence pipeline. You see the evidence
collected so far about a company. Decide which few extra searches would most sharpen or test a
prediction about the company's next move. Available kinds:
- ads: Google Ads Transparency Center. query = a domain. Already run for the company's main domain;
  only useful again for a second domain such as a regional or product site.
- ai_mode: Google AI Mode. query = a question such as what users criticise about the product. Shows
  how AI answers describe the company.
- jobs: Google Jobs. query = a targeted search like "<company> Tokyo" or "<company> enterprise sales".
- news: Google News. query = a targeted search about one specific development.
- patents: Google Patents within the company's filings. query = keywords, e.g. "(agent OR email)".
- web: Google Search. query = anything else, e.g. "<company> pricing change".
Only ask for searches whose answer would change the analysis. Do not repeat a search already run."""

ANALYST_SYSTEM = """You are Rivalyze, a competitive-intelligence analyst.

Your method: a company scripts its press releases, but it cannot hide what it hires for, what it
patents, what ads it buys, how search demand for it moves, or what people ask about it. Read those
involuntary signals and say what the company is actually doing and what it will do next.

Rules
- Every claim must cite evidence ids exactly as they appear in brackets, e.g. J3 or P2. Never invent
  an id. METRICS is not an id: cite the evidence the metric was computed from. Claims without valid
  citations are deleted automatically.
- Be specific: name roles, places, patent titles, dates and the numbers given under METRICS.
- Hiring evidence is a sample of live postings, not a headcount. Talk about direction and mix.
  An empty sample means the search matched nothing; it is not evidence that a company stopped hiring.
- A tell is strongest when two different signals agree; say so when they do.
- Say vs Do: "says" cites narrative or web evidence. "does" cites hiring, rnd, ads, demand, market,
  doubts or ai_view evidence. Look for where the two diverge, and say plainly when they agree.
- Forecasts are falsifiable moves: a launch, a market entry, a pricing change, an acquisition area,
  a hiring slowdown. Not vague trends. Give each a counter-move a competitor can start this week.
- News may contain articles about something else with the same name. Ignore those.
- Rival reads compare the rival against the target using the rival's own evidence.
- Plain language. No hype, no filler."""


PLAN_TTL = timedelta(days=7)


class ScanError(Exception):
    pass


class Scan:
    def __init__(self, company: str, include_rivals: bool = True, emit: Optional[Emit] = None,
                 serp: Optional[SerpClient] = None, llm: Optional[LLM] = None, plan_cache: bool = True):
        self.query = company.strip()
        self.include_rivals = include_rivals
        self.plan_cache = plan_cache
        self._emit = emit
        self.serp = serp or SerpClient()
        self.llm = llm or LLM()
        self.store = EvidenceStore()
        self.collect = Collectors(self.serp, self.store, self._trace)
        self.events: list[dict] = []
        self.trace: list[dict] = []
        self.metrics: dict = {}
        self._t0 = time.perf_counter()

    # ---- events ------------------------------------------------------------

    async def emit(self, type_: str, **data):
        event = {"type": type_, "t": round(time.perf_counter() - self._t0, 2), **data}
        if type_ != "report":
            self.events.append(event)
        if self._emit:
            await self._emit(event)

    async def _trace(self, meta: CallMeta, signal: str, label: str, results: int):
        call = {"engine": meta.engine, "signal": signal, "query": label, "cached": meta.cached,
                "ms": meta.ms, "results": results, "error": meta.error}
        self.trace.append(call)
        await self.emit("search", **call)

    async def _safe(self, name: str, coro):
        """Run one collector. A failed or unaffordable search degrades the scan, not ends it."""
        try:
            return await coro
        except (BudgetExceeded, SearchUnavailable) as e:
            await self.emit("note", text=f"Skipped {name}: {e}")
        except Exception as e:
            await self.emit("note", text=f"{name} failed: {str(e)[:160]}")
        return None

    # ---- stages ------------------------------------------------------------

    async def run(self) -> dict:
        company = self.query

        await self.emit("stage", stage="scout", text=f"Finding out who {company} is and who people compare it to")
        candidates, web = await asyncio.gather(
            self._safe("rival discovery", self.collect.rivals(company)),
            self._safe("web search", self.collect.web(company)))
        if not self.store.items:
            raise ScanError("No search results were available for this company. "
                            "Set SERPAPI_API_KEY or open one of the recorded demos.")
        candidates = candidates or []

        await self.emit("stage", stage="plan", text="Planning which signals to pull")
        plan = self._load_plan()
        if plan is None:
            plan = await self.llm.structured(PLAN_SYSTEM, json.dumps({
                "company_typed_by_user": company,
                "autocomplete_vs_candidates": candidates,
                "top_web_results": (web or {}).get("organic", []),
                "ai_overview": [e.snippet for e in self.store.by_signal("ai_view")][:6],
            }, ensure_ascii=False), Plan, temperature=0.1, fast=True)
            self._save_plan(plan)
        picked = [r for r in plan.rivals if r.name.lower() != company.lower()][:4] if self.include_rivals else []
        rivals = [r.name for r in picked]
        deep_rivals = rivals[:settings.max_rivals]
        await self.emit("plan", company=plan.official_name, description=plan.description,
                        rivals=rivals, ticker=plan.ticker, domain=plan.domain)

        await self.emit("stage", stage="collect",
                        text="Pulling hiring, news, search demand, patents and ad spend in parallel")
        tasks = {
            "jobs": self.collect.jobs(company),
            "news": self.collect.news(company, plan.news_query),
            "trends": self.collect.trends(company, [company] + rivals),
            "patents": self.collect.patents(company, plan.legal_name or plan.official_name),
        }
        if plan.domain:
            tasks["ads"] = self.collect.ads(company, plan.domain)
        if plan.ticker:
            tasks["finance"] = self.collect.finance(company, plan.ticker)
        for rival in picked[:settings.max_rivals]:
            # Search and match on the employer, so "Confluence" finds Atlassian's roles.
            tasks[f"jobs:{rival.name}"] = self.collect.jobs(rival.employer or rival.name, subject=rival.name)
        results = dict(zip(tasks, await asyncio.gather(
            *[self._safe(name, coro) for name, coro in tasks.items()])))
        self._compute_metrics(company, rivals, deep_rivals, results)

        if settings.max_followups and self.serp.remaining:
            await self.emit("stage", stage="critique", text="Looking for gaps in the evidence")
            critique = await self.llm.structured(
                CRITIC_SYSTEM,
                f"COMPANY: {plan.official_name} ({plan.description})\nDOMAIN: {plan.domain or 'unknown'}\n"
                f"SEARCHES ALREADY RUN: {json.dumps([(c['engine'], c['query']) for c in self.trace])}\n"
                f"METRICS: {json.dumps(self._metrics_for_llm(), ensure_ascii=False)}\n\n"
                f"EVIDENCE:\n{self.store.digest()}\n\n"
                f"Choose at most {settings.max_followups} follow-up searches.",
                Critique, temperature=0.2, fast=True)
            follow_ups = critique.follow_ups[:min(settings.max_followups, self.serp.remaining)]
            await self.emit("critique", gaps=critique.gaps[:4],
                            follow_ups=[f.model_dump() for f in follow_ups])
            if follow_ups:
                await self.emit("stage", stage="followup", text="Running the follow-up searches the critic asked for")
                await asyncio.gather(*[self._safe(f.kind, self._follow_up(company, plan, f))
                                       for f in follow_ups])

        await self.emit("stage", stage="analyse",
                        text=f"Reading {len(self.store.items)} pieces of evidence for tells")
        analysis = await self.llm.structured(
            ANALYST_SYSTEM,
            f"TARGET: {plan.official_name} — {plan.description}\n"
            f"RIVALS: {', '.join(rivals) or 'none requested'}\n\n"
            f"METRICS (computed from the search data):\n"
            f"{json.dumps(self._metrics_for_llm(), ensure_ascii=False, indent=1)}\n\n"
            f"EVIDENCE:\n{self.store.digest()}\n\n"
            f"Produce 6-9 tells covering every signal that has evidence, 2-3 say-vs-do items, "
            f"3-4 forecasts and one read for each of: "
            f"{', '.join(deep_rivals) or 'no rivals'}.",
            Analysis, temperature=0.35)

        await self.emit("stage", stage="ground", text="Checking every claim against its receipts")
        grounded, grounding = ground(analysis, self.store)
        await self.emit("grounding", **grounding)

        report = self._report(plan, rivals, candidates, grounded, grounding)
        await self.emit("report", report=report)
        return report

    # A reused plan means the same queries, so a rescan hits the search cache instead of the quota.
    def _plan_path(self):
        key = re.sub(r"[^a-z0-9]+", "-", self.query.lower()).strip("-")
        return self.serp.cache_dir / "_plans" / f"{key}.json"

    def _load_plan(self) -> Optional[Plan]:
        path = self._plan_path()
        if not self.plan_cache or not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            if datetime.now(timezone.utc) - datetime.fromisoformat(entry["saved_at"]) > PLAN_TTL:
                return None
            return Plan.model_validate(entry["plan"])
        except (OSError, ValueError, KeyError):
            return None

    def _save_plan(self, plan: Plan):
        if not self.plan_cache:
            return
        path = self._plan_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"saved_at": datetime.now(timezone.utc).isoformat(),
                                    "plan": plan.model_dump()}, ensure_ascii=False), encoding="utf-8")

    async def _follow_up(self, company: str, plan: Plan, f: FollowUp):
        if f.kind == "ads":
            res = await self.collect.ads(company, f.query)
            self.metrics.setdefault("ads", {**analytics.ads_stats(res["ads"]),
                                            "other_advertisers_on_domain": res["others_targeting_domain"]})
        elif f.kind == "finance":
            self.metrics["market"] = await self.collect.finance(company, plan.ticker or f.query)
        elif f.kind == "ai_mode":
            await self.collect.ai_mode(company, f.query)
        elif f.kind == "jobs":
            await self.collect.jobs(company, f.query)
        elif f.kind == "news":
            await self.collect.news(company, f.query, keep=8)
        elif f.kind == "patents":
            await self.collect.patents(company, plan.legal_name or plan.official_name, f.query)
        else:
            await self.collect.web(company, f.query)

    # ---- assembly ----------------------------------------------------------

    def _compute_metrics(self, company: str, rivals: list[str], deep_rivals: list[str], results: dict):
        m = self.metrics
        if results.get("jobs"):
            m["hiring"] = analytics.hiring_stats(results["jobs"]["roles"])
        if results.get("news"):
            m["news"] = analytics.news_stats(results["news"]["iso_dates"], results["news"]["sources"])
        if results.get("patents"):
            p = results["patents"]
            m["patents"] = analytics.patent_stats(p["filings"], p["cpc"], p["total"])
        if results.get("finance"):
            m["market"] = results["finance"]
        if results.get("ads"):
            m["ads"] = {**analytics.ads_stats(results["ads"]["ads"]),
                        "other_advertisers_on_domain": results["ads"]["others_targeting_domain"]}
        if results.get("trends") and results["trends"]["series"]:
            t = results["trends"]
            stats = analytics.trend_stats(t["series"], t["terms"])
            m["trends"] = {"terms": t["terms"], "series": t["series"], "stats": stats, "link": t["link"]}
            for s in stats:
                direction = "up" if s["change_pct"] > 0 else "down"
                self.store.add("demand", subject=s["term"], engine="google_trends", query=t["query"],
                               title=f"Search interest in {s['term']}: {s['recent_average']} over the last "
                                     f"4 weeks vs {s['baseline_average']} before ({direction} "
                                     f"{abs(s['change_pct'])}%)",
                               snippet=f"12-month average {s['average']} on Google's 0-100 scale, shared "
                                       f"across {', '.join(t['terms'])}. Peak week: {s['peak_week']}.",
                               link=t["link"], source="Google Trends", extra=s)
        compare = []
        for name in [company] + rivals:
            row = {"name": name}
            trend = next((s for s in (m.get("trends") or {}).get("stats", []) if s["term"] == name), None)
            if trend:
                row.update(trend_average=trend["average"], trend_change_pct=trend["change_pct"])
            roles = m.get("hiring") if name == company else None
            if name in deep_rivals and results.get(f"jobs:{name}"):
                roles = analytics.hiring_stats(results[f"jobs:{name}"]["roles"])
            if roles:
                row.update(hiring_sample=roles["sample_size"], by_function=roles["by_function"],
                           posted_last_7_days=roles["posted_last_7_days"],
                           top_function=(roles["by_function"] or [{}])[0].get("name"))
            compare.append(row)
        m["compare"] = compare

    def _metrics_for_llm(self) -> dict:
        """Everything except the raw weekly series, which the model does not need."""
        m = dict(self.metrics)
        if "trends" in m:
            m["trends"] = m["trends"]["stats"]
        return m

    def _report(self, plan: Plan, rivals: list[str], candidates: list[str],
                analysis: dict, grounding: dict) -> dict:
        engines = sorted({c["engine"] for c in self.trace})
        return {
            "id": uuid.uuid4().hex[:12],
            "query": self.query,
            "company": plan.official_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "plan": plan.model_dump(),
            "rivals": rivals,
            "rival_candidates": candidates,
            "analysis": analysis,
            "metrics": self.metrics,
            "evidence": {k: v.model_dump() for k, v in self.store.items.items()},
            "grounding": grounding,
            "usage": {
                "live_searches": self.serp.live_calls,
                "cache_hits": self.serp.cache_hits,
                "budget": self.serp.budget,
                "engines": engines,
                "calls": self.trace,
                "llm_calls": self.llm.calls,
                "evidence_items": len(self.store.items),
                "duration_s": round(time.perf_counter() - self._t0, 1),
            },
        }
