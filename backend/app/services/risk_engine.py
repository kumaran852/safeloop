"""Deterministic, explainable operational-priority score (0-100). NOT a clinical or injury-probability model."""
from dataclasses import dataclass

LEVELS = ["Low", "Moderate", "High", "Critical"]
DEFAULT_THRESHOLDS = {"moderate": 30, "high": 50, "critical": 70}
WEIGHTS = {
    "severity_per_point": 4,      # max 40
    "repetitive": 10,
    "frequent_lifting": 10,
    "shift_10h": 10,
    "shift_8h": 5,
    "prior_report_each": 5,       # same worker + body region in window
    "prior_report_max": 15,
    "peer_pattern": 10,           # >= 2 reports from other workers, same ward+task+region
    "unverified_case": 5,         # earlier case for same worker/region without verified improvement
}
SEVERITY_FLOOR = 8  # severity >= 8 is always at least "High"


@dataclass(frozen=True)
class RiskInput:
    severity: int
    shift_hours: float
    repetitive: bool = False
    frequent_lifting: bool = False
    prior_worker_reports: int = 0
    peer_pattern_reports: int = 0
    prior_unverified_cases: int = 0


def level_for(score: int, thresholds: dict | None = None) -> str:
    th = thresholds or DEFAULT_THRESHOLDS
    if score >= th["critical"]:
        return "Critical"
    if score >= th["high"]:
        return "High"
    if score >= th["moderate"]:
        return "Moderate"
    return "Low"


def score_report(inp: RiskInput, thresholds: dict | None = None) -> dict:
    w = WEIGHTS
    c = []

    def add(factor, points, detail):
        if points > 0:
            c.append({"factor": factor, "points": points, "detail": detail})

    add("severity", inp.severity * w["severity_per_point"], f"Reported discomfort {inp.severity}/10")
    if inp.repetitive:
        add("repetitive", w["repetitive"], "Repetitive movements reported")
    if inp.frequent_lifting:
        add("frequent_lifting", w["frequent_lifting"], "Frequent lifting reported")
    if inp.shift_hours >= 10:
        add("shift_length", w["shift_10h"], f"Long shift ({inp.shift_hours:g} h, 10 h or more)")
    elif inp.shift_hours >= 8:
        add("shift_length", w["shift_8h"], f"Extended shift ({inp.shift_hours:g} h, 8 h or more)")
    if inp.prior_worker_reports > 0:
        pts = min(inp.prior_worker_reports * w["prior_report_each"], w["prior_report_max"])
        add("prior_reports", pts, f"{inp.prior_worker_reports} earlier report(s) by this worker for the same body region")
    if inp.peer_pattern_reports >= 2:
        add("peer_pattern", w["peer_pattern"], f"{inp.peer_pattern_reports} reports from other workers for the same ward, task and body region")
    if inp.prior_unverified_cases > 0:
        add("unverified_case", w["unverified_case"], "An earlier case for this worker and body region has no verified improvement")

    score = max(0, min(100, sum(x["points"] for x in c)))
    level = level_for(score, thresholds)
    notes = []
    if inp.severity >= SEVERITY_FLOOR and LEVELS.index(level) < LEVELS.index("High"):
        level = "High"
        notes.append(f"Severity floor: discomfort of {SEVERITY_FLOOR}/10 or more is always at least High priority for review.")
    return {"score": score, "level": level, "contributions": c, "notes": notes, "max_score": 100}


def reason_text(result: dict) -> str:
    parts = "; ".join(x["detail"] for x in result["contributions"])
    extra = " " + " ".join(result["notes"]) if result["notes"] else ""
    return f"{result['level']} operational priority (score {result['score']}/100): {parts}.{extra}"
