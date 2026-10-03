"""One collector per SerpApi engine.

Each collector runs a search, turns the response into `Evidence` items the agents
can cite, and returns the numbers `analytics` needs. No LLM is involved here, so
everything a collector reports is exactly what the search returned.
"""
import re
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional
from urllib.parse import quote_plus

from agents.schemas import EvidenceStore
from serp.client import CallMeta, SerpClient

Tracer = Callable[[CallMeta, str, str, int], Awaitable[None]]


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def same_company(candidate: str, company: str) -> bool:
    """Loose match: 'Notion Labs, Inc.' and 'Notion Labs Japan' both belong to 'Notion'."""
    a, b = _norm(candidate), _norm(company)
    if not a or not b:
        return False
    return a == b or a.startswith(b + " ") or b.startswith(a + " ") or f" {b} " in f" {a} "


class Collectors:
    def __init__(self, serp: SerpClient, store: EvidenceStore, trace: Optional[Tracer] = None):
        self.serp = serp
        self.store = store
        self.trace = trace

    async def _search(self, engine: str, signal: str, subject: str, label: str, **params):
        data, meta = await self.serp.search(engine, **params)
        return data, meta, (signal, subject, label)

    async def _done(self, meta: CallMeta, ctx: tuple, n: int):
        if self.trace:
            await self.trace(meta, ctx[0], ctx[2], n)

    # ---- scout -------------------------------------------------------------

    async def rivals(self, company: str) -> list[str]:
        """What people type after '<company> vs' is a crowd-sourced competitor list."""
        q = f"{company} vs "
        data, meta, ctx = await self._search("google_autocomplete", "rivals", company, q, q=q)
        names: list[str] = []
        for s in data.get("suggestions", []):
            value = s.get("value", "")
            m = re.match(rf"^{re.escape(company.lower())}\s+vs\.?\s+(.+)$", value.lower())
            if not m:
                continue
            name = m.group(1).strip()
            if name and name not in names:
                names.append(name)
                self.store.add("rivals", subject=company, engine="google_autocomplete", query=q,
                               title=value, snippet=f"Autocomplete rank {len(names)}",
                               link=f"https://www.google.com/search?q={quote_plus(value)}",
                               extra={"rival": name, "relevance": s.get("relevance")})
        await self._done(meta, ctx, len(names))
        return names

    async def web(self, company: str, query: Optional[str] = None) -> dict:
        """One Google search yields three signals: web results, People Also Ask, AI Overview."""
        q = query or f"{company} company"
        data, meta, ctx = await self._search("google", "web", company, q, q=q, hl="en", gl="us")
        n = 0
        kg = data.get("knowledge_graph") or {}
        if kg.get("title"):
            self.store.add("web", subject=company, engine="google", query=q,
                           title=f"{kg.get('title')} — {kg.get('type', 'knowledge graph')}",
                           snippet=kg.get("description", ""), link=kg.get("website"),
                           source="Google Knowledge Graph")
            n += 1
        for r in data.get("organic_results", [])[:6]:
            self.store.add("web", subject=company, engine="google", query=q,
                           title=r.get("title", ""), snippet=r.get("snippet", ""),
                           link=r.get("link"), source=r.get("source", ""), date=r.get("date", ""))
            n += 1
        questions = [r.get("question") for r in data.get("related_questions", []) if r.get("question")]
        for r in data.get("related_questions", []):
            if r.get("question"):
                self.store.add("doubts", subject=company, engine="google", query=q,
                               title=r["question"], snippet=r.get("snippet") or "",
                               link=r.get("link") or f"https://www.google.com/search?q={quote_plus(r['question'])}",
                               source="People Also Ask")
                n += 1
        for r in data.get("related_searches", [])[:8]:
            if r.get("query"):
                self.store.add("doubts", subject=company, engine="google", query=q,
                               title=r["query"], link=r.get("link"), source="Related searches")
                n += 1
        n += self._ai_blocks(data.get("ai_overview") or {}, company, "google", q, "Google AI Overview")
        await self._done(meta, ctx, n)
        return {"questions": questions, "knowledge_graph": kg,
                "organic": [{"title": r.get("title"), "link": r.get("link"), "snippet": r.get("snippet")}
                            for r in data.get("organic_results", [])[:6]]}

    def _ai_blocks(self, ai: dict, company: str, engine: str, q: str, source: str, limit: int = 8) -> int:
        refs = {r.get("index"): r for r in ai.get("references", [])}
        n = 0
        for block in ai.get("text_blocks", []):
            snippets = [block.get("snippet")] if block.get("type") == "paragraph" else \
                       [i.get("snippet") for i in block.get("list", [])]
            idx = (block.get("reference_indexes") or [None])[0]
            ref = refs.get(idx, {})
            for s in snippets:
                if not s or n >= limit:
                    continue
                self.store.add("ai_view", subject=company, engine=engine, query=q,
                               title=s[:110], snippet=s, link=ref.get("link"),
                               source=f"{source}, citing {ref['source']}" if ref.get("source") else source)
                n += 1
        return n

    # ---- core signals ------------------------------------------------------

    async def jobs(self, company: str, query: Optional[str] = None, subject: Optional[str] = None) -> dict:
        """`company` is the employer to match; `subject` is who the evidence is filed under."""
        q = query or company
        subject = subject or company
        data, meta, ctx = await self._search("google_jobs", "hiring", subject, q, q=q, hl="en", gl="us")
        roles = []
        for j in data.get("jobs_results", []):
            if not same_company(j.get("company_name", ""), company):
                continue
            ext = j.get("extensions", [])
            posted = next((e for e in ext if "ago" in e), "")
            remote = "Work from home" in ext or j.get("location", "").strip().lower() == "anywhere"
            highlights = [i for h in j.get("job_highlights", []) for i in h.get("items", [])]
            link = j.get("source_link") or next(
                (o.get("link") for o in j.get("apply_options", []) if o.get("link")), None) or j.get("share_link")
            role = {"title": j.get("title", ""), "location": j.get("location", ""), "posted": posted,
                    "remote": remote, "schedule": next((e for e in ext if e in
                        ("Full-time", "Part-time", "Internship", "Contractor")), "")}
            roles.append(role)
            self.store.add("hiring", subject=subject, engine="google_jobs", query=q,
                           title=f"{role['title']} — {role['location'] or 'location not listed'}",
                           snippet=" ".join(highlights)[:400] or (j.get("description") or "")[:400],
                           link=link, source=f"via {j.get('via', 'Google Jobs')}", date=posted, extra=role)
        await self._done(meta, ctx, len(roles))
        return {"roles": roles, "returned": len(data.get("jobs_results", []))}

    async def news(self, company: str, query: Optional[str] = None, keep: int = 20) -> dict:
        q = query or company
        data, meta, ctx = await self._search("google_news", "narrative", company, q, q=q, hl="en", gl="us")
        results = data.get("news_results", [])
        dates, sources = [], []
        for r in results:
            if r.get("iso_date"):
                dates.append(r["iso_date"])
            if (r.get("source") or {}).get("name"):
                sources.append(r["source"]["name"])
        for r in results[:keep]:
            self.store.add("narrative", subject=company, engine="google_news", query=q,
                           title=r.get("title", ""), link=r.get("link"),
                           source=(r.get("source") or {}).get("name", ""),
                           date=(r.get("iso_date") or "")[:10], snippet=r.get("snippet") or "")
        await self._done(meta, ctx, len(results))
        return {"iso_dates": dates, "sources": sources, "total": len(results)}

    async def trends(self, company: str, terms: list[str]) -> dict:
        """One search compares the target and its rivals on the same 0-100 scale."""
        q = ",".join(terms[:5])
        data, meta, ctx = await self._search("google_trends", "demand", company, q,
                                             q=q, data_type="TIMESERIES", date="today 12-m")
        timeline = (data.get("interest_over_time") or {}).get("timeline_data", [])
        series = []
        for point in timeline:
            if point.get("partial_data"):
                continue
            row = {"date": point.get("date", ""), "ts": int(point.get("timestamp", 0))}
            for v in point.get("values", []):
                row[v.get("query")] = v.get("extracted_value", 0)
            series.append(row)
        await self._done(meta, ctx, len(series))
        return {"terms": terms[:5], "series": series, "query": q,
                "link": f"https://trends.google.com/trends/explore?date=today%2012-m&q={quote_plus(q)}"}

    async def patents(self, company: str, assignee: str, query: Optional[str] = None) -> dict:
        # Google Patents reads a comma as a list separator, so "Notion Labs, Inc." matches nothing.
        assignee = re.sub(r",?\s+(inc|llc|ltd|corp|corporation|co|plc|gmbh)\.?$", "",
                          assignee.strip(), flags=re.I).replace(",", "")
        params = {"assignee": assignee, "sort": "new"}
        # The engine needs a query; a broad boolean keeps the assignee filter doing the work.
        params["q"] = query or "(system OR method OR device OR apparatus OR composition)"
        label = f"assignee:{assignee}" + (f" {query}" if query else "")
        data, meta, ctx = await self._search("google_patents", "rnd", company, label, **params)
        first = _norm(assignee).split(" ")[0] if assignee else ""
        filings, owners = [], []
        for p in data.get("organic_results", []):
            if first and first not in _norm(p.get("assignee", "")):
                continue
            owners.append(_core_name(p.get("assignee", "")))
            filings.append({"title": p.get("title", ""), "filing_date": p.get("filing_date", "")})
            self.store.add("rnd", subject=company, engine="google_patents", query=label,
                           title=p.get("title", ""), snippet=(p.get("snippet") or "").strip(" …"),
                           link=p.get("patent_link"), source=p.get("assignee", ""),
                           date=p.get("filing_date", ""),
                           extra={"publication_number": p.get("publication_number"),
                                  "inventor": p.get("inventor")})
        cpc = [{"code": c.get("key"), "share": c.get("percentage")}
               for c in (data.get("summary") or {}).get("cpc", []) if c.get("key") != "Total"]
        await self._done(meta, ctx, len(filings))
        # A short name such as "Coda" also matches unrelated companies. When the results are not
        # mostly one owner, the total cannot be attributed and callers should not compare on it.
        top = max((owners.count(o) for o in set(owners)), default=0)
        return {"filings": filings, "cpc": cpc[:6], "single_owner": bool(owners) and top / len(owners) >= 0.7,
                "total": (data.get("search_information") or {}).get("total_results", 0)}

    # ---- follow-ups the critic can ask for ---------------------------------

    async def ads(self, company: str, domain: str) -> dict:
        data, meta, ctx = await self._search("google_ads_transparency_center", "ads", company,
                                             domain, text=domain)
        own = []
        for a in data.get("ad_creatives", []):
            if not same_company(a.get("advertiser", ""), company):
                continue  # resellers and unrelated advertisers also point ads at the domain
            first = _ts(a.get("first_shown"))
            last = _ts(a.get("last_shown"))
            ad = {"advertiser": a.get("advertiser"), "format": a.get("format"),
                  "days_shown": a.get("total_days_shown"), "first_shown": first, "last_shown": last}
            own.append(ad)
            self.store.add("ads", subject=company, engine="google_ads_transparency_center", query=domain,
                           title=f"{(a.get('format') or 'ad').title()} ad by {a.get('advertiser')}",
                           snippet=f"First shown {first}, last shown {last}, "
                                   f"{a.get('total_days_shown')} days running",
                           link=a.get("details_link"), source="Google Ads Transparency Center",
                           date=first, extra={**ad, "image": a.get("image")})
        await self._done(meta, ctx, len(own))
        return {"ads": own, "others_targeting_domain": len(data.get("ad_creatives", [])) - len(own)}

    async def finance(self, company: str, ticker: str) -> dict:
        data, meta, ctx = await self._search("google_finance", "market", company, ticker, q=ticker, hl="en")
        summary = data.get("summary") or {}
        if not summary:
            await self._done(meta, ctx, 0)
            return {}
        move = summary.get("price_movement") or {}
        sign = "-" if move.get("movement") == "Down" else "+"
        stats = {s.get("label"): s.get("value")
                 for s in ((data.get("knowledge_graph") or {}).get("key_stats") or {}).get("stats", [])}
        link = f"https://www.google.com/finance/quote/{ticker}"
        out = {"ticker": ticker, "price": summary.get("price"),
               "change_pct": round(move.get("percentage", 0), 2) * (-1 if sign == "-" else 1),
               "market_cap": stats.get("Mkt. cap"), "pe": stats.get("P/E ratio")}
        self.store.add("market", subject=company, engine="google_finance", query=ticker,
                       title=f"{summary.get('title')} ({ticker}) {summary.get('price')}, "
                             f"{sign}{abs(move.get('percentage', 0)):.2f}% today",
                       snippet=", ".join(f"{k}: {v}" for k, v in stats.items() if v)[:300],
                       link=link, source="Google Finance", date=(summary.get("date") or "")[:11])
        n = 1
        for block in data.get("financials", [])[:1]:
            latest = (block.get("results") or [{}])[0]
            rows = [r for r in latest.get("table", []) if r.get("value") not in (None, "—")][:9]
            if rows:
                self.store.add("market", subject=company, engine="google_finance", query=ticker,
                               title=f"{block.get('title')} — {latest.get('period_type', '')} {latest.get('date', '')}",
                               snippet="; ".join(f"{r['title']} {_money(r['value'])} ({r.get('change')} YoY)"
                                                 for r in rows),
                               link=link, source="Google Finance", date=latest.get("date", ""))
                out["financials"] = [{"title": r["title"], "value": _money(r["value"]),
                                      "change": r.get("change")} for r in rows]
                n += 1
        await self._done(meta, ctx, n)
        return out

    async def ai_mode(self, company: str, question: str) -> dict:
        data, meta, ctx = await self._search("google_ai_mode", "ai_view", company, question, q=question)
        n = self._ai_blocks(data, company, "google_ai_mode", question, "Google AI Mode", limit=10)
        await self._done(meta, ctx, n)
        return {"blocks": n}


CORPORATE = {"inc", "llc", "ltd", "corp", "corporation", "co", "plc", "gmbh", "pty", "us", "usa", "ip",
             "holdings", "limited", "technologies", "technology", "international", "company"}


def _core_name(assignee: str) -> str:
    """'Atlassian Pty Ltd' and 'Atlassian US, Inc.' are the same owner."""
    return " ".join(w for w in _norm(assignee).split() if w not in CORPORATE)


def _ts(value) -> str:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def _money(value) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if abs(n) >= size:
            return f"${n / size:.2f}{unit}"
    return f"${n:,.0f}"
