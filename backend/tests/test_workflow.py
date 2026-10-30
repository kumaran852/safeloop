def mk_worker(c, ward=1):
    r = c.post("/api/workers", json={"ward_id": ward, "task": "Waste Collection"})
    assert r.status_code == 201
    return r.json()


def report(c, w, **kw):
    body = {"worker_id": w["id"], "ward_id": w["ward_id"], "task": "Waste Collection", "body_region": "shoulder", "severity": 9,
            "shift_hours": 10, "shift_type": "Morning", "repetitive": True, "frequent_lifting": True}
    body.update(kw)
    return c.post("/api/reports", json=body)


def test_health_and_validation(client):
    assert client.get("/api/health").json()["status"] == "ok"
    w = mk_worker(client)
    assert report(client, w, severity=11).status_code == 422
    assert report(client, w, shift_hours=0).status_code == 422
    assert report(client, w, task="Unknown task").status_code == 422


def test_report_alert_case_linkage_and_duplicate(client):
    w = mk_worker(client)
    r = report(client, w)
    assert r.status_code == 201
    d = r.json()
    assert d["risk"]["level"] in ("High", "Critical") and d["risk"]["contributions"]
    assert d["alert"]["report_id"] == d["report"]["id"] and d["case"]["status"] == "Open"
    assert client.get(f"/api/reports/{d['report']['id']}").json()["case_id"] == d["case"]["id"]
    dup = report(client, w)
    assert dup.status_code == 409 and dup.json()["detail"]["code"] == "possible_duplicate"
    assert report(client, w, allow_duplicate=True).json()["alert"] is None  # flagged, original already has a case


def test_case_lifecycle_followup_reopen_and_verification_rules(client):
    w = mk_worker(client)
    cid = report(client, w).json()["case"]["id"]
    s = lambda to, **kw: client.post(f"/api/cases/{cid}/status", json={"to_status": to, **kw})
    assert s("In Progress").status_code == 409          # invalid transition
    assert s("Assigned").status_code == 409             # no owner
    a = client.post(f"/api/cases/{cid}/assign", json={"owner": "Ward Supervisor", "due_date": "2099-01-01"})
    assert a.json()["status"] == "Assigned"
    assert s("In Progress").status_code == 200 and s("Pending Verification").status_code == 200
    assert s("Resolved", resolution_type="verified_improvement").status_code == 409   # no follow-up yet
    fu = client.post(f"/api/cases/{cid}/follow-ups", json={"outcome": "No change", "notes": "Still painful"})
    assert fu.status_code == 201 and fu.json()["status"] == "Reopened"
    assert client.post(f"/api/cases/{cid}/status", json={"to_status": "Resolved", "resolution_type": "administrative_closure"}).status_code == 409
    assert s("In Progress").status_code == 200 and s("Pending Verification").status_code == 200
    client.post(f"/api/cases/{cid}/follow-ups", json={"outcome": "Improved", "notes": "Much better"})
    assert s("Resolved", resolution_type="verified_improvement").json()["resolution_type"] == "verified_improvement"
    events = client.get(f"/api/cases/{cid}").json()["events"]
    assert [e["event_type"] for e in events][0] == "created" and any(e["to_status"] == "Reopened" for e in events)


def test_analytics_dashboard_and_csv(client):
    w = mk_worker(client)
    cid = report(client, w).json()["case"]["id"]
    client.post(f"/api/cases/{cid}/assign", json={"owner": "Ward Supervisor"})
    sm = client.get("/api/analytics/summary").json()
    assert sm["sample"]["reports"] == 1 and sm["cases"]["total"] == 1
    assert sm["response_times"]["assignment"]["n"] == 1 and sm["response_times"]["intervention"]["available"] is False
    assert sm["repeat_reports"]["pct"] is None
    db = client.get("/api/analytics/dashboard").json()
    assert db["totals"]["reports"] == 1 and db["totals"]["open_cases"] == 1
    csv = client.get("/api/analytics/export/reports.csv")
    assert csv.headers["content-type"].startswith("text/csv") and csv.text.count("\n") == 2
    assert "SL-0001" in client.get("/api/analytics/export/cases.csv").text


def test_reset_requires_confirmation_and_seed_idempotent(client):
    assert client.post("/api/admin/reset", json={"confirm": "no"}).status_code == 400
    assert client.post("/api/admin/reset", json={"confirm": "RESET", "demo": True}).status_code == 200
    n = client.get("/api/workers?page_size=200").json()["total"]
    assert n == 24
    from app.database import SessionLocal
    from app.seed import seed_demo
    with SessionLocal() as db:
        assert seed_demo(db) is False
    assert client.get("/api/workers?page_size=200").json()["total"] == n
    assert client.get("/api/analytics/patterns").json()["clusters"]
