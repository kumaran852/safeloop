from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Case, Report, Ward, Worker
from ..schemas import WorkerIn, WorkerPatch
from ..serializers import case_out, iso, report_out, worker_out
from ..services.settings_service import get_settings

router = APIRouter(prefix="/workers", tags=["workers"])


def _check(db, ward_id, task):
    w = db.get(Ward, ward_id)
    if not w or not w.active:
        raise HTTPException(422, "Ward not found or inactive")
    if task not in get_settings(db)["tasks"]:
        raise HTTPException(422, "Unknown task")


def _extra(db, w):
    n = db.scalar(select(func.count(Report.id)).where(Report.worker_id == w.id)) or 0
    last = db.scalar(select(func.max(Report.created_at)).where(Report.worker_id == w.id))
    open_c = db.scalar(select(func.count(Case.id)).where(Case.worker_id == w.id, Case.status != "Resolved")) or 0
    return {"report_count": n, "last_report_at": iso(last), "open_cases": open_c}


@router.get("")
def list_workers(q: Optional[str] = None, ward_id: Optional[int] = None, task: Optional[str] = None, active: Optional[bool] = None,
                 page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200), db: Session = Depends(get_db)):
    conds = []
    if q:
        conds.append(Worker.pseudo_id.ilike(f"%{q.strip()}%"))
    if ward_id:
        conds.append(Worker.ward_id == ward_id)
    if task:
        conds.append(Worker.task == task)
    if active is not None:
        conds.append(Worker.active == active)
    total = db.scalar(select(func.count(Worker.id)).where(*conds)) or 0
    rows = db.scalars(select(Worker).where(*conds).order_by(Worker.pseudo_id).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [worker_out(w, _extra(db, w)) for w in rows], "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201)
def create_worker(p: WorkerIn, db: Session = Depends(get_db)):
    _check(db, p.ward_id, p.task)
    pid = p.pseudo_id
    if pid and db.scalar(select(func.count(Worker.id)).where(Worker.pseudo_id == pid)):
        raise HTTPException(409, f"Worker ID {pid} already exists")
    w = Worker(pseudo_id=pid or "TMP", ward_id=p.ward_id, task=p.task, shift_type=p.shift_type, active=p.active)
    db.add(w)
    db.flush()
    if not pid:
        w.pseudo_id = f"SW-{w.id:04d}"
        while db.scalar(select(func.count(Worker.id)).where(Worker.pseudo_id == w.pseudo_id, Worker.id != w.id)):
            w.pseudo_id += "x"
    db.commit()
    return worker_out(w, _extra(db, w))


@router.get("/{worker_id}")
def get_worker(worker_id: int, db: Session = Depends(get_db)):
    w = db.get(Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    reports = db.scalars(select(Report).where(Report.worker_id == w.id).order_by(Report.created_at.desc()).limit(50)).all()
    cases = db.scalars(select(Case).where(Case.worker_id == w.id).order_by(Case.created_at.desc())).all()
    return {**worker_out(w, _extra(db, w)), "reports": [report_out(r) for r in reports], "cases": [case_out(c) for c in cases]}


@router.patch("/{worker_id}")
def patch_worker(worker_id: int, p: WorkerPatch, db: Session = Depends(get_db)):
    w = db.get(Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    data = p.model_dump(exclude_unset=True)
    _check(db, data.get("ward_id", w.ward_id), data.get("task", w.task))
    for k, v in data.items():
        if v is not None:
            setattr(w, k, v)
    db.commit()
    return worker_out(w, _extra(db, w))


@router.delete("/{worker_id}", status_code=204)
def delete_worker(worker_id: int, db: Session = Depends(get_db)):
    w = db.get(Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if db.scalar(select(func.count(Report.id)).where(Report.worker_id == w.id)):
        raise HTTPException(409, "Worker has reports and cannot be deleted. Mark the worker inactive instead.")
    db.delete(w)
    db.commit()
