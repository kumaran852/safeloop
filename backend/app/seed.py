import random
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import BODY_REGIONS, SHIFT_TYPES
from .models import Alert, Case, Setting, Ward, Worker, utcnow
from .services import intervention_service as svc
from .services.settings_service import DEFAULTS

WARDS = [("W01", "Ward 01"), ("W02", "Ward 02"), ("W03", "Ward 03"), ("W04", "Ward 04"), ("W05", "Ward 05"), ("W06", "Ward 06")]
TASK_BY_WARD = {"W01": "Street Sweeping", "W02": "Waste Segregation", "W03": "Waste Collection", "W04": "Drain Cleaning", "W05": "Loading", "W06": "Waste Collection"}
OWNERS = ["Ward Supervisor", "Zonal Safety Officer", "Occupational Health Coordinator"]


def seed_reference(db: Session) -> None:
    if not db.scalar(select(func.count(Ward.id))):
        db.add_all([Ward(code=c, name=n) for c, n in WARDS])
    for k, v in DEFAULTS.items():
        if db.get(Setting, k) is None:
            db.add(Setting(key=k, value=v))
    db.flush()


def seed_demo(db: Session) -> bool:
    """Synthetic data only. Idempotent: skipped once the 'demo_seeded' marker exists."""
    seed_reference(db)
    if db.get(Setting, "demo_seeded") is not None or db.scalar(select(func.count(Worker.id))):
        return False
    rng, now = random.Random(42), utcnow()
    wards = {w.code: w for w in db.scalars(select(Ward))}
    by_ward, n = {}, 0
    for code, w in wards.items():
        by_ward[code] = []
        for _ in range(4):
            n += 1
            wk = Worker(pseudo_id=f"SW-{n:04d}", ward_id=w.id, task=TASK_BY_WARD.get(code, "Waste Collection"), shift_type=rng.choice(SHIFT_TYPES),
                        is_synthetic=True, created_at=now - timedelta(days=90))
            db.add(wk)
            by_ward[code].append(wk)
    db.flush()
    specs = []

    def add(days, wk, region, sev, hours, rep, lift, desc=None):
        specs.append((days, wk, region, sev, hours, rep, lift, desc))

    for k in range(7):
        add(rng.uniform(1, 26), by_ward["W03"][k % 4], "shoulder", rng.randint(5, 8), rng.choice([8, 9, 10, 11]), True, True, "Shoulder pain after lifting full bins (synthetic).")
    for k in range(5):
        add(rng.uniform(1, 22), by_ward["W05"][k % 3], "lower_back", rng.randint(6, 9), rng.choice([9, 10, 11]), True, True, "Lower back strain while loading (synthetic).")
    for _ in range(58):
        code = rng.choice(list(wards))
        sev = rng.choices(range(1, 11), weights=[3, 4, 5, 5, 4, 3, 2, 1, 1, 1])[0]
        add(rng.uniform(0.5, 55), rng.choice(by_ward[code]), rng.choice(BODY_REGIONS), sev, rng.choice([6, 7, 8, 8, 9, 10]), rng.random() < 0.45, rng.random() < 0.4)
    specs.sort(key=lambda s: -s[0])
    for days, wk, region, sev, hours, rep, lift, desc in specs:
        data = {"worker_id": wk.id, "ward_id": wk.ward_id, "task": wk.task, "body_region": region, "severity": sev, "shift_hours": float(hours),
                "shift_type": wk.shift_type, "repetitive": rep, "frequent_lifting": lift, "description": desc}
        svc.create_report(db, data, now=now - timedelta(days=days), synthetic=True, allow_duplicate=True)
    db.flush()

    for i, c in enumerate(db.scalars(select(Case).order_by(Case.created_at)).all()):
        age_days = (now - c.created_at).days
        scen = i % 2 if age_days < 2 else i % 7
        t, own, h = c.created_at, rng.choice(OWNERS), [0]

        def at(add_h):
            h[0] += add_h
            return min(t + timedelta(hours=h[0]), now)

        if scen == 0:
            continue
        if c.alert:
            c.alert.status, c.alert.acknowledged_at, c.alert.acknowledged_by = "Acknowledged", at(rng.randint(1, 10)), "demo-operator"
        if scen == 1:
            continue
        svc.assign_case(db, c, own, None, None, None, "demo-operator", at(rng.randint(1, 8)))
        if scen == 2:
            continue
        svc.change_status(db, c, "In Progress", own, "Work started (synthetic).", now=at(rng.randint(4, 30)))
        if scen == 3:
            continue
        svc.change_status(db, c, "Pending Verification", own, "Intervention completed; awaiting verification (synthetic).", now=at(rng.randint(24, 72)))
        if scen == 4:
            svc.add_follow_up(db, c, "Improved", "Worker reports reduced discomfort after task rotation and cart use (synthetic).", "Supervisor check-in", own, now=at(48))
            svc.change_status(db, c, "Resolved", own, "Verified at follow-up.", "verified_improvement", now=at(1))
        elif scen == 5:
            svc.add_follow_up(db, c, "No change", "Discomfort persists; lifting aid not yet available (synthetic).", None, own, now=at(48))
        else:
            svc.change_status(db, c, "Resolved", own, "Closed by supervisor without a follow-up observation (synthetic).", "administrative_closure", now=at(24))
    db.add(Setting(key="demo_seeded", value={"at": now.isoformat()}))
    db.flush()
    return True
