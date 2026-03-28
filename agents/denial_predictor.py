"""
Denial Predictor Agent — STUB
==============================
P3 replaces this file.

Expected contract:
  READS:  state["hospital_input"] → {cpt_code, icd_code, payer, clinical_note}
          state["benefits"]       → {prior_auth_required}
          state["reeval"]         → bool (True if re-evaluating after fix applied)
          state["fix_list"]       → list (check which fixes have applied=True)
  WRITES: state["ncci_result"]    → {valid, edit_flags, mue_check}
          state["denial_score"]   → {risk_pct, status, risk_factors, note_analysis}
          state["fix_list"]       → [{issue, action, risk_reduction, applied}]
          state["reeval"]         → False (reset after re-eval completes)
          state["messages"]

Data files used:
  - data/ncci_edits.json   (PTP edit pairs + MUE limits)
  - data/denial_rules.json (base rates + risk factors + demo scenarios)

Claude API calls:
  - prompts/denial_prompt.py for clinical note analysis
  - prompts/denial_prompt.py for fix list wording
  - Claude NEVER generates a risk score — only analyzes notes and writes fix actions

Scoring formula:
  total_denial_risk = min(0.95, base_rate + sum(risk_increases))
  Status tiers: <0.10 LOW, 0.10–0.30 MEDIUM, >0.30 HIGH
"""


def denial_predictor(state: dict) -> dict:
    benefits = state.get("benefits")
    if not isinstance(benefits, dict) or "prior_auth_required" not in benefits:
        raise ValueError("denial_predictor requires state['benefits']['prior_auth_required'] before scoring")

    reeval = state.get("reeval", False)

    if reeval:
        return {
            "ncci_result": {"valid": True, "edit_flags": [], "mue_check": {}},
            "denial_score": {
                "risk_pct": 0.04,
                "status": "LOW RISK",
                "risk_factors": [],
                "note_analysis": "Clinical note supports medical necessity. Prior auth now attached.",
            },
            "fix_list": [
                {"issue": "Prior authorization not on file",
                 "action": "Obtain prior authorization number from Aetna for CPT 73721. Attach to claim field 23.",
                 "risk_reduction": 0.28, "applied": True},
            ],
            "reeval": False,
            "messages": [{"role": "system", "content": "Denial predictor: re-eval complete (STUB)."}],
        }

    return {
        "ncci_result": {"valid": True, "edit_flags": [], "mue_check": {}},
        "denial_score": {
            "risk_pct": 0.34,
            "status": "HIGH RISK",
            "risk_factors": [
                {"factor_key": "missing_prior_auth",
                 "description": "Prior authorization not obtained or not on file",
                 "risk_increase": 0.30},
            ],
            "note_analysis": (
                "Clinical note documents right knee pain x3 months with positive McMurray test "
                "and medial compartment narrowing on X-ray. Supports medical necessity for MRI. "
                "However, Aetna PPO requires prior authorization for CPT 73721 (advanced imaging)."
            ),
        },
        "fix_list": [
            {"issue": "Prior authorization not on file",
             "action": "Contact Aetna provider services. Obtain auth number for CPT 73721. Attach to claim field 23 before submission.",
             "risk_reduction": 0.28, "applied": False},
        ],
        "messages": [{"role": "system", "content": "Denial predictor: returned demo data (STUB)."}],
    }
