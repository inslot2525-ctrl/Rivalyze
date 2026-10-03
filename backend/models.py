from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from config import settings

Base = declarative_base()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ScanRecord(Base):
    """One finished scan: the full report plus the event trace that produced it."""
    __tablename__ = "scans"

    id = Column(String, primary_key=True)
    company = Column(String, index=True, nullable=False)
    company_key = Column(String, index=True, nullable=False)
    report = Column(JSON, nullable=False)
    events = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=_now, nullable=False, index=True)


class MonitoredCompany(Base):
    __tablename__ = "monitored_companies"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, default="default", nullable=False)
    frequency_hours = Column(Integer, default=24, nullable=False)
    last_run = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)


engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
