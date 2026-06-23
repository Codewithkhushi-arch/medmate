---
name: medication-parser
description: Parses free-text medication descriptions (e.g. "500mg metformin twice daily with food") into structured fields the scheduler_agent can use directly: medication_name, dosage, times_per_day, notes.
---

# Medication Parser Skill

Use this skill whenever a user describes a medication in natural language
instead of giving you structured fields directly.

## Instructions

1. Read the user's free-text description.
2. Extract:
   - `medication_name`: the drug name, normalized to title case.
   - `dosage`: the strength + unit, e.g. "500mg". If absent, ask the user.
   - `times_per_day`: an integer. Map phrases like "twice daily" -> 2,
     "once a day" -> 1, "every 8 hours" -> 3, "as needed" -> ask the user
     to confirm a typical daily count rather than guessing for PRN meds.
   - `notes`: anything else relevant (e.g. "with food", "before bed").
3. If any required field is ambiguous or missing, ask one short clarifying
   question rather than guessing -- medication data should never be invented.
4. Once all fields are confirmed, call `add_medication_schedule` with the
   structured values.

## Example

Input: "I take 500mg of metformin twice a day with food"
Output:
```json
{
  "medication_name": "Metformin",
  "dosage": "500mg",
  "times_per_day": 2,
  "notes": "with food"
}
```
