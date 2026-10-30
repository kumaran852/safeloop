from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DEFAULT_TASKS
from ..models import Setting
from .risk_engine import DEFAULT_THRESHOLDS

DEFAULTS = {
    "thresholds": dict(DEFAULT_THRESHOLDS),
    "pattern": {"window_days": 30, "min_reports": 3, "min_workers": 2},
    "tasks": list(DEFAULT_TASKS),
    "repeat_window_days": 30,
    "duplicate_window_hours": 24,
}


def get_settings(db: Session) -> dict:
    out = deepcopy(DEFAULTS)
    for row in db.scalars(select(Setting)):
        if row.key in out:
            out[row.key] = {**out[row.key], **row.value} if isinstance(out[row.key], dict) else row.value
    return out


def set_setting(db: Session, key: str, value) -> None:
    row = db.get(Setting, key)
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.flush()
