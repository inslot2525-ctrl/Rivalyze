import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

import storage
from agents.ask import ask
from agents.llm import LLMUnavailable
from agents.pipeline import Scan, ScanError
from battlecard import battlecard
from config import settings
from models import AsyncSessionLocal, MonitoredCompany, init_db
from serp.client import account_usage

log = logging.getLogger("rivalyze")
scheduler = AsyncIOScheduler()

# Live scans spend real searches, so only a couple may run at once.
scan_slots = asyncio.Semaphore(2)


def _job_id(company: str) -> str:
    return f"monitor_{storage.company_key(company)}"


async def run_monitored_scan(company: str):
    """Scheduled job: rescan a watched company. The saved report carries the diff."""
    try:
        async with scan_slots:
            scan = Scan(company)
            report = await scan.run()
        await storage.save_scan(report, scan.events)
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(MonitoredCompany).where(MonitoredCompany.company == company))
            monitor = result.scalar_one_or_none()
            if monitor:
                monitor.last_run = datetime.now(timezone.utc)
                await session.commit()
    except Exception:
        log.exception("Monitored scan failed for %s", company)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.start()
    # Jobs live in memory, so rebuild them from the watchlist on every start.
    async with AsyncSessionLocal() as session:
        for m in (await session.execute(select(MonitoredCompany))).scalars():
            scheduler.add_job(run_monitored_scan, IntervalTrigger(hours=m.frequency_hours),
                              args=[m.company], id=_job_id(m.company), replace_existing=True)
            if not m.is_active:
                scheduler.pause_job(_job_id(m.company))
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Rivalyze API", version="3.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


def sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@app.get("/")
def root():
    return {"name": "Rivalyze", "version": app.version, "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok", "live_search": settings.live, "llm": bool(settings.gemini_api_key),
            "demos": len(storage.list_demos())}


@app.get("/usage")
async def usage():
    return {**await account_usage(), "scan_budget": settings.scan_search_budget}


# ---- scans -----------------------------------------------------------------

@app.get("/scan/stream")
async def scan_stream(company: str = Query(min_length=1, max_length=80), rivals: bool = True):
    """Run a scan and stream its trace as server-sent events, ending with the report."""
    company = company.strip()
    if not company:
        raise HTTPException(400, "Company name is required")
    if not settings.gemini_api_key:
        raise HTTPException(503, "GEMINI_API_KEY is not set. Open a recorded demo instead.")

    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: dict):
        if event["type"] != "report":
            await queue.put(event)

    async def work():
        try:
            async with scan_slots:
                scan = Scan(company, include_rivals=rivals, emit=emit)
                report = await scan.run()
            report = await storage.save_scan(report, scan.events)
            await queue.put({"type": "report", "report": report})
        except (ScanError, LLMUnavailable) as e:
            await queue.put({"type": "error", "message": str(e)})
        except Exception as e:
            log.exception("Scan failed for %s", company)
            await queue.put({"type": "error", "message": f"Scan failed: {str(e)[:200]}"})
        finally:
            await queue.put(None)

    async def stream():
        task = asyncio.create_task(work())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield sse(event)
        finally:
            task.cancel()  # browser went away: stop spending searches

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.get("/scans")
async def scans(limit: int = Query(20, ge=1, le=100)):
    return await storage.list_scans(limit)


async def _report(ref: str) -> dict:
    """`ref` is a scan id, or `demo:<slug>` for a recorded demo."""
    if ref.startswith("demo:"):
        demo = storage.load_demo(ref[5:])
        if not demo:
            raise HTTPException(404, "Demo not found")
        return demo["report"]
    record = await storage.get_scan(ref)
    if not record:
        raise HTTPException(404, "Scan not found")
    return record.report


@app.get("/scans/{ref}")
async def scan_detail(ref: str):
    return await _report(ref)


@app.get("/scans/{ref}/battlecard.md", response_class=PlainTextResponse)
async def scan_battlecard(ref: str):
    report = await _report(ref)
    filename = f"{storage.company_key(report['company'])}-battlecard.md"
    return PlainTextResponse(battlecard(report), media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ---- recorded demos: replay a real scan without spending searches ------------

@app.get("/demos")
def demos():
    return storage.list_demos()


@app.get("/demos/{slug}/stream")
async def demo_stream(slug: str, speed: float = Query(6.0, ge=1, le=50)):
    demo = storage.load_demo(slug)
    if not demo:
        raise HTTPException(404, "Demo not found")

    async def stream():
        last = 0.0
        for event in demo["events"]:
            await asyncio.sleep(min(max(event["t"] - last, 0) / speed, 1.2))
            last = event["t"]
            yield sse({**event, "replay": True})
        yield sse({"type": "report", "report": {**demo["report"], "id": f"demo:{demo['slug']}",
                                                "replay": True, "changes": []}})

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


# ---- ask ---------------------------------------------------------------------

class AskRequest(BaseModel):
    scan: str = Field(description="Scan id, or demo:<slug>")
    question: str = Field(min_length=2, max_length=500)
    history: list[dict] = Field(default_factory=list, max_length=12)


@app.post("/ask")
async def ask_endpoint(req: AskRequest):
    report = await _report(req.scan)
    try:
        return await ask(report, req.question.strip(), req.history)
    except LLMUnavailable as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        log.exception("Ask failed")
        raise HTTPException(502, str(e)[:200])


# ---- watchlist ---------------------------------------------------------------

class MonitorRequest(BaseModel):
    company: str = Field(min_length=1, max_length=80)
    frequency_hours: int = Field(24, ge=6, le=24 * 14)


class MonitorUpdate(BaseModel):
    frequency_hours: Optional[int] = Field(None, ge=6, le=24 * 14)
    is_active: Optional[bool] = None


async def _monitor(session, company: str) -> MonitoredCompany:
    result = await session.execute(select(MonitoredCompany).where(MonitoredCompany.company == company))
    monitor = result.scalar_one_or_none()
    if not monitor:
        raise HTTPException(404, "Not on the watchlist")
    return monitor


@app.post("/monitor", status_code=201)
async def add_monitor(req: MonitorRequest):
    company = req.company.strip()
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(MonitoredCompany).where(MonitoredCompany.company == company))
        if existing.scalar_one_or_none():
            raise HTTPException(409, "Already on the watchlist")
        session.add(MonitoredCompany(company=company, frequency_hours=req.frequency_hours))
        await session.commit()
    # The first rescan happens after one interval; the scan the user just ran is the baseline.
    scheduler.add_job(run_monitored_scan, IntervalTrigger(hours=req.frequency_hours),
                      args=[company], id=_job_id(company), replace_existing=True)
    return {"company": company, "frequency_hours": req.frequency_hours}


@app.get("/monitor")
async def list_monitors():
    async with AsyncSessionLocal() as session:
        monitors = (await session.execute(select(MonitoredCompany))).scalars().all()
    out = []
    for m in monitors:
        latest = await storage.latest_scan(m.company)
        job = scheduler.get_job(_job_id(m.company))
        out.append({
            "company": m.company, "frequency_hours": m.frequency_hours, "is_active": m.is_active,
            "last_run": m.last_run.isoformat() if m.last_run else None,
            "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
            "latest_scan": latest.id if latest else None,
            "changes": (latest.report.get("changes") or [])[:5] if latest else [],
        })
    return out


@app.patch("/monitor/{company}")
async def update_monitor(company: str, req: MonitorUpdate):
    async with AsyncSessionLocal() as session:
        monitor = await _monitor(session, company)
        if req.frequency_hours is not None:
            monitor.frequency_hours = req.frequency_hours
            scheduler.add_job(run_monitored_scan, IntervalTrigger(hours=req.frequency_hours),
                              args=[company], id=_job_id(company), replace_existing=True)
        if req.is_active is not None:
            monitor.is_active = req.is_active
        if not monitor.is_active:
            scheduler.pause_job(_job_id(company))
        elif req.is_active:
            scheduler.resume_job(_job_id(company))
        await session.commit()
    return {"status": "updated"}


@app.delete("/monitor/{company}")
async def delete_monitor(company: str):
    async with AsyncSessionLocal() as session:
        await _monitor(session, company)
        await session.execute(delete(MonitoredCompany).where(MonitoredCompany.company == company))
        await session.commit()
    if scheduler.get_job(_job_id(company)):
        scheduler.remove_job(_job_id(company))
    return {"status": "removed"}
