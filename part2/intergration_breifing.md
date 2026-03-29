# Part 2 Integration Briefing (Adapter Strategy)

Date: 2026-03-28

## Integration policy
Part 2 logic is merged via adapters into the main contract.
Main `graph.py` and `app.py` schema remain unchanged.

## Compatibility guarantees
- Cost compute core is preserved from Part 2 (`part2.Data.compute.compute_estimate`).
- Main agent signature remains `cost_predictor(state: dict) -> dict`.
- Prior auth remains nested in `benefits.prior_auth_required` (required by denial safety checks).
- Cost explanation and tips remain nested in `cost_estimate`.

## Non-goals in this merge
- No graph topology refactor.
- No UI schema/key refactor.
- No formula rewrite of Part 2 compute engine.

## Follow-up
- Validate end-to-end again after P3 denial agent integration.
- Rotate Anthropic key if previously exposed outside this workspace.
