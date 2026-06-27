"""
Lightweight tests that don't require a live Gemini API call -- they verify
the agent graph wires together correctly and that the pure-Python tool
functions behave as expected. Run with: pytest tests/
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from medmate_agent.tools.schedule_tools import (
    add_medication_schedule,
    get_today_schedule,
    mark_dose_taken,
    check_missed_doses,
)
from medmate_agent.tools.inventory_tools import set_pill_count, predict_refill_date
from medmate_agent.tools.security_gate import consent_gate_callback


class FakeState(dict):
    def get(self, k, default=None):
        return super().get(k, default)


class FakeCtx:
    def __init__(self, state, user_id="u1"):
        self.state = state
        self.user_id = user_id


def test_schedule_round_trip():
    ctx = FakeCtx(FakeState({}), user_id="u1")
    result = add_medication_schedule(ctx, "Metformin", "500mg", 2, "with food")
    assert result["status"] == "scheduled"
    today = get_today_schedule(ctx)
    assert "metformin" in today["medications"]
    logged = mark_dose_taken(ctx, "metformin")
    assert logged["status"] == "logged"


def test_refill_prediction():
    ctx = FakeCtx(FakeState({}), user_id="u2")
    set_pill_count(ctx, "lisinopril", pills_remaining=10, doses_per_day=2)
    prediction = predict_refill_date(ctx, "lisinopril")
    assert prediction["days_left"] == 5
    assert prediction["should_refill_now"] is True


def test_consent_gate_blocks_without_consent():
    ctx = FakeCtx(FakeState({"role": "caregiver", "consent_given": False, "target_patient_id": "patient1"}))
    result = consent_gate_callback(ctx)
    assert result is not None  # blocked


def test_consent_gate_allows_patient_self_access():
    ctx = FakeCtx(FakeState({"role": "patient"}))
    result = consent_gate_callback(ctx)
    assert result is None  # allowed through


def test_consent_gate_allows_caregiver_with_consent():
    ctx = FakeCtx(FakeState({"role": "caregiver", "consent_given": True, "target_patient_id": "patient1"}))
    result = consent_gate_callback(ctx)
    assert result is None  # allowed through


def test_check_missed_doses():
    ctx = FakeCtx(FakeState({}), user_id="test_user_missed")
    add_medication_schedule(ctx, "Lisinopril", "10mg", 1, "in the morning")
    
    # Check missed doses - should contain lisinopril
    missed_res = check_missed_doses(ctx)
    assert missed_res["count"] == 1
    assert missed_res["missed_medications"][0]["med_id"] == "lisinopril"
    
    # Mark it taken
    mark_dose_taken(ctx, "lisinopril")
    
    # Check missed doses - should now be empty
    missed_res = check_missed_doses(ctx)
    assert missed_res["count"] == 0


def test_pii_scrubbing():
    # Test scrub_pii directly
    from medmate_agent.tools.security_gate import scrub_pii, consent_gate_callback, AUDIT_LOG
    
    text = "My email is user@example.com, call me at 123-456-7890. SSN is 999-12-3456."
    redacted = scrub_pii(text)
    assert "[REDACTED EMAIL]" in redacted
    assert "[REDACTED PHONE]" in redacted
    assert "[REDACTED SSN]" in redacted
    assert "user@example.com" not in redacted
    assert "123-456-7890" not in redacted
    assert "999-12-3456" not in redacted

    # Test consent_gate_callback scrubs user_content
    class FakePart:
        def __init__(self, text):
            self.text = text

    class FakeContent:
        def __init__(self, text):
            self.parts = [FakePart(text)]

    ctx = FakeCtx(FakeState({"role": "patient"}))
    ctx.user_content = FakeContent("Please contact me at test@test.com")
    
    consent_gate_callback(ctx)
    assert ctx.user_content.parts[0].text == "Please contact me at [REDACTED EMAIL]"
    
    # Check that it logged to audit log
    assert any(log["event"] == "pii_redacted" for log in AUDIT_LOG)
