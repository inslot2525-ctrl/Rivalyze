import traceback
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from models import init_db, get_session, CompanySnapshot, Alert, MonitoredCompany, AsyncSessionLocal
from agents.orchestrator import run_agent, run_comparative, answer_followup, generate_pdf

load_dotenv()

scheduler = AsyncIOScheduler()


async def run_scheduled_analysis(company: str, user_id: str):
    """Background job: run analysis, compare with previous, generate alerts."""
    try:
        brief = await run_agent(company)

        async with AsyncSessionLocal() as session:
            # Mark old snapshots as not latest
            from sqlalchemy import update
            await session.execute(
                update(CompanySnapshot)
                .where(CompanySnapshot.company == company, CompanySnapshot.is_latest == True)
                .values(is_latest=False)
            )

            # Save new snapshot
            snapshot = CompanySnapshot(company=company, brief_json=brief, is_latest=True)
            session.add(snapshot)
            await session.flush()

            # Compare with previous latest
            from sqlalchemy import select
            prev = await session.execute(
                select(CompanySnapshot)
                .where(CompanySnapshot.company == company, CompanySnapshot.is_latest == False)
                .order_by(CompanySnapshot.created_at.desc())
                .limit(1)
            )
            prev_snapshot = prev.scalar_one_or_none()

            if prev_snapshot:
                alerts = detect_changes(prev_snapshot.brief_json, brief, snapshot.id)
                for alert in alerts:
                    session.add(alert)

            await session.commit()
    except Exception as e:
        traceback.print_exc()


def detect_changes(old: dict, new: dict, snapshot_id: int) -> List[Alert]:
    """Detect significant changes between briefs."""
    alerts = []
    fields_to_watch = [
        ("sentiment", "Sentiment shifted"),
        ("hiring.signal", "Hiring signal changed"),
        ("finance.price", "Stock price moved"),
        ("finance.market_cap", "Market cap changed"),
        ("summary", "Strategic summary updated"),
    ]

    for field_path, alert_type in fields_to_watch:
        old_val = get_nested(old, field_path)
        new_val = get_nested(new, field_path)
        if old_val != new_val and old_val is not None and new_val is not None:
            severity = "high" if field_path in ["sentiment", "hiring.signal", "finance.price"] else "medium"
            alerts.append(Alert(
                snapshot_id=snapshot_id,
                alert_type=alert_type,
                field_changed=field_path,
                old_value=str(old_val),
                new_value=str(new_val),
                severity=severity,
            ))
    return alerts


def get_nested(d: dict, path: str):
    keys = path.split(".")
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return None
    return d


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Rivalyze API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    company: str
    comparative: bool = False


class FollowupRequest(BaseModel):
    brief: dict
    question: str
    search_history: list = []


class MonitorRequest(BaseModel):
    company: str
    frequency_hours: int = 24


class MonitorUpdateRequest(BaseModel):
    frequency_hours: Optional[int] = None
    is_active: Optional[bool] = None


@app.get("/")
def root():
    return {"status": "Rivalyze API v2.0 is running ⚡"}


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.company.strip():
        raise HTTPException(status_code=400, detail="Company name is required")
    try:
        if req.comparative:
            result = await run_comparative(req.company.strip())
        else:
            result = await run_agent(req.company.strip())
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/followup")
async def followup(req: FollowupRequest):
    try:
        answer = await answer_followup(req.brief, req.question, req.search_history)
        return {"answer": answer}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export/pdf")
async def export_pdf(brief: dict):
    try:
        pdf_bytes = generate_pdf(brief)
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{brief.get("company", "rivalyze")}_brief.pdf"'}
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Monitoring endpoints
@app.post("/monitor")
async def add_monitor(req: MonitorRequest, background_tasks: BackgroundTasks):
    if not req.company.strip():
        raise HTTPException(status_code=400, detail="Company name required")
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        existing = await session.execute(
            select(MonitoredCompany).where(MonitoredCompany.company == req.company.strip())
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Already monitored")

        monitor = MonitoredCompany(company=req.company.strip(), frequency_hours=req.frequency_hours)
        session.add(monitor)
        await session.commit()

        # Schedule job
        job_id = f"monitor_{req.company.strip().replace(' ', '_')}"
        scheduler.add_job(
            run_scheduled_analysis,
            IntervalTrigger(hours=req.frequency_hours),
            args=[req.company.strip(), "default"],
            id=job_id,
            replace_existing=True,
        )

        # Run initial analysis
        background_tasks.add_task(run_scheduled_analysis, req.company.strip(), "default")

        return {"status": "monitoring started", "company": req.company.strip()}


@app.get("/monitor")
async def list_monitors():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(MonitoredCompany))
        monitors = result.scalars().all()
        return [{"company": m.company, "frequency_hours": m.frequency_hours, "is_active": m.is_active, "last_run": m.last_run} for m in monitors]


@app.patch("/monitor/{company}")
async def update_monitor(company: str, req: MonitorUpdateRequest):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, update
        result = await session.execute(select(MonitoredCompany).where(MonitoredCompany.company == company))
        monitor = result.scalar_one_or_none()
        if not monitor:
            raise HTTPException(status_code=404, detail="Not monitored")

        if req.frequency_hours is not None:
            monitor.frequency_hours = req.frequency_hours
            job_id = f"monitor_{company.replace(' ', '_')}"
            scheduler.reschedule_job(job_id, trigger=IntervalTrigger(hours=req.frequency_hours))

        if req.is_active is not None:
            monitor.is_active = req.is_active
            job_id = f"monitor_{company.replace(' ', '_')}"
            if req.is_active:
                scheduler.resume_job(job_id)
            else:
                scheduler.pause_job(job_id)

        await session.commit()
        return {"status": "updated"}


@app.delete("/monitor/{company}")
async def delete_monitor(company: str):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, delete
        result = await session.execute(select(MonitoredCompany).where(MonitoredCompany.company == company))
        monitor = result.scalar_one_or_none()
        if not monitor:
            raise HTTPException(status_code=404, detail="Not monitored")

        job_id = f"monitor_{company.replace(' ', '_')}"
        try:
            scheduler.remove_job(job_id)
        except:
            pass

        await session.execute(delete(MonitoredCompany).where(MonitoredCompany.company == company))
        await session.commit()
        return {"status": "removed"}


@app.get("/alerts/{company}")
async def get_alerts(company: str, limit: int = 20):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Alert)
            .join(CompanySnapshot)
            .where(CompanySnapshot.company == company)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        alerts = result.scalars().all()
        return [{
            "type": a.alert_type,
            "field": a.field_changed,
            "old": a.old_value,
            "new": a.new_value,
            "severity": a.severity,
            "created_at": a.created_at.isoformat(),
            "acknowledged": a.acknowledged,
        } for a in alerts]


@app.get("/history/{company}")
async def get_history(company: str, limit: int = 10):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(CompanySnapshot)
            .where(CompanySnapshot.company == company)
            .order_by(CompanySnapshot.created_at.desc())
            .limit(limit)
        )
        snapshots = result.scalars().all()
        return [{
            "brief": s.brief_json,
            "created_at": s.created_at.isoformat(),
        } for s in snapshots]