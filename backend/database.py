"""SQLite storage for Ad Autopsy (SQLAlchemy, file-based — no Docker/Postgres)."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.environ.get("AD_AUTOPSY_DB", os.path.join(os.path.dirname(__file__), "ad_autopsy.db"))
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    spend = Column(Float, default=0.0)
    impressions = Column(Float, default=0.0)
    clicks = Column(Float, default=0.0)
    lp_views = Column(Float, default=0.0)
    atc = Column(Float, default=0.0)
    purchases = Column(Float, default=0.0)
    price = Column(Float, default=0.0)
    cogs = Column(Float, default=0.0)
    fees_pct = Column(Float, default=0.0)
    stop_loss = Column(Float, default=300.0)
    currency = Column(String, default="CAD")
    notes = Column(String, default="")
    created_at = Column(DateTime, default=utcnow)


class CompetitorAd(Base):
    __tablename__ = "competitor_ads"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, nullable=False, index=True)
    ad_id = Column(String, default="")
    start_date = Column(Date, nullable=True)
    format = Column(String, default="")  # first-person story, confessional, ...
    country = Column(String, default="CA")  # CA or US
    active = Column(Boolean, default=True)
    destination_url = Column(String, default="")
    source = Column(String, default="brand_search")  # brand_search | problem_word_search
    problem_word = Column(String, default="")
    notes = Column(String, default="")
    created_at = Column(DateTime, default=utcnow)

    @property
    def days_running(self) -> int | None:
        if not self.start_date:
            return None
        return (date.today() - self.start_date).days


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
