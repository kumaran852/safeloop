from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import REGION_LABELS
from ..models import Alert, Case, CaseEvent, FollowUp, Report, Ward, Worker, utcnow
from .risk_engine import RiskInput, reason_text, score_report
from .settings_service import get_settings

STATUSES = ["Open", "Assigned", "In Progress", "Pending Verification", "Resolved", "Reopened"]
TRANSITIONS = {
    "Open": ["Assigned"],
    "Assigned": ["In Progress"],
    "In Progress": ["Pending Verification"],
    "Pending Verification": ["Resolved", "Reopened", "In Progress"],
    "Resolved": ["Reopened"],
    "Reopened": ["Assigned", "In Progress"],
}
OUTCOMES = ["Improved", "No change", "Worsened", "Recurrence"]
BAD_OUTCOMES = {"No change", "Worsened", "Recurrence"}
RESOLUTION_TYPES = ["verified_improvement", "administrative_closure"]
PRIORITY_FOR = {"Critical": "Urgent", "High": "High", "Moderate": "Medium", "Low": "Low"}
DUE_DAYS = {"Urgent": 2, "High": 5, "Medium": 10, "Low": 14}


class DomainError(Exception):
    def __init__(self, status_code: int, message: str, extra: Optional[dict] = None):
        super().__init__(message)
        self.status_code, self.message, self.extra = status_code, message, extra


def recommend_action(region: str, level: str, repetitive: bool, lifting: bool) -> str:
    label = REGION_LABELS.get(region, region).lower()
    steps = ["Supervisor to speak with the worker and review the task before the due date"]
    if lifting:
        steps.append("check lifting method, load size and availability of carts or lifting aids")
    if repetitive:
        steps.append("consider task rotation and short recovery breaks")
    steps.append(f"inspect equipment and workload relevant to {label} discomfort")
    if level in ("High", "Critical"):
        steps.append("refer to qualified occupational-health personnel if discomfort persists")
    return "; ".join(steps) + ". This is a prevention prompt, not a medical diagnosis."


def _event(db, case, etype, actor, note=None, frm=None, to=None, now=None):
    db.add(CaseEvent(case_id=case.id, ts=now or utcnow(), event_type=etype, from_status=frm, to_status=to, note=note, actor=actor or "operator"))


def find_duplicate(db: Session, worker_id, region, severity, now, hours):
    return db.scalars(
        select(Report)
        .where(Report.worker_id == worker_id, Report.body_region == region,
               Report.created_at >= now - timedelta(hours=hours), Report.created_at <= now,
               Report.severity.between(severity - 1, severity + 1))
        .order_by(Report.id.desc())
    ).first()


def create_report(db: Session, data: dict, now: Optional[datetime] = None, synthetic: bool = False, allow_duplicate: bool = False):
    now = now or utcnow()
    worker = db.get(Worker, data["worker_id"])
    if not worker:
        raise DomainError(404, "Worker not found")
    ward = db.get(Ward, data["ward_id"])
    if not ward or not ward.active:
        raise DomainError(422, "Ward not found or inactive")
    cfg = get_settings(db)
    if data["task"] not in cfg["tasks"]:
        raise DomainError(422, f"Unknown task '{data['task']}'. Configured tasks: {', '.join(cfg['tasks'])}")
    region = data["body_region"]
    dup = find_duplicate(db, worker.id, region, data["severity"], now, cfg["duplicate_window_hours"])
    if dup and not allow_duplicate:
        raise DomainError(409, f"Possible duplicate of report #{dup.id} (same worker and body region within {cfg['duplicate_window_hours']} h, similar severity).",
                          {"code": "possible_duplicate", "duplicate_of": dup.id,
                           "message": f"Possible duplicate of report #{dup.id}. Submit again with 'allow duplicate' to save it as a flagged duplicate."})
    since = now - timedelta(days=cfg["pattern"]["window_days"])
    base = [Report.created_at >= since, Report.created_at < now, Report.duplicate_of_id.is_(None), Report.body_region == region]
    prior = db.scalar(select(func.count(Report.id)).where(Report.worker_id == worker.id, *base)) or 0
    peers = db.scalar(select(func.count(Report.id)).where(Report.ward_id == ward.id, Report.task == data["task"], Report.worker_id != worker.id, *base)) or 0
    unverified = db.scalar(select(func.count(Case.id)).where(
        Case.worker_id == worker.id, Case.body_region == region,
        or_(Case.resolution_type.is_(None), Case.resolution_type != "verified_improvement"))) or 0
    risk = score_report(RiskInput(data["severity"], data["shift_hours"], data["repetitive"], data["frequent_lifting"], prior, peers, unverified), cfg["thresholds"])
    report = Report(
        worker_id=worker.id, ward_id=ward.id, task=data["task"], body_region=region, severity=data["severity"],
        shift_hours=data["shift_hours"], shift_type=data["shift_type"], repetitive=data["repetitive"],
        frequent_lifting=data["frequent_lifting"], description=data.get("description"),
        risk_score=risk["score"], risk_level=risk["level"], risk_reason=reason_text(risk),
        contributions=risk["contributions"] + [{"factor": "note", "points": 0, "detail": n} for n in risk["notes"]],
        is_synthetic=synthetic, duplicate_of_id=dup.id if dup else None, created_at=now)
    db.add(report)
    db.flush()
    alert = case = None
    covered = dup is not None and (db.scalar(select(func.count(Case.id)).where(Case.report_id == dup.id)) or 0) > 0
    if risk["level"] in ("High", "Critical") and not covered:
        alert = Alert(report_id=report.id, level=risk["level"], reason=report.risk_reason, status="New", created_at=now)
        db.add(alert)
        db.flush()
        case = open_case(db, report, alert, "system", now)
    return report, alert, case, risk


def open_case(db: Session, report: Report, alert: Optional[Alert], actor: str, now: Optional[datetime] = None,
              owner: Optional[str] = None, due_date=None, priority: Optional[str] = None, action: Optional[str] = None) -> Case:
    now = now or utcnow()
    if db.scalar(select(func.count(Case.id)).where(Case.report_id == report.id)):
        raise DomainError(409, "This report already has a case")
    prio = priority or PRIORITY_FOR[report.risk_level]
    case = Case(report_id=report.id, alert_id=alert.id if alert else None, worker_id=report.worker_id, ward_id=report.ward_id,
                task=report.task, body_region=report.body_region, risk_level=report.risk_level, reason=report.risk_reason,
                recommended_action=action or recommend_action(report.body_region, report.risk_level, report.repetitive, report.frequent_lifting),
                priority=prio, due_date=due_date or (now + timedelta(days=DUE_DAYS[prio])).date(),
                status="Open", created_at=now, updated_at=now)
    db.add(case)
    db.flush()
    _event(db, case, "created", actor, f"Case opened from report #{report.id} ({report.risk_level}).", None, "Open", now)
    if owner:
        assign_case(db, case, owner, None, None, None, actor, now)
    return case


def assign_case(db, case: Case, owner, due_date, priority, action, actor, now=None):
    now = now or utcnow()
    if case.status == "Resolved":
        raise DomainError(409, "Resolved cases cannot be edited. Reopen the case first.")
    owner = (owner or "").strip()
    if not owner:
        raise DomainError(422, "An owner is required")
    changed = []
    if case.owner != owner:
        changed.append(f"owner: {case.owner or 'unassigned'} -> {owner}")
        case.owner = owner
    if due_date and case.due_date != due_date:
        changed.append(f"due date: {case.due_date} -> {due_date}")
        case.due_date = due_date
    if priority and case.priority != priority:
        changed.append(f"priority: {case.priority} -> {priority}")
        case.priority = priority
    if action and action.strip() and case.recommended_action != action.strip():
        changed.append("recommended action updated")
        case.recommended_action = action.strip()
    prev = case.status
    if prev in ("Open", "Reopened"):
        case.status = "Assigned"
        case.assigned_at = case.assigned_at or now
    case.updated_at = now
    _event(db, case, "assigned" if prev in ("Open", "Reopened") else "reassigned", actor, "; ".join(changed) or "Assignment confirmed", prev, case.status, now)
    a = case.alert
    if a and a.status == "New":
        a.status, a.acknowledged_at, a.acknowledged_by = "Acknowledged", now, actor or "operator"
    return case


def _latest_followup(db, case_id):
    return db.scalars(select(FollowUp).where(FollowUp.case_id == case_id).order_by(FollowUp.id.desc())).first()


def change_status(db, case: Case, to: str, actor, note=None, resolution_type=None, now=None):
    now = now or utcnow()
    if to not in STATUSES:
        raise DomainError(422, f"Unknown status '{to}'")
    if to == case.status:
        raise DomainError(409, f"Case is already {to}")
    if to not in TRANSITIONS[case.status]:
        raise DomainError(409, f"Cannot move from {case.status} to {to}. Allowed: {', '.join(TRANSITIONS[case.status])}")
    note = (note or "").strip() or None
    if to in ("Assigned", "In Progress") and not case.owner:
        raise DomainError(409, "Assign an owner first")
    if to == "Assigned" and not case.due_date:
        raise DomainError(409, "Set a due date first")
    if to == "Reopened" and not note:
        raise DomainError(422, "A reason is required to reopen a case")
    prev = case.status
    if to == "Resolved":
        if resolution_type not in RESOLUTION_TYPES:
            raise DomainError(422, f"resolution_type must be one of {', '.join(RESOLUTION_TYPES)}")
        latest = _latest_followup(db, case.id)
        if resolution_type == "verified_improvement" and not (latest and latest.outcome == "Improved"):
            raise DomainError(409, "Verified improvement requires a follow-up observation with outcome 'Improved'. Record one, or close administratively.")
        if resolution_type == "administrative_closure" and not note:
            raise DomainError(422, "A note is required for administrative closure")
        case.resolution_type, case.resolved_at = resolution_type, now
    if to == "In Progress" and not case.started_at:
        case.started_at = now
    if to == "Reopened":
        case.resolution_type, case.resolved_at = None, None
    case.status, case.updated_at = to, now
    _event(db, case, "status_change", actor, note, prev, to, now)
    if case.alert:
        if to == "Resolved":
            case.alert.status = "Closed"
        elif to == "Reopened":
            case.alert.status = "Acknowledged"
    return case


def add_note(db, case, note, actor, now=None):
    now = now or utcnow()
    note = (note or "").strip()
    if len(note) < 2:
        raise DomainError(422, "Note is empty")
    _event(db, case, "note", actor, note, None, None, now)
    case.updated_at = now
    return case


def add_follow_up(db, case: Case, outcome, notes, evidence, actor, observed_at=None, now=None):
    now = now or utcnow()
    if case.status not in ("In Progress", "Pending Verification", "Resolved"):
        raise DomainError(409, f"Follow-ups can be recorded once work has started (current status: {case.status})")
    if outcome not in OUTCOMES:
        raise DomainError(422, f"outcome must be one of {', '.join(OUTCOMES)}")
    notes = (notes or "").strip()
    if len(notes) < 3:
        raise DomainError(422, "Follow-up notes are required")
    fu = FollowUp(case_id=case.id, observed_at=observed_at or now, outcome=outcome, notes=notes,
                  evidence=(evidence or "").strip() or None, recorded_by=actor or "operator", created_at=now)
    db.add(fu)
    db.flush()
    _event(db, case, "follow_up", actor, f"{outcome}: {notes}", None, None, now)
    case.updated_at = now
    if outcome in BAD_OUTCOMES and case.status in ("Pending Verification", "Resolved"):
        prev = case.status
        case.status, case.resolution_type, case.resolved_at = "Reopened", None, None
        _event(db, case, "status_change", "system", f"Automatically reopened: follow-up outcome '{outcome}' indicates a continuing issue.", prev, "Reopened", now)
        if case.alert:
            case.alert.status = "Acknowledged"
    return fu


def acknowledge_alert(db, alert: Alert, actor, now=None):
    if alert.status != "New":
        raise DomainError(409, f"Alert is already {alert.status}")
    alert.status, alert.acknowledged_at, alert.acknowledged_by = "Acknowledged", now or utcnow(), actor or "operator"
    return alert
