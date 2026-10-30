import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Case, Report
from ..serializers import case_out, iso, report_out
from ..services import metrics_service as m
from ..services.pattern_detection import detect_patterns

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    d = m.dashboard(db)
    ids = d.pop("recent_report_ids")
    cids = d.pop("outstanding_case_ids")
    reports = {r.id: r for r in db.scalars(select(Report).where(Report.id.in_(ids)))} if ids else {}
    cases = {c.id: c for c in db.scalars(select(Case).where(Case.id.in_(cids)))} if cids else {}
    d["recent_reports"] = [report_out(reports[i]) for i in ids if i in reports]
    d["outstanding_cases"] = [case_out(cases[i]) for i in cids if i in cases]
    return d


@router.get("/summary")
def summary(date_from: Optional[date] = None, date_to: Optional[date] = None, ward_id: Optional[int] = None, task: Optional[str] = None, db: Session = Depends(get_db)):
    return m.analytics_summary(db, date_from, date_to, ward_id, task)


@router.get("/patterns")
def patterns(ward_id: Optional[int] = None, window_days: Optional[int] = None, db: Session = Depends(get_db)):
    return detect_patterns(db, ward_id, window_days)


@router.get("/data-quality")
def data_quality(db: Session = Depends(get_db)):
    return m.data_quality(db)


def _safe(v):
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s  # neutralise CSV/formula injection


def _csv(name, headers, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow([_safe(x) for x in r])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/export/reports.csv")
def export_reports(date_from: Optional[date] = None, date_to: Optional[date] = None, ward_id: Optional[int] = None, task: Optional[str] = None, db: Session = Depends(get_db)):
    rows = db.scalars(select(Report).where(*m.report_conds(date_from, date_to, ward_id, task)).order_by(Report.created_at)).all()
    return _csv("safeloop_reports.csv",
                ["report_id", "created_at_utc", "worker", "ward", "task", "body_region", "severity", "shift_hours", "shift_type", "repetitive", "frequent_lifting",
                 "risk_score", "risk_level", "case", "case_status", "synthetic_demo_data", "possible_duplicate_of"],
                [[r.id, iso(r.created_at), r.worker.pseudo_id, r.ward.name, r.task, r.body_region, r.severity, r.shift_hours, r.shift_type, r.repetitive,
                  r.frequent_lifting, r.risk_score, r.risk_level, f"SL-{r.case.id:04d}" if r.case else "", r.case.status if r.case else "", r.is_synthetic,
                  r.duplicate_of_id or ""] for r in rows])


@router.get("/export/cases.csv")
def export_cases(date_from: Optional[date] = None, date_to: Optional[date] = None, ward_id: Optional[int] = None, task: Optional[str] = None, db: Session = Depends(get_db)):
    rows = db.scalars(select(Case).join(Report, Case.report_id == Report.id).where(*m.report_conds(date_from, date_to, ward_id, task)).order_by(Case.id)).all()
    return _csv("safeloop_cases.csv",
                ["case", "status", "resolution_type", "risk_level", "priority", "ward", "task", "body_region", "owner", "due_date", "overdue", "created_at_utc",
                 "assigned_at_utc", "started_at_utc", "resolved_at_utc", "follow_ups", "latest_outcome", "report_id"],
                [[c["code"], c["status"], c["resolution_type"], c["risk_level"], c["priority"], c["ward"], c["task"], c["body_region"], c["owner"], c["due_date"],
                  c["overdue"], c["created_at"], c["assigned_at"], c["started_at"], c["resolved_at"], c["follow_up_count"], c["latest_outcome"], c["report_id"]]
                 for c in (case_out(x) for x in rows)])
