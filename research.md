# Person 1 Research and Implementation Log (LangGraph + Streamlit)

Date: 2026-03-28
Source alignment: `unified_build_guide_v2.docx` (Sections 3, 5, 7, 8)

Process rule: Always update `research.md` after each meaningful implementation or validation step.

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

## Part 2 Merge Update (Adapter-First, Base Logic Preserved) — 2026-03-28

Status: Completed

### What was merged
- Main contract remained unchanged (graph/UI schema frozen).
- `agents/cost_predictor.py` now uses Part 2 compute engine as the calculation core:
  - `part2.Data.compute.compute_estimate(...)` is called directly.
  - Part 2 formulas were preserved (no calculation rewrite); only input/output adapters were added.
- `agents/coverage_analyzer.py` kept its existing contract and still guarantees `benefits.prior_auth_required`.

### Adapter mapping table (main contract -> Part 2 compute -> returned main state)
| Main input key | Adapter value for P2 compute | Main output key |
|---|---|---|
| `patient_input.cpt_code` | `procedure` via CPT->procedure lookup | `cost_estimate.*`, `cms_rates`, `fee_schedule` |
| `patient_input.zip_code` | `location` via ZIP prefix -> state name | `fee_schedule` locality selection + `cms_rates` filter |
| `patient_input.insurance_type` | `insurance_plan` (`aetna_ppo->PPO`, `bcbs_ppo->PPO_BCBS`, `unitedhealthcare_hmo->HMO`) | `fee_schedule.commercial_estimate_*`, `cost_estimate.insurance_*` |
| `patient_input.provider_type` | `provider` (`hospital->Hospital`, `imaging_center/asc->Private Clinic`) | `cost_estimate.total_*`, `cost_estimate.oop_*` |
| `patient_input.urgency` | `urgency` (`routine/urgent/emergency` -> title-cased P2 values) | `cost_estimate.total_*` |
| `benefits.*` (from coverage node) | prompt context only (deductible/coinsurance/prior auth) | `cost_estimate.explanation`, `cost_estimate.savings_tips` |

### Output shape guarantees kept
- `cost_predictor` returns only main expected keys:
  - `cms_rates`
  - `fee_schedule`
  - `cost_estimate` (with nested `explanation` + `savings_tips`)
  - `messages`
- No top-level prior-auth output keys introduced.

### Secret hygiene
- Removed hardcoded Anthropic key line from `part2/agents/cost_predictor.py`.
- Updated Part 2 compute imports to package-safe relative imports (`part2/Data/compute.py`) for mainline compatibility.
- Repo scan for `sk-ant-` now returns no matches.

### Verification results
- `python graph.py` passes all smoke paths:
  - patient
  - hospital
  - hospital re-eval
- Adapter contract test passed:
  - verified `cms_rates`, `fee_schedule`, `cost_estimate`, `messages` exist
  - verified nested `cost_estimate.explanation` and `cost_estimate.savings_tips`
- Coverage safety matrix passed:
  - (`aetna_ppo`, `73721`)
  - (`bcbs_ppo`, `71260`)
  - (`unitedhealthcare_hmo`, `29827`)
  - invalid plan fallback
  - unknown CPT fallback

### Notes
- Base compute behavior changed output values versus old stub ranges (expected). Example patient OOP high moved from `370` (stub) to `349` (Part 2 compute result).
- Streamlit manual re-check is still recommended after these adapter changes.

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
