"""Saving scans, diffing a scan against the previous one, and loading recorded demos."""
import json
import re
from typing import Optional

from sqlalchemy import select

from config import settings
from models import AsyncSessionLocal, ScanRecord

# Signals where a new item between two scans is news in itself.
DIFF_SIGNALS = {"hiring": "New role", "rnd": "New patent filing", "ads": "New ad creative",
                "narrative": "New coverage"}


def company_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def diff_reports(previous: dict, current: dict) -> list[dict]:
    """What appeared since the last scan of the same company."""
    target = current["company"]
    old_keys = {(e["signal"], e.get("link") or e["title"]) for e in previous["evidence"].values()}
    changes = []
    for ev in current["evidence"].values():
        label = DIFF_SIGNALS.get(ev["signal"])
        if not label or ev["subject"] not in (target, current["query"]):
            continue
        if (ev["signal"], ev.get("link") or ev["title"]) not in old_keys:
            changes.append({"kind": label, "signal": ev["signal"], "title": ev["title"],
                            "evidence_id": ev["id"], "date": ev.get("date", "")})

    def trend(report):
        stats = (report["metrics"].get("trends") or {}).get("stats") or []
        return next((s for s in stats if s["term"] == report["query"]), None)

    before, after = trend(previous), trend(current)
    if before and after and abs(after["recent_average"] - before["recent_average"]) >= 5:
        changes.append({"kind": "Search demand moved", "signal": "demand",
                        "title": f"4-week search interest went from {before['recent_average']} "
                                 f"to {after['recent_average']}", "evidence_id": None, "date": ""})

    old_forecasts = {f["prediction"] for f in previous["analysis"]["forecasts"]}
    for f in current["analysis"]["forecasts"]:
        if f["prediction"] not in old_forecasts:
            changes.append({"kind": "New forecast", "signal": "forecast", "title": f["prediction"],
                            "evidence_id": (f["evidence_ids"] or [None])[0], "date": ""})
    return changes


async def latest_scan(company: str) -> Optional[ScanRecord]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ScanRecord).where(ScanRecord.company_key == company_key(company))
            .order_by(ScanRecord.created_at.desc()).limit(1))
        return result.scalar_one_or_none()


async def save_scan(report: dict, events: list[dict]) -> dict:
    """Attach the diff against the previous scan, then persist."""
    previous = await latest_scan(report["company"])
    report["changes"] = diff_reports(previous.report, report) if previous else []
    report["previous_scan_at"] = previous.created_at.isoformat() if previous else None
    async with AsyncSessionLocal() as session:
        session.add(ScanRecord(id=report["id"], company=report["company"],
                               company_key=company_key(report["company"]),
                               report=report, events=events))
        await session.commit()
    return report


async def get_scan(scan_id: str) -> Optional[ScanRecord]:
    async with AsyncSessionLocal() as session:
        return await session.get(ScanRecord, scan_id)


async def list_scans(limit: int = 20) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ScanRecord).order_by(ScanRecord.created_at.desc()).limit(limit))
        return [{"id": s.id, "company": s.company, "created_at": s.created_at.isoformat(),
                 "one_liner": s.report["analysis"]["one_liner"],
                 "changes": len(s.report.get("changes") or [])} for s in result.scalars()]


def list_demos() -> list[dict]:
    demos = []
    for path in sorted(settings.demos_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        r = data["report"]
        demos.append({"slug": data["slug"], "company": r["company"], "recorded_at": r["created_at"],
                      "one_liner": r["analysis"]["one_liner"], "rivals": r["rivals"],
                      "searches": len(r["usage"]["calls"]), "evidence": r["usage"]["evidence_items"]})
    return demos


def load_demo(slug: str) -> Optional[dict]:
    path = settings.demos_dir / f"{company_key(slug)}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
