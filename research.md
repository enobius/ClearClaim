# Person 1 Research and Implementation Log (LangGraph + Streamlit)

Date: 2026-03-28
Source alignment: `unified_build_guide_v2.docx` (Sections 3, 5, 7, 8)

Process rule: Always update `research.md` after each meaningful implementation or validation step.

## Post-Merge Validation Review — 2026-03-29

Status: Functional with residual risks (review-only)

### Findings (severity ordered)
- MEDIUM: Invalid CPT is tolerated rather than rejected
  - `validate_entry` checks required fields but not CPT format/existence.
  - Cost path falls back to defaults for unknown CPT instead of explicit validation error.
  - References: `graph.py:175-191`, `agents/cost_predictor.py:74-76`, `agents/cost_predictor.py:102-110`.
- MEDIUM: No-number policy is prompt-enforced but not runtime-enforced
  - Prompt forbids invented numbers; response is not post-validated for numeric drift.
  - References: `prompts/cost_prompt.py:29-33`, `agents/cost_predictor.py:237-250`.
- LOW: Apply-fix missing-state path returns from `main()`
  - Error path in Streamlit uses `return`, exiting current run early.
  - Reference: `app.py:196-200`.

### Integrity checks passed
- State key contract consistency across cost/coverage/denial writers.
- Re-eval payload persistence uses full `hospital_result` context.
- Coverage fallback to `DEFAULT_PLAN` works.
- Re-eval loop resets `reeval=False` after denial re-entry.
- Security hygiene scan (`sk-ant-`) returned no matches.
- `python graph.py` smoke tests pass all three flows.

### Demo verification status (Knee MRI)
- Patient mode: deterministic ranges + prior auth banner.
- Hospital mode: ~34% risk.
- Apply-fix loop: drops to ~4% and updates in-place.

### Action recommendations before final rehearsal
1. Add explicit CPT whitelist/format validation in `validate_entry`.
2. Add lightweight runtime guard for explanation numeric drift if strict judge-proofing is required.

## Remediation Update (Tech Lead Audit) — 2026-03-28

Status: Completed

### Issue Disposition
- Issue 1 (HIGH): Fixed in `app.py`
  - Re-eval payload source changed from original input payload to full computed hospital state.
  - `reeval_payload` now starts from `st.session_state.hospital_result`.
  - Added defensive check: if no hospital result is present, UI shows an error and skips re-eval invoke.
- Issue 2 (MEDIUM): Fixed in `agents/denial_predictor.py`
  - Added guard at function entry requiring `state["benefits"]["prior_auth_required"]`.
  - Raises clear `ValueError` if benefits context is missing.
  - Graph topology intentionally unchanged (`output_writer -> denial_predictor` re-eval shortcut retained).
- Issue 3 (MEDIUM): Hardened in `agents/coverage_analyzer.py`
  - Added normalization for `plan_key` and `cpt_code` before tool invocation.
  - Empty/None plan falls back to `DEFAULT_PLAN`.
  - Empty/None CPT falls back to `"73721"`.
  - Existing unknown-CPT fallback behavior remains (`required=False` + fallback note).

### Validation Results (Post-Remediation)
- Graph smoke tests passed:
  - `python graph.py`
  - Patient flow pass
  - Hospital flow pass
  - Hospital re-eval flow pass (34% -> 4% with stubs)
- Compile checks passed:
  - `python -m py_compile app.py agents/coverage_analyzer.py agents/denial_predictor.py`
- Coverage analyzer matrix passed:
  - (`aetna_ppo`, `73721`)
  - (`bcbs_ppo`, `71260`)
  - (`unitedhealthcare_hmo`, `29827`)
  - (`invalid_plan`, `73721`) -> fell back to Aetna default plan cleanly
  - (`aetna_ppo`, `99999`) -> `prior_auth_required=False` with fallback note
- Re-eval payload preservation test passed:
  - Verified payload built from full prior result contains `benefits`, `ncci_result`, `denial_score` before invoke.
  - Re-eval risk delta remained stable (`0.34 -> 0.04`) in stub scenario.

### Remaining Integration Risk Notes
- P2/P3 agent internals are still stubs in this branch; full end-to-end confidence depends on their real implementations.
- `output_writer` defaulting can still mask incorrect agent output shapes; run strict key checks during merge validation.

## Scope
Person 1 owns:
- LangGraph orchestration backbone (`graph.py` + supervisor routing)
- Streamlit UI (`app.py`) with patient and hospital tabs

## Current Status vs Required Blocks

### Block 1: Scaffold + State Schema (Hours 0-1)
Status: Complete
- `requirements.txt` includes required stack (`langgraph`, `anthropic`, `streamlit`).
- Shared graph state is explicitly defined in `graph.py` with strict mode-based validation at entry.

### Block 2: Supervisor + Stub/Real Agent Wiring (Hours 1-3)
Status: Complete
- Graph topology corrected to benefits-first flow:
  - `START -> validate_entry -> nlp_parser -> supervisor -> coverage_analyzer -> predictor_guard -> cost_predictor|denial_predictor -> output_writer -> END`
- Re-eval loop implemented:
  - `output_writer -> denial_predictor` when `mode="hospital"` and `reeval=True`.
- Active nodes are wired to module agents:
  - `agents.supervisor.supervisor`
  - `agents.coverage_analyzer.coverage_analyzer`
  - `agents.cost_predictor.cost_predictor`
  - `agents.denial_predictor.denial_predictor`
- Optional demo stubs are retained behind `USE_STUB_AGENTS=1`.

### Block 3: Streamlit UI (Hours 3-7)
Status: Complete
- `app.py` implemented with two tabs:
  - Patient mode form + output cards/split/proir-auth banner/tips
  - Hospital mode form + denial badge/NCCI/risk factors/fix list
- Graph invocation wired for both tabs.
- Hospital Apply Fix loopback implemented (`fix_list` update + `reeval=True` re-entry).

### Block 4: Polish + Demo Setup (Hours 7-10)
Status: Complete (MVP level)
- Added loading states (`st.spinner`).
- Added demo prefill buttons for patient and hospital Knee MRI scenarios.
- Added transparency footer text.

### Block 5: Integration (Hours 10-12)
Status: In progress
- Orchestration is integration-ready and uses module imports by default.
- Final integration quality depends on P2/P3 replacing their current stub internals with full logic.

## Implemented Fixes (from prior findings)

1. Resolved: Benefits ordering/data-contract break
- `coverage_analyzer` now runs before predictor routing.
- `predictor_guard` enforces `benefits.prior_auth_required` presence.

2. Resolved: Stub drift in graph wiring
- Graph active path imports module agents directly.
- Stubs are explicit fallback only.

3. Resolved: Missing UI entrypoint
- `app.py` now exists and runs with two-tab flow.

4. Partially resolved: Supervisor duplication risk
- Graph now uses `agents/supervisor.py` as active source.
- Local helper logic in graph is reduced to non-supervisor concerns.

5. Resolved: Windows smoke output encoding
- ASCII-safe smoke output used (`All smoke tests passed`).

## Additional Implementation Details

### Coverage analyzer tool contract
- `agents/coverage_analyzer.py` includes:
  - `@tool(parse_docstring=True)` on `lookup_member_benefits(...)`
  - JSON-backed lookup from `data/member_benefits.json`
  - Node-level adapter `coverage_analyzer(state) -> dict`

### Prompt constraints and structured output helpers
- `prompts/cost_prompt.py`:
  - Explicit deterministic-number constraints
  - `get_cost_response_config()` for low-variance settings
- `prompts/denial_prompt.py`:
  - Explicit no-risk-score generation constraint
  - `get_denial_response_config()` with `output_version="responses/v1"`
  - `parse_fix_list_response(...)` strict JSON parsing/normalization fallback

## Validation Log

Completed:
- `python graph.py` smoke tests pass:
  - Patient flow pass
  - Hospital flow pass
  - Hospital re-eval flow pass
- `python -m py_compile graph.py agents/coverage_analyzer.py prompts/cost_prompt.py prompts/denial_prompt.py app.py` pass
- User-confirmed: Streamlit run appears functional in local environment

Known environment note:
- In sandbox runtime, `streamlit` import test was unavailable due to missing package install, but user verified local run works.

## Integration Checklist for P2/P3 Handoff

- [x] P2 replaces `agents/cost_predictor.py` stub internals with adapter-based compute/fee/prompt flow (main contract preserved)
- [x] Coverage analyzer is real JSON-backed and graph-integrated
- [ ] P3 replaces `agents/denial_predictor.py` stub internals with real NCCI/risk/fix flow
- [x] Graph edges validated for both modes and re-eval loop
- [x] `app.py` tested manually for both tabs (user-confirmed Streamlit working)
- [ ] Final end-to-end run with non-stub P2/P3 internals

## Next Action Focus
1. Coordinate with P2/P3 on exact output key shapes to keep strict state contract stable.
2. Run one full end-to-end demo after P2/P3 internals are merged.
3. Keep updating this file after each merge/test cycle.

## Person 1 Hardening + Regression Update - 2026-03-29

Status: Completed

### Implemented fixes (residual issues)
- Strict CPT validation in orchestration (`graph.py`)
  - Added 5-digit CPT regex validation in `validate_entry`.
  - Added supported CPT whitelist validation: `73721`, `71260`, `29827`, `45380`, `93306`.
  - Invalid CPT now fails fast with clear `ValueError` messages.
- Runtime no-number guard in cost explanation (`agents/cost_predictor.py`)
  - Added numeric token extraction/normalization guard for explanation text.
  - Allowed numbers are constrained to deterministic inputs (CPT, rates/ranges, deductible, coinsurance, submitted charge).
  - If drift is detected, explanation is replaced with safe fallback and a system message is added.
- Streamlit apply-fix UX safety (`app.py`)
  - Missing `hospital_result` branch now shows an error and skips re-eval invoke without exiting the page flow.
  - Re-eval still uses `hospital_result` as payload base.

### Regression acceptance criteria (release gate)
- [x] `python graph.py` smoke tests pass (patient, hospital, hospital re-eval).
- [x] Invalid CPT inputs fail fast with explicit validation errors.
- [x] No-number guard accepts valid explanation numbers and rejects out-of-band numbers.
- [x] 5 canonical patient regression scenarios match exact expected outputs.
- [x] Hospital apply-fix path remains stable (stub behavior: ~34% to ~4%).

### Test run log (2026-03-29)
- Command: `python graph.py`
  - Result: PASS
  - Notes: All 3 smoke scenarios passed. Re-eval risk remained 34% -> 4%.
- Command: `python -m py_compile graph.py agents/cost_predictor.py app.py`
  - Result: PASS
- Deterministic 5-case regression suite (graph invoke, patient mode)
  - Knee MRI / Aetna / CT baseline: PASS
  - Chest CT / BCBS / TX urgent: PASS
  - Rotator cuff / UHC HMO / CA emergency: PASS
  - Colonoscopy / BCBS / FL routine imaging center: PASS
  - Echo / Aetna / NY routine ASC: PASS
- Negative CPT validation suite
  - `7372`: PASS (rejected; must be 5-digit)
  - `ABC12`: PASS (rejected; must be 5-digit)
  - `99999`: PASS (rejected; unsupported CPT list)
- No-number guard unit checks
  - Allowed-number explanation: PASS
  - Injected out-of-band number: PASS (fallback explanation applied)

### Pass/fail template for future runs
Use this block each cycle:

```
Run date:
Commit/ref:

1) Smoke (`python graph.py`):
- Patient:
- Hospital:
- Hospital re-eval:

2) CPT validation negatives:
- non-5-digit numeric:
- alphanumeric:
- unsupported 5-digit:

3) No-number guard:
- allowed-numbers case:
- injected-number case:

4) 5-case deterministic regression:
- 73721 / 06604 / aetna_ppo / hospital / routine / partially_met:
- 71260 / 77030 / bcbs_ppo / hospital / urgent / not_met:
- 29827 / 90048 / unitedhealthcare_hmo / hospital / emergency / not_met:
- 45380 / 33136 / bcbs_ppo / imaging_center / routine / fully_met:
- 93306 / 10016 / aetna_ppo / asc / routine / partially_met:

Overall release gate: PASS/FAIL
Blocking issues:
```

## UI Hotfix - Hospital Risk Refresh - 2026-03-29

Status: Completed

- Issue: Hospital denial risk metric did not visually update immediately after Apply Fix.
- Root cause: `render_hospital_result(...)` ran before re-eval completed in the same Streamlit rerun.
- Fix: Added `st.rerun()` after storing re-evaluated state in `app.py` Apply Fix handler.
- Expected behavior now: clicking Apply Fix updates session state and immediately rerenders top-level denial risk metric with new value.
