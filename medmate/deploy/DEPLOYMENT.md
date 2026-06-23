# Deploying MedMate to Agent Runtime

The judging rubric does not require a live public endpoint, but it does
require *documentation to reproduce the deployment* if you choose to deploy.
These are the steps used for this project, run from the repo root.

## Prerequisites
- A Google Cloud project with billing enabled.
- `agents-cli` installed: `uvx google-agents-cli setup`
- Authenticated: `gcloud auth application-default login`
- A Gemini API key in `.env` (copy `.env.example` -> `.env`, never commit it).

## 1. Local smoke test first

```bash
pip install -r requirements.txt
adk run medmate_agent
```

This starts an interactive session against `root_agent` in
`medmate_agent/agent.py`. Try: "I take 500mg metformin twice a day with food"
then "is it safe with warfarin and aspirin too" to exercise the scheduler
and interaction-checker sub-agents end to end.

## 2. Deploy to Agent Runtime

```bash
agents-cli deploy agent-runtime \
  --agent-path medmate_agent \
  --project YOUR_GCP_PROJECT_ID \
  --region us-central1 \
  --display-name "medmate-concierge"
```

This packages `medmate_agent/` (including its MCP server dependency
declared in `requirements.txt`) and deploys it to Agent Runtime. On
success the CLI prints a resource name and the agent is automatically
registered in the Gemini Enterprise Agent Registry.

## 3. Verify registration

```bash
agents-cli publish gemini-enterprise --list
```

Confirms `medmate-concierge` is listed as active and discoverable.

## 4. (Optional) Deploy a frontend

A minimal Cloud Run frontend can call the deployed Agent Runtime endpoint
directly. See the course's "Vibecode and Deploy a Frontend for an ADK
agent" codelab for the pattern this project follows; the frontend itself
is out of scope for this repo to keep judging time focused on the agent
architecture.

## Rollback / teardown

```bash
agents-cli deploy agent-runtime --delete --display-name "medmate-concierge"
```
