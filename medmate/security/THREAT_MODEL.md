# MedMate Threat Model (STRIDE)

Scope: the orchestrator, its three sub-agents, the drug-interaction MCP
server, and the in-memory data stores used in this demo.

| STRIDE Category | Threat | Mitigation in this project |
|---|---|---|
| **S**poofing | A caregiver impersonates a patient to view/edit their medication data. | `consent_gate_callback` (medmate_agent/tools/security_gate.py) requires `consent_given=True` in session state for that specific patient-caregiver pair before any caregiver request reaches the orchestrator. |
| **T**ampering | A user manipulates dose logs or pill counts to hide missed doses. | Dose logs are append-only (`mark_dose_taken` only appends, never edits/deletes past entries). Production version should add cryptographic signing or a write-once store. |
| **R**epudiation | No record of who accessed a patient's data, or when. | Every gate decision (`access_granted` / `access_denied`) is written to `AUDIT_LOG` with a timestamp, acting user, role, and target patient. |
| **I**nformation Disclosure | Medication/health data leaks to an unauthorized party, or gets sent to a third-party LLM/tool unnecessarily. | Sub-agents are scoped narrowly (the interaction checker only ever receives a medication name list, never the full patient record). No medication data is logged to stdout/stderr in the tool implementations. `.env` (API keys) is gitignored and never read by application logic that touches patient data. |
| **D**enial of Service | The MCP server (subprocess) hangs or crashes, blocking the interaction checker. | `StdioConnectionParams(timeout=10.0)` bounds how long the orchestrator waits on the MCP subprocess before failing the call gracefully instead of hanging indefinitely. |
| **E**levation of Privilege | A caregiver-scoped session is able to call refill/scheduler tools for a patient who never granted consent. | The consent gate runs as a `before_agent_callback` on the **root** orchestrator, so it executes before any sub-agent (and therefore any tool) is reachable -- there is no code path that lets a sub-agent run without first passing the gate. |

## Known limitations (disclosed intentionally, not hidden)

- The interaction table and the in-memory stores (`_SCHEDULE_DB`,
  `_INVENTORY_DB`, `AUDIT_LOG`) reset on process restart. A production
  deployment should replace these with an encrypted-at-rest database
  (e.g. Firestore with CMEK) and a real append-only audit store.
- `draft_refill_message` deliberately never sends anything; a human must
  copy/approve and send it. This was a design choice to keep a human in
  the loop for anything that leaves the system, not an oversight.
- No authentication layer is implemented in this demo; `user_id` is passed
  in directly. A production deployment would sit this behind Google
  Identity Platform / OAuth and derive `user_id` from a verified token,
  never from client-supplied input.
