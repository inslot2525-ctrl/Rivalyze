from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

Base = declarative_base()


class CompanySnapshot(Base):
    __tablename__ = "company_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, index=True, nullable=False)
    brief_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_latest = Column(Boolean, default=True, nullable=False)

    alerts = relationship("Alert", back_populates="snapshot", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("company_snapshots.id"), nullable=False)
    alert_type = Column(String, nullable=False)
    field_changed = Column(String, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    severity = Column(String, default="info")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False)

    snapshot = relationship("CompanySnapshot", back_populates="alerts")


class MonitoredCompany(Base):
    __tablename__ = "monitored_companies"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, default="default", nullable=False)
    frequency_hours = Column(Integer, default=24, nullable=False)
    last_run = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


engine = create_async_engine("sqlite+aiosqlite:///./rivalyze.db", echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session