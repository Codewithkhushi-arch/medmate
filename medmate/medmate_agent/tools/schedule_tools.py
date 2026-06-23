"""
Scheduler tools: in-memory medication schedule for the demo.
Swap the _SCHEDULE_DB dict for a real database (e.g. Firestore) for production use.
"""
from datetime import datetime, date
from typing import Optional
from google.adk.tools import ToolContext

# Design Choice Rationale: These in-memory stores are used to provide a 
# zero-infrastructure developer experience out-of-the-box. In production, 
# this would be replaced with a secure database service (e.g. Firestore 
# with customer-managed encryption keys) without changing the tool function signatures.
_SCHEDULE_DB: dict[str, dict[str, dict]] = {}
_DOSE_LOG: dict[str, list[dict]] = {}


def add_medication_schedule(
    tool_context: ToolContext,
    medication_name: str,
    dosage: str,
    times_per_day: int,
    notes: Optional[str] = None,
) -> dict:
    """Adds a medication to a user's schedule.

    Args:
        tool_context: ADK tool context auto-injecting session details.
        medication_name: Name of the medication, e.g. "Metformin".
        dosage: Dosage string, e.g. "500mg".
        times_per_day: How many times per day this medication is taken.
        notes: Optional free-text notes, e.g. "take with food".

    Returns:
        A dict confirming the medication that was scheduled.
    """
    user_id = tool_context.state.get("target_patient_id", tool_context.user_id)
    med_id = f"{medication_name.lower().replace(' ', '_')}"
    _SCHEDULE_DB.setdefault(user_id, {})[med_id] = {
        "medication_name": medication_name,
        "dosage": dosage,
        "times_per_day": times_per_day,
        "notes": notes or "",
        "added_on": date.today().isoformat(),
    }
    return {"status": "scheduled", "med_id": med_id, **_SCHEDULE_DB[user_id][med_id]}


def get_today_schedule(tool_context: ToolContext) -> dict:
    """Returns every medication scheduled for the given user.

    Args:
        tool_context: ADK tool context auto-injecting session details.

    Returns:
        A dict mapping med_id to medication details.
    """
    user_id = tool_context.state.get("target_patient_id", tool_context.user_id)
    return {"user_id": user_id, "medications": _SCHEDULE_DB.get(user_id, {})}


def mark_dose_taken(tool_context: ToolContext, med_id: str) -> dict:
    """Logs that a dose was taken right now, for adherence tracking.

    Args:
        tool_context: ADK tool context auto-injecting session details.
        med_id: The medication identifier returned by add_medication_schedule.

    Returns:
        A dict confirming the logged dose with a timestamp.
    """
    user_id = tool_context.state.get("target_patient_id", tool_context.user_id)
    if user_id not in _SCHEDULE_DB or med_id not in _SCHEDULE_DB[user_id]:
        return {"status": "error", "message": f"No such medication '{med_id}' for this user."}
    entry = {"med_id": med_id, "taken_at": datetime.now().isoformat()}
    _DOSE_LOG.setdefault(user_id, []).append(entry)
    return {"status": "logged", **entry}


def check_missed_doses(tool_context: ToolContext) -> dict:
    """Checks which scheduled medications have not been logged as taken today.

    Args:
        tool_context: ADK tool context auto-injecting session details.

    Returns:
        A dict mapping the user_id to a list of missed medications and their details.
    """
    user_id = tool_context.state.get("target_patient_id", tool_context.user_id)
    today_str = date.today().isoformat()
    # Retrieve all unique med_ids logged as taken today
    logged_today = {
        entry["med_id"]
        for entry in _DOSE_LOG.get(user_id, [])
        if entry.get("taken_at", "").startswith(today_str)
    }

    schedule = get_today_schedule(tool_context)
    medications = schedule.get("medications", {})

    missed = []
    for med_id, details in medications.items():
        if med_id not in logged_today:
            missed.append({
                "med_id": med_id,
                **details
            })

    return {
        "user_id": user_id,
        "missed_medications": missed,
        "count": len(missed),
    }

