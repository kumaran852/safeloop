from collections import defaultdict
from datetime import timedelta
from statistics import mean
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import REGION_LABELS
from ..models import Report, utcnow
from .settings_service import get_settings

REGION_TIPS = {
    "shoulder": "Review overhead and lifting practices for the shoulder.",
    "lower_back": "Review manual handling, load weights and bending postures.",
    "upper_back": "Review reaching and carrying postures.",
    "neck": "Review head-down or overhead work postures.",
    "elbow_wrist_hand": "Review gripping, tool handles and repetitive hand movements.",
    "knee": "Review kneeling, stair and uneven-ground exposure.",
    "hip_thigh": "Review carrying loads over distance and loading-height transfers.",
    "ankle_foot": "Review footwear and walking surfaces.",
}


def detect_patterns(db: Session, ward_id: Optional[int] = None, window_days: Optional[int] = None) -> dict:
    cfg = get_settings(db)
    p = cfg["pattern"]
    window = window_days or p["window_days"]
    now = utcnow()
    since, prev_since = now - timedelta(days=window), now - timedelta(days=2 * window)
    conds = [Report.created_at >= prev_since, Report.duplicate_of_id.is_(None)]
    if ward_id:
        conds.append(Report.ward_id == ward_id)
    rows = db.scalars(select(Report).where(*conds)).all()
    cur = [r for r in rows if r.created_at >= since]
    prev = [r for r in rows if r.created_at < since]

    groups = defaultdict(list)
    for r in cur:
        groups[(r.ward.name, r.task, r.body_region)].append(r)
    clusters = []
    for (ward, task, region), rs in groups.items():
        workers = {r.worker_id for r in rs}
        if len(rs) < p["min_reports"] or len(workers) < p["min_workers"]:
            continue
        n = len(rs)
        rep, lift = sum(r.repetitive for r in rs), sum(r.frequent_lifting for r in rs)
        long_shift = sum(r.shift_hours >= 10 for r in rs)
        recs = [REGION_TIPS.get(region, "Review the task.")]
        if lift / n >= 0.5:
            recs.append("Assess lifting practices, load limits and lifting equipment (carts, hoists).")
        if rep / n >= 0.5:
            recs.append("Consider task rotation and scheduled micro-breaks.")
        if long_shift / n >= 0.3:
            recs.append("Review shift length and workload distribution.")
        recs += ["Supervisor follow-up with affected workers.", "Refer workers with persistent discomfort to qualified occupational-health personnel."]
        label = REGION_LABELS.get(region, region).lower()
        clusters.append({
            "ward": ward, "task": task, "region": region, "region_label": REGION_LABELS.get(region, region),
            "reports": n, "distinct_workers": len(workers), "avg_severity": round(mean(r.severity for r in rs), 1),
            "avg_score": round(mean(r.risk_score for r in rs), 1), "repetitive_pct": round(100 * rep / n), "lifting_pct": round(100 * lift / n),
            "long_shift_pct": round(100 * long_shift / n), "first_report": min(r.created_at for r in rs).isoformat() + "Z",
            "last_report": max(r.created_at for r in rs).isoformat() + "Z",
            "synthetic_reports": sum(r.is_synthetic for r in rs), "observed_reports": sum(not r.is_synthetic for r in rs),
            "window_days": window,
            "why_flagged": f"{n} reports from {len(workers)} workers about {label} discomfort during {task} in {ward} within {window} days (thresholds: at least {p['min_reports']} reports from at least {p['min_workers']} workers).",
            "recommendations": recs,
            "caveat": "Pattern in recorded reports only. It does not establish a cause and is not a medical assessment.",
        })
    clusters.sort(key=lambda c: (-c["reports"], -c["avg_score"]))

    cw, pw = defaultdict(list), defaultdict(list)
    for r in cur:
        cw[r.ward.name].append(r)
    for r in prev:
        pw[r.ward.name].append(r)
    trends = []
    for w in sorted(set(cw) | set(pw)):
        c, pr = cw.get(w, []), pw.get(w, [])
        trends.append({"ward": w, "current_reports": len(c), "previous_reports": len(pr), "change": len(c) - len(pr),
                       "avg_score": round(mean(r.risk_score for r in c), 1) if c else None,
                       "high_or_critical": sum(r.risk_level in ("High", "Critical") for r in c)})
    return {"window_days": window, "since": since.isoformat() + "Z", "thresholds": p, "sample_size": len(cur), "previous_window_size": len(prev),
            "synthetic_share": round(100 * sum(r.is_synthetic for r in cur) / len(cur), 1) if cur else None,
            "clusters": clusters, "ward_trends": trends}
