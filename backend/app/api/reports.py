from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Report
from ..schemas import ReportIn
from ..serializers import alert_out, case_out, report_out
from ..services import intervention_service as svc
from ..services.metrics_service import report_conds

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", status_code=201)
def create_report(p: ReportIn, db: Session = Depends(get_db)):
    data = p.model_dump()
    allow = data.pop("allow_duplicate")
    report, alert, case, risk = svc.create_report(db, data, allow_duplicate=allow)
    note = None
    if report.duplicate_of_id:
        note = f"Saved as a flagged possible duplicate of report #{report.duplicate_of_id}."
        if not alert and report.risk_level in ("High", "Critical"):
            note += " The original report already has a case, so no new alert was created."
    db.commit()
    return {"report": report_out(report, full=True), "risk": risk, "alert": alert_out(alert) if alert else None,
            "case": case_out(case) if case else None, "note": note}


@router.get("")
def list_reports(ward_id: Optional[int] = None, task: Optional[str] = None, risk_level: Optional[str] = None, worker_id: Optional[int] = None,
                 body_region: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None,
                 page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200), db: Session = Depends(get_db)):
    conds = report_conds(date_from, date_to, ward_id, task)
    if risk_level:
        conds.append(Report.risk_level == risk_level)
    if worker_id:
        conds.append(Report.worker_id == worker_id)
    if body_region:
        conds.append(Report.body_region == body_region)
    total = db.scalar(select(func.count(Report.id)).where(*conds)) or 0
    rows = db.scalars(select(Report).where(*conds).order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [report_out(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    return {**report_out(r, full=True), "alert": alert_out(r.alert) if r.alert else None, "case": case_out(r.case) if r.case else None}
