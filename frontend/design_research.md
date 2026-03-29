# ClearClaim Design Research

Date: 2026-03-29
Scope: Streamlit (`../ClearClaim/app.py`), LangGraph (`../ClearClaim/graph.py`), React UI (`src/App.jsx`), FastAPI wrapper (`backend/main.py`).

## Current Architecture
- Legacy UI: Streamlit calls `build_graph().invoke(...)` in-process.
- New UI: React app calls FastAPI Option A endpoints.
- Backend: FastAPI invokes ClearClaim graph and returns stable run envelopes.
- Persistence: SQLite-backed run/session history (`CLEARCLAIM_DB_PATH`).

## Canonical Behavior Mapping

### Patient Flow
- Inputs: `procedure -> cpt_code`, `zip_code`, `insurance_type`, `provider_type`, `urgency`, `deductible_status`.
- Action: `Estimate Cost`.
- Rendered sections:
  - Estimated total / insurance pays / out-of-pocket (midpoint headline, low-high range)
  - Split donut
  - Prior-auth banner
  - Explanation
  - Savings tips
- State rule: patient result is transient and replaced on next submit.

### Hospital Flow
- Inputs: `cpt_code`, `icd_code`, `payer`, `clinical_note`.
- Action: `Predict Denial Risk`.
- Rendered sections:
  - Denial risk + status
  - NCCI validity + flags
  - Risk factors
  - Clinical note analysis
  - Fix list
- Re-eval: select fix -> apply -> re-run -> show risk delta.
- State rule: hospital result persists across tab switches in React state.

## API Contract (Option A)
- `POST /api/v1/patient/estimate`
- `POST /api/v1/hospital/denial`
- `POST /api/v1/hospital/{run_id}/reevaluate`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/sessions/{session_id}`

Envelope fields:
- `run_id`, `session_id`, `mode`, `status`, `workflow_version`
- `input`, `output`, `warnings`, `messages`, `created_at`, `completed_at`

Mode payload keys preserved:
- Patient: `benefits`, `cms_rates`, `fee_schedule`, `cost_estimate`, `messages`
- Hospital: `ncci_result`, `denial_score`, `fix_list`, `messages`

## Environment and Runtime Notes
- Backend auto-loads env vars from:
  - `../ClearClaim/.env`
  - `backend/.env`
- This is used for `ANTHROPIC_API_KEY` consistency between Streamlit and FastAPI runs.
- Frontend transport:
  - `VITE_API_MODE=live` (FastAPI)
  - `VITE_API_MODE=mock` (contract-shaped mock responses)

## Testing Status
- Frontend:
  - `npm run lint` passes
  - `npm run build` passes
- Backend:
  - `python -m py_compile backend/main.py backend/tests/test_api_contract.py` passes
  - `python -m pytest backend/tests/test_api_contract.py -q` passes

## Implementation Log

### 2026-03-29 - FastAPI Integration
- Implemented Option A endpoints in `backend/main.py`.
- Added SQLite persistence for runs/sessions.
- Added request-id middleware (`x-request-id`).

### 2026-03-29 - Streamlit Procedure Sync
- Patient CPT input changed to procedure dropdown parity.
- React now derives CPT from procedure mapping before submit.

### 2026-03-29 - Backend-Only Rendering
- Removed fake preview payload rendering from React.
- UI now renders only backend-backed data states.

### 2026-03-29 - Clinical Note Formatting
- `denial.note_analysis` renderer now formats section-like text and bullet-like lines for readability.
- Renderer is presentation-only; no synthesized medical content.

### 2026-03-29 - Patient KPI Headline Fix
- Patient KPI headline values changed from high-end values to midpoint values.
- Low-high ranges remain visible.

### 2026-03-29 - Repository Cleanup Pass
- Removed corrupted/garbled text history from this document.
- Kept only active architecture decisions, contract, and validated implementation state.

### 2026-03-29 - Folder Cleanup Pass
- Removed generated folders from this repo only:
  - `.pytest_cache/`
  - `dist/`
  - `backend/__pycache__/`
  - `backend/tests/__pycache__/`
- Intentionally did not remove `node_modules/**/dist` because those are dependency runtime files.
