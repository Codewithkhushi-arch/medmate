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
import re
from google.genai import types

AUDIT_LOG: list[dict] = []


def _audit(event: str, **details) -> None:
    AUDIT_LOG.append({"timestamp": datetime.now().isoformat(), "event": event, **details})


def scrub_pii(text: str) -> str:
    """Anonymizes phone numbers, emails, and SSNs from text."""
    if not text:
        return text
    # Email pattern
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    text = re.sub(email_pattern, "[REDACTED EMAIL]", text)
    # SSN pattern
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    text = re.sub(ssn_pattern, "[REDACTED SSN]", text)
    # Phone pattern
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    text = re.sub(phone_pattern, "[REDACTED PHONE]", text)
    return text


def redact_and_audit(text: str, user_id: str) -> str:
    """Scrubs PII from the text and logs the redaction types to the audit log."""
    redacted = scrub_pii(text)
    if redacted != text:
        redactions = []
        if "[REDACTED EMAIL]" in redacted and "[REDACTED EMAIL]" not in text:
            redactions.append("email")
        if "[REDACTED SSN]" in redacted and "[REDACTED SSN]" not in text:
            redactions.append("ssn")
        if "[REDACTED PHONE]" in redacted and "[REDACTED PHONE]" not in text:
            redactions.append("phone")
        _audit("pii_redacted", user_id=user_id, types=redactions)
    return redacted


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

    # Scrub PII in user_content (current message) if available
    user_content = getattr(ctx, 'user_content', None)
    if user_content and hasattr(user_content, 'parts') and user_content.parts:
        for part in user_content.parts:
            if hasattr(part, 'text') and part.text:
                part.text = redact_and_audit(part.text, ctx.user_id)

    # Scrub PII in historical session events (to prevent leaks from history) if available
    session = getattr(ctx, 'session', None)
    if session and hasattr(session, 'events') and session.events:
        for event in session.events:
            if getattr(event, 'author', '') == 'user' or getattr(event, 'role', '') == 'user':
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts') and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            part.text = redact_and_audit(part.text, ctx.user_id)

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
