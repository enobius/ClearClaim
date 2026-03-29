# ClearClaim Design Research

Date: 2026-03-29
Scope: `app.py`, `graph.py`, and the active agent contract behind `build_graph()`

## 1) Current Architecture and Data Flow

### Runtime shape
- The Streamlit UI in `app.py` is the entrypoint.
- `get_graph_app()` caches the compiled LangGraph app with `@st.cache_resource`.
- Both UI tabs call `app.invoke(payload)` directly. There is no HTTP boundary today.
- `graph.py` compiles a `StateGraph` with a shared `GraphState` contract.

### Current graph topology
`START -> validate_entry -> nlp_parser -> supervisor -> coverage_analyzer -> predictor_guard -> cost_predictor|denial_predictor -> output_writer -> END`

Hospital re-evaluation adds a conditional loop:
- `output_writer -> denial_predictor` when `mode == "hospital"` and `reeval == True`

### Current state contract
`GraphState` currently carries both input and output fields:
- Inputs: `mode`, `patient_input`, `hospital_input`, `reeval`
- Shared computed state: `benefits`, `cms_rates`, `fee_schedule`, `cost_estimate`, `ncci_result`, `denial_score`, `fix_list`
- Message trace: `messages` is append-only via `operator.add`

### Data flow for patient mode
1. User submits patient form in Streamlit.
2. UI builds:
   - `mode = "patient"`
   - `patient_input = {cpt_code, zip_code, insurance_type, provider_type, urgency, deductible_status}`
   - `messages = []`
3. `validate_entry()` checks required fields.
4. `nlp_parser()` trims/normalizes `cpt_code`.
5. `supervisor()` logs routing intent only.
6. `coverage_analyzer()` loads benefits from `data/member_benefits.json` using `insurance_type` and `cpt_code`.
7. `predictor_guard()` enforces `benefits.prior_auth_required` exists.
8. `cost_predictor()` runs deterministic pricing logic, builds `cms_rates`, `fee_schedule`, and `cost_estimate`, then adds a narrative explanation and savings tips.
9. `output_writer()` fills default numeric fields and normalizes output for the UI.
10. Streamlit renders patient metrics from the returned dict.

### Data flow for hospital mode
1. User submits hospital form in Streamlit.
2. UI builds:
   - `mode = "hospital"`
   - `hospital_input = {cpt_code, icd_code, payer, clinical_note}`
   - `messages = []`
3. `validate_entry()` checks required fields.
4. `nlp_parser()` trims/normalizes `cpt_code`.
5. `supervisor()` logs routing intent only.
6. `coverage_analyzer()` loads benefits from `data/member_benefits.json` using `payer` and `cpt_code`.
7. `predictor_guard()` enforces `benefits.prior_auth_required` exists.
8. `denial_predictor()` computes NCCI, denial risk, note analysis, and `fix_list`.
9. `output_writer()` normalizes state.
10. Streamlit stores the full result in `st.session_state` and renders it.
11. If a fix is selected, the UI mutates the returned `fix_list`, sets `reeval = True`, and invokes the graph again.

## 2) Current UI Behavior

### Patient mode
- Tabs are rendered with `st.tabs(["Patient Mode", "Hospital Mode"])`.
- A demo button sets `st.session_state.patient_demo_loaded = True`.
- The patient form includes:
  - CPT Code
  - ZIP Code
  - Insurance
  - Provider Type
  - Urgency
  - Deductible Status
- Submit path:
  - Spinner text: `Running patient cost workflow...`
  - On success, patient output is rendered immediately and not persisted in session state.
- Output behavior:
  - Three metrics for total range, out-of-pocket range, and insurance pays
  - Progress bar for patient share vs insurance share
  - Prior auth banner based on `benefits.prior_auth_required`
  - Explanation block from `cost_estimate.explanation`
  - Savings tips from `cost_estimate.savings_tips`
- Important behavior:
  - No patient result is stored for later reuse.
  - The tab is effectively stateless across reruns except for the demo toggle.

### Hospital mode
- A demo button sets `st.session_state.hospital_demo_loaded = True`.
- The hospital form includes:
  - Clinical Note
  - CPT Code
  - ICD-10 Code
  - Payer
- Submit path:
  - Spinner text: `Running hospital denial workflow...`
  - Result is stored in:
    - `st.session_state.hospital_payload`
    - `st.session_state.hospital_result`
    - `st.session_state.hospital_pre_risk`
- Output behavior:
  - Denial risk metric with status label
  - NCCI validity status
  - NCCI flags when present
  - Risk factors list
  - Clinical note analysis block
  - Fix list with applied/pending markers
- Re-evaluation behavior:
  - If fixes exist, the UI shows a selectbox for one fix.
  - Clicking `Apply Fix and Recalculate` clones the current fix list, marks the chosen fix as applied, sets `reeval = True`, and re-invokes the graph with the entire prior hospital result as the base payload.
  - Success message shows risk delta from `hospital_pre_risk` to the new risk.
- Important behavior:
  - Hospital state survives reruns via `st.session_state`.
  - The selected fix is reflected in the UI payload, but the backend re-eval path currently marks all existing fixes applied when it recomputes.

## 3) Identified Coupling and Pain Points

### Tight UI/backend coupling
- The Streamlit app imports `build_graph()` directly and invokes the compiled graph in-process.
- The UI depends on internal graph state keys like `cost_estimate`, `denial_score`, `ncci_result`, `fix_list`, and `benefits`.
- Any backend schema change can break the UI immediately with no versioning layer.

### State management is split and implicit
- Patient mode is effectively transient, while hospital mode is persisted in `st.session_state`.
- Session state keys are ad hoc and UI-owned:
  - `hospital_result`
  - `hospital_payload`
  - `hospital_pre_risk`
  - demo flags
- There is no server-side session record, run history, or audit trail.

### Re-evaluation contract is overloaded
- The current hospital fix flow mutates the prior result and reuses it as the next input.
- The graph has to infer whether it is a first pass or re-eval from `reeval`.
- The backend and UI both participate in fix application semantics, which is brittle.

### Blocking execution model
- `app.invoke()` runs synchronously inside the Streamlit request cycle.
- LLM calls, JSON file reads, and compute steps all block the user experience.
- There is no timeout, queue, retry, or cancellation strategy.

### Hidden contract assumptions
- `coverage_analyzer()` expects a valid plan key and CPT, but defaults silently when values are missing.
- `predictor_guard()` assumes `benefits.prior_auth_required` is present.
- `output_writer()` pads missing numeric outputs with defaults, which can hide upstream contract drift.
- `denial_predictor()` currently uses a graph-level `reeval` flag and fix list shape that the UI must preserve exactly.

### Operational limitations
- No API layer means:
  - No independent frontend deploy
  - No horizontal scaling for UI and backend separately
  - No authenticated API boundary
  - No easy background job handoff
- The current design is fine for a local demo but not for a multi-user product.

## 4) Transition Plan to React + FastAPI

### Target architecture
- React frontend owns presentation, form state, and navigation.
- FastAPI owns request validation, workflow execution, persistence, and auth hooks.
- LangGraph remains the orchestration engine behind FastAPI.
- The backend becomes the only caller of `app.invoke()` or its later equivalent service abstraction.

### Recommended service boundaries
1. React UI
   - Patient and hospital forms
   - Result cards, status banners, and fix application UI
   - Client-side route/state for the active workflow view
2. FastAPI API
   - Validates requests with Pydantic
   - Creates workflow runs
   - Returns synchronous results when quick enough
   - Queues background jobs when latency is uncertain
3. Workflow service
   - Owns LangGraph execution
   - Persists input snapshots and output snapshots
   - Emits structured logs and tracing metadata
4. Storage
   - Postgres for run/session metadata and audit history
   - Redis for job queue and short-lived run state if a queue is used

### API endpoint design

#### Option A: Mode-specific endpoints
This is the clearest mapping to the current UI.

`POST /api/v1/patient/estimate`
- Purpose: run the patient cost workflow
- Request: patient input only
- Response: cost estimate payload

`POST /api/v1/hospital/denial`
- Purpose: run the hospital denial workflow
- Request: hospital input only
- Response: denial score, NCCI result, and fix list

`POST /api/v1/hospital/{run_id}/reevaluate`
- Purpose: apply one or more fixes and rerun hospital scoring
- Request: fix selection or applied fix set
- Response: updated denial score and fix state

`GET /api/v1/runs/{run_id}`
- Purpose: fetch a previous run and its current status

`GET /api/v1/sessions/{session_id}`
- Purpose: fetch session-scoped workflow history for the logged-in user

#### Option B: Unified workflow endpoint
This is easier to extend later if more modes are added.

`POST /api/v1/workflows`
- Request contains `mode` plus the matching input payload
- Response returns a workflow run envelope with mode-specific output

`POST /api/v1/workflows/{run_id}/reevaluate`
- Reuses the same run envelope for fix application

#### Recommendation
- Start with mode-specific endpoints for clarity and simpler client code.
- Internally, route both through a shared workflow service so the implementation stays unified.

### Request and response contracts

#### Common request envelope
```json
{
  "client_request_id": "optional-idempotency-key",
  "session_id": "server-issued-or-client-supplied-session-id",
  "mode": "patient",
  "input": {},
  "context": {
    "timezone": "America/New_York",
    "source": "react-web"
  }
}
```

#### Patient request body
```json
{
  "cpt_code": "73721",
  "zip_code": "06604",
  "insurance_type": "aetna_ppo",
  "provider_type": "hospital",
  "urgency": "routine",
  "deductible_status": "partially_met"
}
```

#### Hospital request body
```json
{
  "cpt_code": "73721",
  "icd_code": "M17.11",
  "payer": "aetna_ppo",
  "clinical_note": "Patient with right knee pain for 3 months..."
}
```

#### Re-evaluation request body
```json
{
  "base_run_id": "run_123",
  "selected_fix_index": 0,
  "applied_fixes": [
    {
      "issue": "Prior authorization not on file",
      "action": "Attach auth number in claim field 23.",
      "risk_reduction": 0.28,
      "applied": true
    }
  ]
}
```

#### Common response envelope
```json
{
  "run_id": "run_123",
  "session_id": "sess_456",
  "mode": "hospital",
  "status": "completed",
  "workflow_version": "2026-03-29",
  "input": {},
  "output": {},
  "warnings": [],
  "messages": [],
  "created_at": "2026-03-29T14:22:11Z",
  "completed_at": "2026-03-29T14:22:13Z"
}
```

#### Mode-specific output contracts
Patient output should preserve:
- `cms_rates`
- `fee_schedule`
- `benefits`
- `cost_estimate`
- `messages`

Hospital output should preserve:
- `ncci_result`
- `denial_score`
- `fix_list`
- `messages`

### Session and state strategy

#### Frontend state
- React should keep only UI state in memory:
  - active mode
  - form drafts
  - selected fix index
  - loading/error state
- Persist only:
  - `session_id`
  - optionally the last run id per tab
- Use local storage only for non-sensitive UX preferences if required.

#### Backend state
- Make the backend the source of truth for workflow history.
- Persist each run as an immutable record:
  - `run_id`
  - `session_id`
  - `mode`
  - normalized request payload
  - raw graph input state
  - output snapshot
  - graph version
  - prompt/version metadata
  - timestamps
  - status
- For hospital re-eval, store a parent-child relation:
  - `base_run_id`
  - `child_run_id`
  - `applied_fixes`

#### Session model
- Prefer a server-issued opaque `session_id` cookie for browser sessions.
- Tie `session_id` to an auth principal once login exists.
- Keep PHI out of client storage unless explicitly required and approved.

### Async/background job strategy

#### When sync is acceptable
- Patient cost estimation is likely a good synchronous path if the deterministic compute stays fast.
- Hospital scoring can also remain synchronous initially if typical latency is low and stable.

#### When async is needed
- Use async jobs for:
  - LLM note analysis
  - long-running data lookups
  - retries after transient provider or model failures
  - batch or bulk claim review

#### Suggested implementation
- FastAPI creates a `run_id` immediately.
- If the workflow is expected to finish quickly, execute inline and return `200`.
- If the workflow may exceed a latency threshold, enqueue a job and return `202 Accepted`.
- Use Redis-backed queueing with a worker process for execution.
- Expose:
  - `GET /api/v1/runs/{run_id}` for polling
  - `GET /api/v1/runs/{run_id}/events` for SSE if live updates are valuable

#### Job states
- `queued`
- `running`
- `completed`
- `failed`
- `canceled`

#### Idempotency
- Require `client_request_id` on all mutation endpoints.
- Deduplicate by `(session_id, client_request_id, endpoint)` so retries do not create duplicate claims.

### Migration roadmap

#### Phase 0: Contract freeze
- Write JSON schemas for current patient and hospital outputs.
- Capture example payloads from the existing Streamlit app.
- Add regression tests that assert keys and basic types.

#### Phase 1: Backend API wrapper
- Build FastAPI endpoints that call the existing graph in-process.
- Keep the current graph code unchanged initially.
- Normalize all results into response envelopes.
- Add request validation with Pydantic models that match the current UI forms.

#### Phase 2: React UI replacement
- Build React screens for:
  - patient estimate
  - hospital denial review
  - fix application and re-evaluation
- Match current Streamlit behavior first, not the final product vision.
- Read/write through FastAPI only.

#### Phase 3: Session and persistence hardening
- Introduce server-side session records.
- Persist runs, fixes, and audit metadata.
- Move `hospital_pre_risk` and similar UI-derived fields into backend state.

#### Phase 4: Async execution and observability
- Add queue-backed background execution for slower or retry-prone paths.
- Add tracing, timing, and structured logs.
- Add explicit failure codes and retry policies.

#### Phase 5: Decompose graph execution
- Replace direct graph invocation from the API layer with a workflow service abstraction.
- If needed, split patient and hospital workflows into separate services or worker queues.

#### Phase 6: Cutover and cleanup
- Remove Streamlit entrypoint after the React UI is stable.
- Remove any temporary compatibility endpoints only after monitoring confirms parity.

## 5) Implementation Details and Risks

### Implementation details to carry forward
- Preserve the current field names where possible:
  - `patient_input`
  - `hospital_input`
  - `benefits`
  - `cost_estimate`
  - `denial_score`
  - `ncci_result`
  - `fix_list`
- Keep `mode` as a first-class discriminator in all contracts.
- Keep `reeval` or replace it with an explicit re-evaluation request model, but do not leave the semantics implicit.
- Version prompt templates and graph execution so the backend can explain result drift.

### Major risks
- Contract drift: React and FastAPI will fail if the output keys change without a version bump.
- Latency spikes: LLM-backed paths may feel sluggish without async execution.
- PHI handling: browser storage and logs must be reviewed carefully.
- Re-eval semantics: selected fix application must be single-source-of-truth, not split between UI and backend.
- Silent defaults: current fallback behavior can hide bad input or upstream failures.
- Regression risk: preserving current UI behavior while changing architecture requires snapshot tests and contract tests.

### Non-goals for the first migration pass
- Do not redesign the underwriting logic.
- Do not rewrite the graph before the API boundary exists.
- Do not add a complex distributed system before run/session persistence is working.

## 6) Recommended Next Step
- Implement the FastAPI wrapper first, using the existing graph and the current output shapes as the source of truth.
- In parallel, define React component contracts from the current Streamlit behaviors so the migration is UI-parity first, architecture second.
