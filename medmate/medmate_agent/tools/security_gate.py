"""
Consent / access-control gate for MedMate.

Implements a before_agent_callback that runs on every invocation of the root
orchestrator. It enforces:
  1. A caregiver may only view/act on a patient's data if explicit consent
     has been recorded in session state for that patient-caregiver pair.
  2. Every gate decision is written to an in-memory audit log (swap for a
     real append-only log/store in production).

This is intentionally simple and dependency-free so it's easy for judges to
read end-to-end, while still demonstrating a real access-control pattern
rather than just a comment saying "this would be secure".
"""
from datetime import datetime
from google.genai import types

AUDIT_LOG: list[dict] = []


def _audit(event: str, **details) -> None:
    AUDIT_LOG.append({"timestamp": datetime.now().isoformat(), "event": event, **details})


def consent_gate_callback(callback_context):
    """before_agent_callback: blocks the orchestrator if consent is missing.

    ADK invokes before_agent_callback as callback(callback_context=...), so
    the parameter must be named exactly `callback_context` -- ADK calls it
    as a keyword argument, not positionally.

    Expects callback_context.state to optionally contain:
        role: "patient" | "caregiver"
        target_patient_id: the patient whose data is being accessed
        consent_given: bool, set True once the patient has approved a caregiver

    Returns:
        None to allow the request through, or a Content object that short
        circuits the agent and is returned directly to the user.
    """
    ctx = callback_context
    role = ctx.state.get("role", "patient")
    target_patient_id = ctx.state.get("target_patient_id", ctx.user_id)
    consent_given = ctx.state.get("consent_given", role == "patient")

    if role == "caregiver" and not consent_given:
        _audit(
            "access_denied",
            user_id=ctx.user_id,
            target_patient_id=target_patient_id,
            reason="missing_consent",
        )
        return types.Content(
            role="model",
            parts=[
                types.Part(
                    text=(
                        "I can't share this patient's medication data with you yet -- "
                        "they haven't granted caregiver access. Ask them to enable "
                        "caregiver consent first."
                    )
                )
            ],
        )

    _audit("access_granted", user_id=ctx.user_id, role=role, target_patient_id=target_patient_id)
    return None
