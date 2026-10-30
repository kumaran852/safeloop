from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import BODY_REGIONS, DATABASE_URL, LEVELS, REGION_LABELS, SHIFT_TYPES
from ..database import Base, SessionLocal, engine, get_db
from ..models import Case, Report, Ward, Worker
from ..schemas import ResetIn, SettingsIn
from ..seed import seed_demo, seed_reference
from ..services.intervention_service import OUTCOMES, STATUSES, TRANSITIONS
from ..services.risk_engine import WEIGHTS
from ..services.settings_service import get_settings, set_setting

router = APIRouter(tags=["settings"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok", "service": "safeloop-api"}


@router.get("/meta")
def meta(db: Session = Depends(get_db)):
    cfg = get_settings(db)
    wards = [{"id": w.id, "code": w.code, "name": w.name, "active": w.active} for w in db.scalars(select(Ward).order_by(Ward.code))]
    return {"tasks": cfg["tasks"], "body_regions": [{"key": k, "label": REGION_LABELS[k]} for k in BODY_REGIONS], "shift_types": SHIFT_TYPES,
            "levels": LEVELS, "statuses": STATUSES, "transitions": TRANSITIONS, "outcomes": OUTCOMES, "wards": wards}


@router.get("/settings")
def get_cfg(db: Session = Depends(get_db)):
    syn = db.scalar(select(func.count(Report.id)).where(Report.is_synthetic.is_(True))) or 0
    tot = db.scalar(select(func.count(Report.id))) or 0
    return {**get_settings(db), "weights": WEIGHTS, "demo": {"synthetic_reports": syn, "observed_reports": tot - syn,
            "workers": db.scalar(select(func.count(Worker.id))) or 0, "cases": db.scalar(select(func.count(Case.id))) or 0},
            "database": DATABASE_URL.split("///")[-1]}


@router.put("/settings")
def put_cfg(p: SettingsIn, db: Session = Depends(get_db)):
    cur = get_settings(db)
    if p.thresholds is not None:
        t = {k: p.thresholds.get(k) for k in ("moderate", "high", "critical")}
        if not all(isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 100 for v in t.values()) or not t["moderate"] < t["high"] < t["critical"]:
            raise HTTPException(422, "Thresholds must be integers 1-100 with moderate < high < critical")
        set_setting(db, "thresholds", t)
    if p.pattern is not None:
        q = {k: p.pattern.get(k, cur["pattern"][k]) for k in ("window_days", "min_reports", "min_workers")}
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in q.values()) or not (7 <= q["window_days"] <= 180 and 2 <= q["min_reports"] <= 50 and 2 <= q["min_workers"] <= 50):
            raise HTTPException(422, "Pattern window 7-180 days; minimum reports and workers must be at least 2 (single observations never form a pattern)")
        set_setting(db, "pattern", q)
    if p.tasks is not None:
        tasks = [t.strip() for t in p.tasks if t.strip()]
        if not tasks or any(len(t) > 40 for t in tasks) or len(set(tasks)) != len(tasks):
            raise HTTPException(422, "Provide at least one unique task name (max 40 characters)")
        set_setting(db, "tasks", tasks)
    if p.repeat_window_days is not None:
        set_setting(db, "repeat_window_days", p.repeat_window_days)
    db.commit()
    return get_settings(db)


@router.post("/admin/reset")
def reset(p: ResetIn):
    if p.confirm != "RESET":
        raise HTTPException(400, "Type RESET to confirm")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_reference(db)
        if p.demo:
            seed_demo(db)
        db.commit()
    return {"status": "reset", "demo_data": p.demo}
