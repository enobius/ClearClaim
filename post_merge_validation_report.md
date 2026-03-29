# Post-Merge Validation Report (Person 1)

Date: 2026-03-29
Scope: Review-only audit of merged orchestration, cost, coverage, denial, and UI loopback behavior.
Source Alignment: `unified_build_guide_v2.docx` (Sections 3, 7, 10)

## Executive Result
- Overall status: Functional and demo-capable with one medium and one low residual risk.
- `python graph.py` smoke suite passes all required paths:
  - patient mode
  - hospital mode
  - hospital re-eval loop

## Findings (Severity Ordered)

1. MEDIUM — Invalid CPT is tolerated, not rejected
- `graph.py` validates required field presence, but not CPT format/existence.
- Cost path falls back to zero/default outputs for unknown CPTs instead of explicit validation failure.
- References:
  - `graph.py:175-191` (`validate_entry`)
  - `agents/cost_predictor.py:74-76` (scenario fallback)
  - `agents/cost_predictor.py:102-110` (fee schedule fallback)
- Risk: judge/tester may receive plausible output for invalid CPT without explicit warning.

2. MEDIUM — "No-number" policy is prompt-level only
- Prompt forbids invented numbers, but there is no runtime response validator that rejects numerical hallucinations in explanation text.
- References:
  - `prompts/cost_prompt.py:29-33`
  - `agents/cost_predictor.py:237-250`
- Risk: low-probability explanation drift if model response violates prompt constraints.

3. LOW — UI apply-fix error path returns from main flow
- In `app.py`, missing `hospital_result` during apply-fix triggers `return`, which exits `main()` early for that run.
- Reference: `app.py:196-200`
- Risk: minor UX behavior; not a graph correctness issue.

## Integrity Checks (All Passed)

- State contract key consistency
  - Cost node writes expected keys (`cms_rates`, `fee_schedule`, `cost_estimate`, `messages`).
  - Denial node writes expected keys (`ncci_result`, `denial_score`, `fix_list`, `reeval`, `messages`).
- Re-eval persistence
  - Apply-fix payload is built from full computed `hospital_result`, preserving benefits context.
  - Reference: `app.py:204-207`
- Coverage fallback
  - Missing plan key falls back to `DEFAULT_PLAN`.
  - Reference: `agents/coverage_analyzer.py:72-75`
- Loopback stability
  - Re-eval path resets `reeval=False` after denial re-entry.
  - Reference: `agents/denial_predictor.py:292`
- Security hygiene
  - Repo scan for `sk-ant-` returned no matches.

## Demo Verification (Knee MRI)

- Patient mode (`73721`, `aetna_ppo`, `06604`): prior auth flag present; numeric outputs rendered.
- Hospital mode (`73721`, `M17.11`, `aetna_ppo`): denial score ~34%.
- Apply-fix loop: score drops to ~4% and updates in-place.

## Recommendation Before Final Rehearsal

- Add explicit CPT whitelist/format validation in `validate_entry` (or at node boundary) to fail fast on invalid CPT.
- Add lightweight explanation text guard (detect/flag out-of-band numbers) if strict no-number enforcement is required for judging.
