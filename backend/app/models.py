from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite stores no tz). Serialised with a trailing Z."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Ward(Base):
    __tablename__ = "wards"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Worker(Base):
    __tablename__ = "workers"
    id: Mapped[int] = mapped_column(primary_key=True)
    pseudo_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    ward_id: Mapped[int] = mapped_column(ForeignKey("wards.id"), index=True)
    task: Mapped[str] = mapped_column(String(40))
    shift_type: Mapped[str] = mapped_column(String(12), default="Morning")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ward: Mapped[Ward] = relationship()


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("severity BETWEEN 1 AND 10", name="ck_report_severity"),
        CheckConstraint("shift_hours > 0 AND shift_hours <= 16", name="ck_report_shift"),
        Index("ix_reports_ward_task_region", "ward_id", "task", "body_region"),
        Index("ix_reports_worker_region", "worker_id", "body_region"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), index=True)
    ward_id: Mapped[int] = mapped_column(ForeignKey("wards.id"), index=True)
    task: Mapped[str] = mapped_column(String(40))
    body_region: Mapped[str] = mapped_column(String(24))
    severity: Mapped[int] = mapped_column(Integer)
    shift_hours: Mapped[float] = mapped_column(Float)
    shift_type: Mapped[str] = mapped_column(String(12))
    repetitive: Mapped[bool] = mapped_column(Boolean, default=False)
    frequent_lifting: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(10), index=True)
    risk_reason: Mapped[str] = mapped_column(Text, default="")
    contributions: Mapped[list] = mapped_column(JSON, default=list)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[Optional[int]] = mapped_column(ForeignKey("reports.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    worker: Mapped[Worker] = relationship()
    ward: Mapped[Ward] = relationship()
    alert: Mapped[Optional["Alert"]] = relationship(back_populates="report", uselist=False)
    case: Mapped[Optional["Case"]] = relationship(back_populates="report", uselist=False)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), unique=True)
    level: Mapped[str] = mapped_column(String(10), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(14), default="New", index=True)  # New | Acknowledged | Closed
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    report: Mapped[Report] = relationship(back_populates="alert")
    case: Mapped[Optional["Case"]] = relationship(back_populates="alert", uselist=False)


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), unique=True)
    alert_id: Mapped[Optional[int]] = mapped_column(ForeignKey("alerts.id"), unique=True, nullable=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), index=True)
    ward_id: Mapped[int] = mapped_column(ForeignKey("wards.id"), index=True)
    task: Mapped[str] = mapped_column(String(40))
    body_region: Mapped[str] = mapped_column(String(24))
    risk_level: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(Text)
    owner: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(10))
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(22), default="Open", index=True)
    resolution_type: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report: Mapped[Report] = relationship(back_populates="case")
    alert: Mapped[Optional[Alert]] = relationship(back_populates="case")
    worker: Mapped[Worker] = relationship()
    ward: Mapped[Ward] = relationship()
    events: Mapped[list["CaseEvent"]] = relationship(order_by="CaseEvent.id")
    follow_ups: Mapped[list["FollowUp"]] = relationship(order_by="FollowUp.id")


class CaseEvent(Base):
    __tablename__ = "case_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    event_type: Mapped[str] = mapped_column(String(20))
    from_status: Mapped[Optional[str]] = mapped_column(String(22), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(22), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(60), default="operator")


class FollowUp(Base):
    __tablename__ = "follow_ups"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    outcome: Mapped[str] = mapped_column(String(14))
    notes: Mapped[str] = mapped_column(Text)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[str] = mapped_column(String(60), default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
