from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import LEVELS
from ..database import get_db
from ..models import Case, Report
from ..schemas import AssignIn, CaseCreate, FollowUpIn, NoteIn, StatusIn
from ..serializers import case_out
from ..services import intervention_service as svc

router = APIRouter(prefix="/cases", tags=["cases"])


def _get(db, case_id) -> Case:
    c = db.get(Case, case_id)
    if not c:
        raise HTTPException(404, "Case not found")
    return c


@router.get("")
def list_cases(status: Optional[str] = None, ward_id: Optional[int] = None, risk_level: Optional[str] = None, owner: Optional[str] = None,
               overdue: Optional[bool] = None, unassigned: Optional[bool] = None, worker_id: Optional[int] = None,
               page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = select(Case)
    if status:
        stmt = stmt.where(Case.status == status)
    if ward_id:
        stmt = stmt.where(Case.ward_id == ward_id)
    if risk_level:
        stmt = stmt.where(Case.risk_level == risk_level)
    if worker_id:
        stmt = stmt.where(Case.worker_id == worker_id)
    if owner:
        stmt = stmt.where(Case.owner.ilike(f"%{owner}%"))
    items = [case_out(c) for c in db.scalars(stmt)]
    if overdue is not None:
        items = [i for i in items if i["overdue"] == overdue]
    if unassigned:
        items = [i for i in items if i["owner"] is None and i["status"] != "Resolved"]
    items.sort(key=lambda i: (i["status"] == "Resolved", not i["overdue"], -LEVELS.index(i["risk_level"]), i["due_date"] or "9999"))
    s = (page - 1) * page_size
    return {"items": items[s:s + page_size], "total": len(items), "page": page, "page_size": page_size}


@router.post("", status_code=201)
def create_case(p: CaseCreate, db: Session = Depends(get_db)):
    r = db.get(Report, p.report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    c = svc.open_case(db, r, r.alert, p.actor, owner=p.owner, due_date=p.due_date, priority=p.priority, action=p.recommended_action)
    db.commit()
    return case_out(c, detail=True)


@router.get("/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db)):
    return case_out(_get(db, case_id), detail=True)


@router.post("/{case_id}/assign")
def assign(case_id: int, p: AssignIn, db: Session = Depends(get_db)):
    c = _get(db, case_id)
    svc.assign_case(db, c, p.owner, p.due_date, p.priority, p.recommended_action, p.actor)
    db.commit()
    return case_out(c, detail=True)


@router.post("/{case_id}/status")
def status(case_id: int, p: StatusIn, db: Session = Depends(get_db)):
    c = _get(db, case_id)
    svc.change_status(db, c, p.to_status, p.actor, p.note, p.resolution_type)
    db.commit()
    return case_out(c, detail=True)


@router.post("/{case_id}/notes")
def note(case_id: int, p: NoteIn, db: Session = Depends(get_db)):
    c = _get(db, case_id)
    svc.add_note(db, c, p.note, p.actor)
    db.commit()
    return case_out(c, detail=True)


@router.post("/{case_id}/follow-ups", status_code=201)
def follow_up(case_id: int, p: FollowUpIn, db: Session = Depends(get_db)):
    c = _get(db, case_id)
    svc.add_follow_up(db, c, p.outcome, p.notes, p.evidence, p.actor, observed_at=p.observed_at.replace(tzinfo=None) if p.observed_at else None)
    db.commit()
    return case_out(c, detail=True)
