import re
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .config import BODY_REGIONS, SHIFT_TYPES

Region = Literal[tuple(BODY_REGIONS)]  # type: ignore[valid-type]
Shift = Literal[tuple(SHIFT_TYPES)]  # type: ignore[valid-type]
Priority = Literal["Low", "Medium", "High", "Urgent"]
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class WorkerIn(BaseModel):
    pseudo_id: Optional[str] = Field(default=None, pattern=r"^[A-Za-z0-9\-]{3,20}$")
    ward_id: int
    task: str = Field(min_length=2, max_length=40)
    shift_type: Shift = "Morning"
    active: bool = True


class WorkerPatch(BaseModel):
    ward_id: Optional[int] = None
    task: Optional[str] = Field(default=None, min_length=2, max_length=40)
    shift_type: Optional[Shift] = None
    active: Optional[bool] = None


class ReportIn(BaseModel):
    worker_id: int
    ward_id: int
    task: str = Field(min_length=2, max_length=40)
    body_region: Region
    severity: int = Field(ge=1, le=10)
    shift_hours: float = Field(gt=0, le=16)
    shift_type: Shift
    repetitive: bool = False
    frequent_lifting: bool = False
    description: Optional[str] = Field(default=None, max_length=500)
    allow_duplicate: bool = False

    @field_validator("description")
    @classmethod
    def _desc(cls, v):
        if v is None:
            return None
        return _CTRL.sub("", v).strip() or None


class CaseCreate(BaseModel):
    report_id: int
    owner: Optional[str] = Field(default=None, max_length=80)
    due_date: Optional[date] = None
    priority: Optional[Priority] = None
    recommended_action: Optional[str] = Field(default=None, max_length=1000)
    actor: str = Field(default="operator", max_length=60)


class AssignIn(BaseModel):
    owner: str = Field(min_length=2, max_length=80)
    due_date: Optional[date] = None
    priority: Optional[Priority] = None
    recommended_action: Optional[str] = Field(default=None, max_length=1000)
    actor: str = Field(default="operator", max_length=60)


class StatusIn(BaseModel):
    to_status: str
    note: Optional[str] = Field(default=None, max_length=1000)
    resolution_type: Optional[Literal["verified_improvement", "administrative_closure"]] = None
    actor: str = Field(default="operator", max_length=60)


class NoteIn(BaseModel):
    note: str = Field(min_length=2, max_length=1000)
    actor: str = Field(default="operator", max_length=60)


class FollowUpIn(BaseModel):
    outcome: Literal["Improved", "No change", "Worsened", "Recurrence"]
    notes: str = Field(min_length=3, max_length=1000)
    evidence: Optional[str] = Field(default=None, max_length=1000)
    observed_at: Optional[datetime] = None
    actor: str = Field(default="operator", max_length=60)


class AckIn(BaseModel):
    actor: str = Field(default="operator", max_length=60)


class WardIn(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z0-9\-]{2,10}$")
    name: str = Field(min_length=2, max_length=80)


class WardPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    active: Optional[bool] = None


class SettingsIn(BaseModel):
    thresholds: Optional[dict] = None
    pattern: Optional[dict] = None
    tasks: Optional[list[str]] = Field(default=None, max_length=20)
    repeat_window_days: Optional[int] = Field(default=None, ge=7, le=180)


class ResetIn(BaseModel):
    confirm: str
    demo: bool = True
