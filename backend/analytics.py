"""Numbers computed in code from collector output.

The agents reason over these, and the UI charts them. Keeping the arithmetic out
of the LLM means a figure in the report is a figure the search data produced.
"""
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

# Checked in order; the first function whose keyword appears in the title wins.
FUNCTIONS = [
    ("Finance / Legal", r"\b(finance|accounting|payroll|legal|counsel|tax|compliance|controller)\b"),
    ("AI / ML", r"\b(ai|ml|machine learning|llm|research scientist|applied scientist|deep learning|nlp)\b"),
    ("Data", r"\b(data|analytics|analyst|bi)\b"),
    ("Sales", r"\b(sales|account executive|account manager|business development|bdr|sdr|revenue|partnerships?)\b"),
    ("Customer", r"\b(customer|support|success|solutions|onboarding|outcomes|implementation)\b"),
    ("Marketing", r"\b(marketing|brand|content|growth|communications|social media|community|pr)\b"),
    ("Design", r"\b(design|designer|ux|ui|creative)\b"),
    ("Product", r"\b(product manager|product lead|program manager|product)\b"),
    ("Hardware / Manufacturing", r"\b(hardware|manufacturing|mechanical|electrical|firmware|technician|"
                                 r"production|assembly|factory|robotics|quality)\b"),
    ("Engineering", r"\b(engineer|engineering|developer|software|sre|devops|infrastructure|security|"
                    r"architect|android|ios|backend|frontend|full[- ]?stack|mobile)\b"),
    ("People / Ops", r"\b(recruit|people|hr|talent|operations|executive assistant|workplace|office)\b"),
]


def job_function(title: str) -> str:
    t = title.lower()
    for name, pattern in FUNCTIONS:
        if re.search(pattern, t):
            return name
    return "Other"


def _posted_days(posted: str) -> Optional[int]:
    m = re.match(r"(\d+)\+?\s+(hour|day|week|month)", posted or "")
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return {"hour": 0, "day": n, "week": n * 7, "month": n * 30}[unit]


def hiring_stats(roles: list[dict]) -> dict:
    functions = Counter(job_function(r["title"]) for r in roles)
    locations = Counter("Remote" if r.get("remote") else (r.get("location") or "Unlisted") for r in roles)
    ages = [d for d in (_posted_days(r.get("posted", "")) for r in roles) if d is not None]
    return {
        "sample_size": len(roles),
        "by_function": [{"name": k, "count": v} for k, v in functions.most_common()],
        "by_location": [{"name": k, "count": v} for k, v in locations.most_common(6)],
        "posted_last_7_days": sum(1 for d in ages if d <= 7),
        "remote_share": round(sum(1 for r in roles if r.get("remote")) / len(roles), 2) if roles else 0,
        "internships": sum(1 for r in roles if r.get("schedule") == "Internship"),
    }


def news_stats(iso_dates: list[str], sources: list[str], now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    parsed = []
    for d in iso_dates:
        try:
            parsed.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
        except ValueError:
            continue
    last7 = sum(1 for d in parsed if now - d <= timedelta(days=7))
    prev7 = sum(1 for d in parsed if timedelta(days=7) < now - d <= timedelta(days=14))
    return {
        "articles": len(iso_dates),
        "last_7_days": last7,
        "previous_7_days": prev7,
        "last_30_days": sum(1 for d in parsed if now - d <= timedelta(days=30)),
        "top_sources": [{"name": k, "count": v} for k, v in Counter(sources).most_common(5)],
    }


def trend_stats(series: list[dict], terms: list[str], recent_weeks: int = 4) -> list[dict]:
    """Per term: 12-month average, last-4-week average, and the change between them."""
    out = []
    for term in terms:
        values = [row.get(term, 0) for row in series]
        if len(values) <= recent_weeks:
            continue
        recent, baseline = values[-recent_weeks:], values[:-recent_weeks]
        r_avg, b_avg = sum(recent) / len(recent), sum(baseline) / len(baseline)
        peak = max(range(len(values)), key=values.__getitem__)
        out.append({
            "term": term,
            "average": round(sum(values) / len(values), 1),
            "recent_average": round(r_avg, 1),
            "baseline_average": round(b_avg, 1),
            "change_pct": round((r_avg - b_avg) / b_avg * 100, 1) if b_avg else 0.0,
            "peak_week": series[peak].get("date", ""),
        })
    return out


def patent_stats(filings: list[dict], cpc: list[dict], total: int, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    dates = sorted((f["filing_date"] for f in filings if f.get("filing_date")), reverse=True)
    cutoff = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    return {
        "total_matching": total,
        "newest_shown": len(filings),
        "latest_filing": dates[0] if dates else "",
        "filed_last_12_months": sum(1 for d in dates if d >= cutoff),
        "top_classes": cpc,
    }


def ads_stats(ads: list[dict], now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        "own_creatives": len(ads),
        "by_format": [{"name": k, "count": v} for k, v in Counter(a.get("format") for a in ads).most_common()],
        "by_advertiser": [{"name": k, "count": v}
                          for k, v in Counter(a.get("advertiser") for a in ads).most_common(4)],
        "launched_last_30_days": sum(1 for a in ads if (a.get("first_shown") or "") >= cutoff),
    }
