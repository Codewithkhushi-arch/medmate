"""
Refill/inventory tools: pill-count tracking and refill date prediction.
"""
from datetime import date, timedelta
from typing import Optional
from google.adk.tools import ToolContext

# Design Choice Rationale: This in-memory database provides a zero-infrastructure 
# developer experience. In a production system, it would be replaced by 
# a secure, authenticated database (e.g. Firestore with CMEK) without 
# altering the tool interface signatures.
_INVENTORY_DB: dict[str, dict[str, dict]] = {}


def set_pill_count(tool_context: ToolContext, med_id: str, pills_remaining: int, doses_per_day: int) -> dict:
    """Records how many pills are left for a medication and the daily dose rate.

    Args:
        tool_context: ADK tool context auto-injecting session details.
        med_id: The medication identifier (matches the scheduler's med_id).
        pills_remaining: Number of pills currently left.
        doses_per_day: How many pills are consumed per day.

    Returns:
        A dict confirming the stored inventory state.
    """
    user_id = tool_context.state.get("target_patient_id", tool_context.user_id)
    _INVENTORY_DB.setdefault(user_id, {})[med_id] = {
        "pills_remaining": pills_remaining,
        "doses_per_day": max(doses_per_day, 1),
        "last_updated": date.today().isoformat(),
    }
    return {"status": "saved", "med_id": med_id, **_INVENTORY_DB[user_id][med_id]}


def predict_refill_date(tool_context: ToolContext, med_id: str) -> dict:
    """Predicts the date a medication will run out, based on current pill count.

    Args:
        tool_context: ADK tool context auto-injecting session details.
        med_id: The medication identifier to check.

    Returns:
        A dict with the predicted run-out date, or an error if no inventory is on file.
    """
    user_id = tool_context.state.get("target_patient_id", tool_context.user_id)
    record = _INVENTORY_DB.get(user_id, {}).get(med_id)
    if not record:
        return {"status": "error", "message": f"No inventory on file for '{med_id}'."}
    days_left = record["pills_remaining"] // record["doses_per_day"]
    run_out_date = date.today() + timedelta(days=days_left)
    return {
        "status": "ok",
        "med_id": med_id,
        "days_left": days_left,
        "predicted_run_out_date": run_out_date.isoformat(),
        "should_refill_now": days_left <= 5,
    }


def draft_refill_message(tool_context: ToolContext, med_id: str, pharmacy_name: Optional[str] = "your pharmacy") -> dict:
    """Drafts a refill request message for a caregiver or patient to review and send.

    This only drafts text; it never sends anything automatically, by design,
    so a human always stays in the loop for medication-related actions.

    Args:
        tool_context: ADK tool context auto-injecting session details.
        med_id: The medication identifier needing a refill.
        pharmacy_name: Name of the pharmacy to address the message to.

    Returns:
        A dict containing the drafted message for human review.
    """
    user_id = tool_context.state.get("target_patient_id", tool_context.user_id)
    record = _INVENTORY_DB.get(user_id, {}).get(med_id)
    if not record:
        return {"status": "error", "message": f"No inventory on file for '{med_id}'."}
    message = (
        f"Hi {pharmacy_name}, could you please process a refill for {med_id.replace('_', ' ')}? "
        f"Current supply is estimated to run out around "
        f"{predict_refill_date(tool_context, med_id)['predicted_run_out_date']}. Thank you!"
    )
    return {"status": "drafted", "requires_human_approval": True, "message": message}
