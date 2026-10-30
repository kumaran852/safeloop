from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, median
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import LEVELS, REGION_LABELS
from ..models import Alert, Case, Report, Worker, utcnow
from .settings_service import get_settings


def _hours(a, b):
    return (b - a).total_seconds() / 3600


def _stat(vals):
    if not vals:
        return {"available": False, "n": 0, "median_hours": None, "mean_hours": None}
    return {"available": True, "n": len(vals), "median_hours": round(median(vals), 1), "mean_hours": round(mean(vals), 1)}


def _rate(num, den):
    return {"num": num, "den": den, "pct": round(100 * num / den, 1) if den else None}


def week_start(d: datetime) -> date:
    return (d - timedelta(days=d.weekday())).date()


def report_conds(date_from: Optional[date], date_to: Optional[date], ward_id: Optional[int], task: Optional[str] = None):
    c = []
    if date_from:
        c.append(Report.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        c.append(Report.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    if ward_id:
        c.append(Report.ward_id == ward_id)
    if task:
        c.append(Report.task == task)
    return c


def is_overdue(c: Case, today: date) -> bool:
    return c.status != "Resolved" and c.due_date is not None and c.due_date < today


def case_stats(cases, today: date) -> dict:
    started = [c for c in cases if c.started_at]
    resolved = [c for c in cases if c.status == "Resolved"]
    latest = [c.follow_ups[-1].outcome for c in cases if c.follow_ups]
    return {
        "total": len(cases),
        "open": sum(1 for c in cases if c.status != "Resolved"),
        "overdue": sum(1 for c in cases if is_overdue(c, today)),
        "unassigned_high_priority": sum(1 for c in cases if c.owner is None and c.status != "Resolved" and c.risk_level in ("High", "Critical")),
        "resolved": len(resolved),
        "completion_rate": _rate(len(resolved), len(cases)),
        "followup_documented": _rate(sum(1 for c in started if c.follow_ups), len(started)),
        "verified_improvement": _rate(sum(1 for c in resolved if c.resolution_type == "verified_improvement"), len(resolved)),
        "administrative_closures": sum(1 for c in resolved if c.resolution_type == "administrative_closure"),
        "latest_outcomes": dict(Counter(latest)),
        "status_counts": dict(Counter(c.status for c in cases)),
    }


def analytics_summary(db: Session, date_from=None, date_to=None, ward_id=None, task=None) -> dict:
    cfg = get_settings(db)
    now = utcnow()
    conds = report_conds(date_from, date_to, ward_id, task)
    reports = db.scalars(select(Report).where(*conds).order_by(Report.created_at)).all()
    cases = db.scalars(select(Case).join(Report, Case.report_id == Report.id).where(*conds)).all()
    alerts = db.scalars(select(Alert).join(Report, Alert.report_id == Report.id).where(*conds)).all()

    weekly = defaultdict(lambda: {"reports": 0, "high_or_critical": 0})
    for r in reports:
        w = weekly[week_start(r.created_at).isoformat()]
        w["reports"] += 1
        w["high_or_critical"] += r.risk_level in ("High", "Critical")
    dist = Counter(r.risk_level for r in reports)
    by_region = defaultdict(list)
    wt = defaultdict(list)
    for r in reports:
        by_region[r.body_region].append(r)
        wt[(r.ward.name, r.task)].append(r)

    ack = [_hours(a.report.created_at, a.acknowledged_at) for a in alerts if a.acknowledged_at]
    assign = [_hours(c.report.created_at, c.assigned_at) for c in cases if c.assigned_at]
    interv = [_hours(c.report.created_at, c.started_at) for c in cases if c.started_at]

    win = cfg["repeat_window_days"]
    eligible = [c for c in cases if c.started_at and c.started_at + timedelta(days=win) <= now]
    repeat = 0
    for c in eligible:
        n = db.scalar(select(func.count(Report.id)).where(
            Report.worker_id == c.worker_id, Report.body_region == c.body_region, Report.duplicate_of_id.is_(None),
            Report.created_at > c.started_at, Report.created_at <= c.started_at + timedelta(days=win))) or 0
        repeat += n > 0

    return {
        "filters": {"date_from": date_from, "date_to": date_to, "ward_id": ward_id, "task": task},
        "sample": {"reports": len(reports), "cases": len(cases), "alerts": len(alerts),
                   "synthetic_reports": sum(r.is_synthetic for r in reports),
                   "observed_reports": sum(not r.is_synthetic for r in reports)},
        "weekly_volume": [{"week": k, **v} for k, v in sorted(weekly.items())],
        "risk_distribution": [{"level": l, "count": dist.get(l, 0)} for l in LEVELS],
        "by_region": [{"region": k, "label": REGION_LABELS.get(k, k), "count": len(v), "avg_score": round(mean(x.risk_score for x in v), 1)} for k, v in sorted(by_region.items(), key=lambda kv: -len(kv[1]))],
        "ward_task": [{"ward": k[0], "task": k[1], "reports": len(v), "avg_score": round(mean(x.risk_score for x in v), 1),
                       "high_or_critical": sum(x.risk_level in ("High", "Critical") for x in v)} for k, v in sorted(wt.items())],
        "response_times": {"acknowledgement": _stat(ack), "assignment": _stat(assign), "intervention": _stat(interv),
                           "definition": "Hours from report submission to alert acknowledgement / first assignment / work started. Only cases with the timestamp recorded are counted (n shown)."},
        "cases": case_stats(cases, now.date()),
        "repeat_reports": {"window_days": win, "eligible_interventions": len(eligible), "with_repeat_report": repeat,
                           "pct": round(100 * repeat / len(eligible), 1) if eligible else None,
                           "definition": f"Interventions started at least {win} days ago where the same worker filed another non-duplicate report for the same body region within {win} days after work started. Association only; not proof of cause."},
        "unavailable": [m for m, ok in [("response_times.acknowledgement", ack), ("response_times.assignment", assign), ("response_times.intervention", interv), ("repeat_reports", eligible)] if not ok],
    }


def dashboard(db: Session) -> dict:
    now = utcnow()
    reports = db.scalars(select(Report)).all()
    cases = db.scalars(select(Case)).all()
    cs = case_stats(cases, now.date())
    active_alerts = db.scalar(select(func.count(Alert.id)).where(Alert.level.in_(["High", "Critical"]), Alert.status.in_(["New", "Acknowledged"]))) or 0
    unack = db.scalar(select(func.count(Alert.id)).where(Alert.status == "New")) or 0
    weeks = [week_start(now - timedelta(days=7 * i)) for i in range(7, -1, -1)]
    wk = {w.isoformat(): {"week": w.isoformat(), "reports": 0, "high_or_critical": 0} for w in weeks}
    for r in reports:
        k = week_start(r.created_at).isoformat()
        if k in wk:
            wk[k]["reports"] += 1
            wk[k]["high_or_critical"] += r.risk_level in ("High", "Critical")
    reg, ward, task = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in reports:
        reg[r.body_region].append(r.risk_score)
        ward[r.ward.name].append(r.risk_score)
        task[r.task].append(r.risk_score)

    def comp(d, key):
        return [{key: k, "reports": len(v), "avg_score": round(mean(v), 1)} for k, v in sorted(d.items())]

    outstanding = sorted([c for c in cases if c.status != "Resolved"],
                         key=lambda c: (not is_overdue(c, now.date()), -LEVELS.index(c.risk_level), c.due_date or date.max))[:8]
    return {
        "totals": {"workers": db.scalar(select(func.count(Worker.id))) or 0, "reports": len(reports), "high_priority_alerts": active_alerts,
                   "unacknowledged_alerts": unack, "open_cases": cs["open"], "overdue_cases": cs["overdue"],
                   "unassigned_high_priority": cs["unassigned_high_priority"], "followup_rate": cs["followup_documented"],
                   "synthetic_reports": sum(r.is_synthetic for r in reports)},
        "weekly": list(wk.values()),
        "by_region": [{"label": REGION_LABELS.get(k, k), "reports": len(v), "avg_score": round(mean(v), 1)} for k, v in sorted(reg.items(), key=lambda kv: -len(kv[1]))],
        "by_ward": comp(ward, "ward"), "by_task": comp(task, "task"),
        "recent_report_ids": [r.id for r in sorted(reports, key=lambda r: r.created_at, reverse=True)[:8]],
        "outstanding_case_ids": [c.id for c in outstanding],
    }


def data_quality(db: Session) -> list:
    today = utcnow().date()
    cases = db.scalars(select(Case)).all()
    reports = db.scalars(select(Report)).all()

    def issue(code, title, sev, items, hint):
        return {"code": code, "title": title, "severity": sev, "count": len(items), "items": items[:10], "hint": hint}

    cl = lambda c: {"type": "case", "id": c.id, "label": f"SL-{c.id:04d} ({c.ward.name}, {c.status})"}
    rl = lambda r: {"type": "report", "id": r.id, "label": f"Report #{r.id} ({r.worker.pseudo_id})"}
    return [
        issue("unassigned_high", "High-priority cases with no owner", "high", [cl(c) for c in cases if c.owner is None and c.status != "Resolved" and c.risk_level in ("High", "Critical")], "Assign an owner and due date."),
        issue("overdue", "Overdue interventions", "high", [cl(c) for c in cases if is_overdue(c, today)], "Follow up with the owner or renegotiate the due date."),
        issue("missing_followup", "Pending/resolved cases with no follow-up observation", "medium", [cl(c) for c in cases if c.status in ("Pending Verification", "Resolved") and not c.follow_ups], "Record a follow-up observation."),
        issue("admin_closure", "Resolved by administrative closure (not verified)", "low", [cl(c) for c in cases if c.resolution_type == "administrative_closure"], "Closure is not evidence of improvement."),
        issue("duplicates", "Reports flagged as possible duplicates", "low", [rl(r) for r in reports if r.duplicate_of_id], "Kept in the data, excluded from pattern/repeat counts."),
        issue("ward_mismatch", "Report ward differs from worker's registered ward", "low", [rl(r) for r in reports if r.ward_id != r.worker.ward_id], "May be legitimate (cover shifts) or a data-entry error."),
    ]
