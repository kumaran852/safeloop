from app.services.risk_engine import RiskInput, level_for, score_report


def test_low_score_and_level():
    r = score_report(RiskInput(severity=2, shift_hours=6))
    assert r["score"] == 8 and r["level"] == "Low"


def test_contributions_sum_to_score():
    r = score_report(RiskInput(9, 10, True, True, prior_worker_reports=2))
    assert r["score"] == sum(c["points"] for c in r["contributions"]) == 36 + 10 + 10 + 10 + 10
    assert r["level"] == "Critical"


def test_severity_floor_forces_high():
    r = score_report(RiskInput(severity=8, shift_hours=6))
    assert r["score"] == 32 and r["level"] == "High" and r["notes"]


def test_score_is_capped_and_thresholds_configurable():
    r = score_report(RiskInput(10, 12, True, True, 9, 5, 2))
    assert r["score"] == 100
    assert level_for(40, {"moderate": 20, "high": 35, "critical": 60}) == "High"


def test_peer_pattern_needs_two_reports():
    assert not any(c["factor"] == "peer_pattern" for c in score_report(RiskInput(3, 6, peer_pattern_reports=1))["contributions"])
    assert any(c["factor"] == "peer_pattern" for c in score_report(RiskInput(3, 6, peer_pattern_reports=2))["contributions"])
