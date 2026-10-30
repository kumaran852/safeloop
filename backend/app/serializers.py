from .config import REGION_LABELS
from .models import Alert, Case, CaseEvent, FollowUp, Report, Worker, utcnow
from .services.metrics_service import is_overdue


def iso(dt):
    return dt.isoformat() + "Z" if dt else None


def worker_out(w: Worker, extra=None):
    d = {"id": w.id, "pseudo_id": w.pseudo_id, "ward_id": w.ward_id, "ward": w.ward.name, "task": w.task, "shift_type": w.shift_type,
         "active": w.active, "is_synthetic": w.is_synthetic, "created_at": iso(w.created_at)}
    d.update(extra or {})
    return d


def report_out(r: Report, full=False):
    d = {"id": r.id, "created_at": iso(r.created_at), "worker_id": r.worker_id, "worker": r.worker.pseudo_id, "ward_id": r.ward_id,
         "ward": r.ward.name, "task": r.task, "body_region": r.body_region, "body_region_label": REGION_LABELS.get(r.body_region, r.body_region),
         "severity": r.severity, "risk_score": r.risk_score, "risk_level": r.risk_level, "is_synthetic": r.is_synthetic,
         "duplicate_of_id": r.duplicate_of_id, "alert_id": r.alert.id if r.alert else None,
         "case_id": r.case.id if r.case else None, "case_status": r.case.status if r.case else None}
    if full:
        d.update({"shift_hours": r.shift_hours, "shift_type": r.shift_type, "repetitive": r.repetitive, "frequent_lifting": r.frequent_lifting,
                  "description": r.description, "risk_reason": r.risk_reason, "contributions": r.contributions})
    return d


def case_brief(c: Case):
    return {"id": c.id, "code": f"SL-{c.id:04d}", "status": c.status, "owner": c.owner,
            "due_date": c.due_date.isoformat() if c.due_date else None, "overdue": is_overdue(c, utcnow().date())}


def alert_out(a: Alert):
    c, r = a.case, a.report
    return {"id": a.id, "level": a.level, "status": a.status, "reason": a.reason, "created_at": iso(a.created_at),
            "acknowledged_at": iso(a.acknowledged_at), "acknowledged_by": a.acknowledged_by,
            "report_id": r.id, "worker": r.worker.pseudo_id, "ward_id": r.ward_id, "ward": r.ward.name, "task": r.task,
            "body_region_label": REGION_LABELS.get(r.body_region, r.body_region), "severity": r.severity, "risk_score": r.risk_score,
            "case": case_brief(c) if c else None, "unassigned": bool(c and c.owner is None and c.status != "Resolved"),
            "overdue": bool(c and is_overdue(c, utcnow().date()))}


def event_out(e: CaseEvent):
    return {"id": e.id, "ts": iso(e.ts), "event_type": e.event_type, "from_status": e.from_status, "to_status": e.to_status, "note": e.note, "actor": e.actor}


def followup_out(f: FollowUp):
    return {"id": f.id, "observed_at": iso(f.observed_at), "outcome": f.outcome, "notes": f.notes, "evidence": f.evidence, "recorded_by": f.recorded_by}


def case_out(c: Case, detail=False):
    d = {"id": c.id, "code": f"SL-{c.id:04d}", "report_id": c.report_id, "alert_id": c.alert_id, "worker_id": c.worker_id,
         "worker": c.worker.pseudo_id, "ward_id": c.ward_id, "ward": c.ward.name, "task": c.task, "body_region": c.body_region,
         "body_region_label": REGION_LABELS.get(c.body_region, c.body_region), "risk_level": c.risk_level, "reason": c.reason,
         "owner": c.owner, "recommended_action": c.recommended_action, "priority": c.priority,
         "due_date": c.due_date.isoformat() if c.due_date else None, "status": c.status, "resolution_type": c.resolution_type,
         "overdue": is_overdue(c, utcnow().date()), "follow_up_count": len(c.follow_ups),
         "latest_outcome": c.follow_ups[-1].outcome if c.follow_ups else None,
         "created_at": iso(c.created_at), "updated_at": iso(c.updated_at), "assigned_at": iso(c.assigned_at),
         "started_at": iso(c.started_at), "resolved_at": iso(c.resolved_at)}
    if detail:
        from .services.intervention_service import TRANSITIONS
        d["events"] = [event_out(e) for e in c.events]
        d["follow_ups"] = [followup_out(f) for f in c.follow_ups]
        d["allowed_transitions"] = TRANSITIONS[c.status]
        d["report"] = report_out(c.report, full=True)
    return d
