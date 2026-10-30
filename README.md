# SAFELOOP — From Worker Signals to Verified Safety Action

Occupational-safety decision-support prototype for municipal sanitation workers. Loop:
**worker report → validation → explainable risk score → alert → case (owner, action, due date) → follow-up → verified or administrative closure → analytics.**

> Early-stage hackathon prototype. Not a medical, diagnostic or injury-prediction system. No authentication: **not safe for real municipal records**. All seeded data is synthetic and tagged "Demo".

## Run on Windows 11
Prerequisites: Python 3.11+ (tick "Add to PATH"), Node.js 18+.

One-time setup and start (PowerShell, project root; if scripts are blocked run `Set-ExecutionPolicy -Scope Process Bypass` first):
```powershell
.\scripts\setup_windows.ps1
.\scripts\start_windows.ps1
```
Manual (two terminals):
```powershell
# Terminal 1
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Terminal 2
cd frontend
npm install
npm run dev
```
- Dashboard: http://localhost:5173  · API docs (Swagger): http://localhost:8000/docs
- Stop: Ctrl+C in each terminal (or close the two windows).
- Port conflicts: `netstat -ano | findstr :8000` then `taskkill /PID <pid> /F`; or run uvicorn with `--port 8001` and set `frontend/.env` `VITE_API_BASE=http://localhost:8001/api` (add that origin's frontend to `CORS_ORIGINS` if not on 5173).
- Database: `data/safeloop.db` (SQLite, created and seeded on first start). Reset: Settings → Reset database, or stop the backend and delete the file.

## Tests
```powershell
cd backend ; .\.venv\Scripts\Activate.ps1 ; python -m pytest -q     # isolated temp DB
cd frontend ; npm test ; npm run build ; npm run typecheck
```

## Demo script
1. Dashboard shows seeded data. 2. Workers → open `SW-0009` (Ward 03) history. 3. New report: ID `SW-0009`, shoulder, severity 9, repetitive + lifting, 10 h. 4. Result shows score and per-factor points; alert and case are created. 5. Reports lists the saved record. 6. Case → Assign owner + due date → move to In Progress → add a note. 7. Pending Verification → record follow-up "No change" (case auto-reopens) or "Improved" then Resolve as verified improvement. Administrative closure is recorded separately and never counted as verified. 8. Dashboard/Analytics update. 9. Analytics → Export CSV. Ward intelligence flags Ward 03 shoulder and Ward 05 lower-back clusters (synthetic).

## Methodology (configurable, unvalidated)
Score 0–100 = discomfort(1–10)×4 + repetitive 10 + frequent lifting 10 + shift ≥10 h 10 (≥8 h 5) + earlier reports same worker/region in window 5 each (max 15) + ≥2 reports from other workers same ward/task/region 10 + earlier unverified case same worker/region 5. Levels: Low <30, Moderate ≥30, High ≥50, Critical ≥70 (editable in Settings; apply to new reports). Discomfort ≥8 is floored at High. Not a probability of injury; no clinical validation; no accuracy measured (no labelled data exists, so precision/recall are not reported).
Patterns: ≥3 reports from ≥2 workers, same ward+task+region, within 30 days (configurable, minimum 2), duplicates excluded; shows sample size and synthetic share; associations only.
Metrics: response times use recorded timestamps (n shown, "unavailable" when none); completion = resolved ÷ all cases; verified improvement = verified ÷ resolved; follow-up documented = cases with ≥1 follow-up ÷ cases where work started; repeat-report rate = interventions started ≥30 days ago with a later same-worker/region report within 30 days ÷ those interventions.
Data quality: duplicate detection (same worker + region, ±1 severity, 24 h → 409 until confirmed, then saved flagged), unassigned high-priority, overdue, missing follow-up, admin closures, ward mismatch. Nothing is silently deleted.

## Architecture
`backend/app`: `models.py`, `schemas.py` (validation), `services/` (risk_engine, intervention_service with status state machine, pattern_detection, metrics_service), `api/` (workers, wards, reports, alerts, cases, analytics+CSV, admin/settings), `seed.py` (idempotent, `random.Random(42)`). `frontend/src`: pages, `services/api.ts`, `i18n` (English/Tamil), `components/ui`.
Main endpoints (prefix `/api`): `health`, `meta`, `workers`, `wards`, `reports`, `alerts` (+`/{id}/acknowledge`), `cases` (+`assign`, `status`, `notes`, `follow-ups`), `analytics/{dashboard,summary,patterns,data-quality,export/reports.csv,export/cases.csv}`, `settings`, `admin/reset`.
Case transitions: Open→Assigned→In Progress→Pending Verification→Resolved; Pending Verification→Reopened/In Progress; Resolved→Reopened; Reopened→Assigned/In Progress.

## Limitations
No authentication/authorisation, encryption, or audit-grade logging; operators type their own "actor" (default `operator`). Tamil covers the worker form and navigation only; operator screens are English. No frontend component tests (util/i18n tests only). Production hardening needed: auth + roles, HTTPS, Postgres, backups, privacy review, clinical/ergonomic review of rules.

## Troubleshooting
`python` not found → reinstall Python with PATH ticked. `npm install` fails → check Node ≥18 and network/proxy. `Activate.ps1` blocked → `Set-ExecutionPolicy -Scope Process Bypass`. "Cannot reach the SAFELOOP API" → backend not running on 8000. `ModuleNotFoundError` → activate the venv and rerun `pip install -r requirements.txt`.
