from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import LEVELS
from ..database import get_db
from ..models import Alert, Report
from ..schemas import AckIn
from ..serializers import alert_out
from ..services import intervention_service as svc

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(status: Optional[str] = None, ward_id: Optional[int] = None, task: Optional[str] = None, level: Optional[str] = None,
                page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = select(Alert).join(Report, Alert.report_id == Report.id)
    if status:
        stmt = stmt.where(Alert.status == status)
    if level:
        stmt = stmt.where(Alert.level == level)
    if ward_id:
        stmt = stmt.where(Report.ward_id == ward_id)
    if task:
        stmt = stmt.where(Report.task == task)
    items = [alert_out(a) for a in db.scalars(stmt)]
    items.sort(key=lambda a: (-LEVELS.index(a["level"]), not a["overdue"], not a["unassigned"], a["status"] == "Closed", a["created_at"]))
    s = (page - 1) * page_size
    return {"items": items[s:s + page_size], "total": len(items), "page": page, "page_size": page_size}


@router.get("/{alert_id}")
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    return alert_out(a)


@router.post("/{alert_id}/acknowledge")
def acknowledge(alert_id: int, p: AckIn, db: Session = Depends(get_db)):
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    svc.acknowledge_alert(db, a, p.actor)
    db.commit()
    return alert_out(a)
