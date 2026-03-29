"""
Denial Predictor Agent — Person 3
===================================
READS:  state["hospital_input"] → {cpt_code, icd_code, payer, clinical_note}
        state["benefits"]       → {prior_auth_required}
        state["reeval"]         → bool (True if re-evaluating after fix applied)
WRITES: state["ncci_result"]    → {valid, edit_flags, mue_check}
        state["denial_score"]   → {risk_pct, status, risk_factors, note_analysis}
        state["fix_list"]       → [{issue, action, risk_reduction, applied}]
        state["reeval"]         → False (reset after re-eval)
        state["messages"]
"""

import json
import os
from dotenv import load_dotenv

load_dotenv()


# ── Data loaders ──────────────────────────────────────────────────────────────

def load_ncci_edits():
    path = os.path.join(os.path.dirname(__file__), "../data/ncci_edits.json")
    with open(path, "r") as f:
        return json.load(f)

def load_denial_rules():
    path = os.path.join(os.path.dirname(__file__), "../data/denial_rules.json")
    with open(path, "r") as f:
        return json.load(f)

def load_member_benefits():
    path = os.path.join(os.path.dirname(__file__), "../data/member_benefits.json")
    with open(path, "r") as f:
        return json.load(f)


# ── Phase 1: NCCI Checks ──────────────────────────────────────────────────────

def check_ptp_edits(primary_cpt: str, other_cpts: list) -> dict:
    ncci = load_ncci_edits()
    ptp_edits = ncci.get("ptp_edits", {})
    edit_flags = []

    if primary_cpt in ptp_edits:
        pairs = ptp_edits[primary_cpt].get("edit_pairs", [])
        for pair in pairs:
            col2 = pair["column_two"]
            if col2 in other_cpts:
                edit_flags.append({
                    "primary": primary_cpt,
                    "conflicting_code": col2,
                    "conflicting_desc": pair["column_two_desc"],
                    "modifier_allowed": pair["modifier_indicator"] == "1",
                    "rationale": pair["rationale"]
                })

    return {
        "valid": len(edit_flags) == 0,
        "edit_flags": edit_flags
    }


def check_mue(cpt: str, units: int) -> dict:
    ncci = load_ncci_edits()
    mue_edits = ncci.get("mue_edits", {})

    if cpt not in mue_edits:
        return {
            "valid": True,
            "max_units": None,
            "billed_units": units,
            "exceeded": False,
            "rationale": "No MUE limit found for this CPT code"
        }

    mue = mue_edits[cpt]
    exceeded = units > mue["max_units"]
    return {
        "valid": not exceeded,
        "max_units": mue["max_units"],
        "billed_units": units,
        "exceeded": exceeded,
        "rationale": mue["rationale"]
    }


# ── Phase 2: Prior Auth + Risk Scorer ────────────────────────────────────────

def check_prior_auth(cpt: str, payer: str) -> dict:
    benefits = load_member_benefits()
    plans = benefits.get("plans", {})

    if payer not in plans:
        return {"required": False, "notes": f"Payer '{payer}' not found"}

    prior_auth_rules = plans[payer].get("prior_auth_rules", {})
    if cpt not in prior_auth_rules:
        return {"required": False, "notes": f"No prior auth rule for CPT {cpt}"}

    rule = prior_auth_rules[cpt]
    return {"required": rule["required"], "notes": rule["notes"]}


def get_risk_status(score: float) -> str:
    if score < 0.10:
        return "LOW RISK"
    elif score <= 0.30:
        return "MEDIUM RISK"
    else:
        return "HIGH RISK"


def compute_risk_score(
    cpt: str,
    payer: str,
    ncci_result: dict,
    prior_auth_obtained: bool,
    units: int = 1,
    additional_risk_factors: list = None
) -> dict:
    rules = load_denial_rules()
    base_rates = rules.get("base_denial_rates", {})
    risk_factors_data = rules.get("risk_factors", {})

    base_rate = base_rates[cpt]["base_rate"] if cpt in base_rates else 0.10
    total_score = base_rate
    active_factors = []

    if not ncci_result.get("valid", True):
        factor = risk_factors_data.get("ncci_edit_violation", {})
        increase = factor.get("risk_increase", 0.35)
        total_score += increase
        active_factors.append({
            "factor_key": "ncci_edit_violation",
            "description": factor.get("description", "NCCI edit violation"),
            "risk_increase": increase
        })

    mue_result = check_mue(cpt, units)
    if mue_result["exceeded"]:
        factor = risk_factors_data.get("mue_exceeded", {})
        increase = factor.get("risk_increase", 0.30)
        total_score += increase
        active_factors.append({
            "factor_key": "mue_exceeded",
            "description": factor.get("description", "MUE exceeded"),
            "risk_increase": increase
        })

    auth_check = check_prior_auth(cpt, payer)
    if auth_check["required"] and not prior_auth_obtained:
        factor = risk_factors_data.get("missing_prior_auth", {})
        increase = factor.get("risk_increase", 0.30)
        total_score += increase
        active_factors.append({
            "factor_key": "missing_prior_auth",
            "description": factor.get("description", "Prior authorization not obtained"),
            "risk_increase": increase
        })

    if additional_risk_factors:
        for factor_key in additional_risk_factors:
            if factor_key in risk_factors_data:
                factor = risk_factors_data[factor_key]
                increase = factor.get("risk_increase", 0)
                total_score += increase
                active_factors.append({
                    "factor_key": factor_key,
                    "description": factor.get("description", factor_key),
                    "risk_increase": increase
                })

    final_score = round(min(0.95, total_score), 4)
    return {
        "risk_pct": final_score,
        "status": get_risk_status(final_score),
        "risk_factors": active_factors,
        "base_rate": base_rate
    }


# ── Phase 3: Claude API Call ──────────────────────────────────────────────────

def call_claude(prompt: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "STUB: Claude response will appear here when API key is set."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Claude API error: {str(e)}"


# ── Phase 3: Fix List Parser ──────────────────────────────────────────────────

def parse_fix_list_from_claude(raw_text: str, risk_factors: list) -> list:
    """
    Try to parse Claude's JSON fix list response.
    Falls back to building fixes from denial_rules.json if JSON parse fails.
    Each fix includes 'applied: False' as required by P1's contract.
    """
    # Try JSON parse first (P1's prompt asks for JSON)
    try:
        payload = json.loads(raw_text)
        fix_list = payload.get("fix_list", [])
        return [
            {
                "issue": str(f.get("issue", "")).strip(),
                "action": str(f.get("action", "")).strip(),
                "risk_reduction": float(f.get("risk_reduction", 0.0)),
                "applied": False
            }
            for f in fix_list if isinstance(f, dict)
        ]
    except (json.JSONDecodeError, Exception):
        pass

    # Fallback: build fixes from denial_rules.json
    rules = load_denial_rules()
    risk_factors_data = rules.get("risk_factors", {})
    fix_list = []
    for factor in risk_factors:
        factor_key = factor.get("factor_key", "")
        if factor_key in risk_factors_data:
            rule = risk_factors_data[factor_key]
            fix_list.append({
                "issue": rule.get("description", factor_key),
                "action": rule.get("fix", "Review and correct before submission."),
                "risk_reduction": rule.get("fix_risk_reduction", 0.0),
                "applied": False
            })
    return fix_list


# ── Main Agent Function ───────────────────────────────────────────────────────

def denial_predictor(state: dict) -> dict:
    """
    Main denial predictor agent — called by LangGraph.
    Matches P1's contract exactly.
    """
    from prompts.denial_prompt import build_note_analysis_prompt, build_fix_list_prompt

    # ── Validate required state fields ──
    benefits = state.get("benefits")
    if not isinstance(benefits, dict) or "prior_auth_required" not in benefits:
        raise ValueError("denial_predictor requires state['benefits']['prior_auth_required']")

    # ── Read inputs ──
    hospital_input    = state.get("hospital_input", {})
    cpt_code          = str(hospital_input.get("cpt_code", "")).strip()
    icd_code          = str(hospital_input.get("icd_code", "")).strip()
    payer             = str(hospital_input.get("payer", "")).strip()
    clinical_note     = str(hospital_input.get("clinical_note", "")).strip()
    other_cpts        = hospital_input.get("other_cpts", [])
    units             = int(hospital_input.get("units", 1))
    prior_auth_required = benefits.get("prior_auth_required", False)
    reeval            = state.get("reeval", False)

    # ── Handle re-evaluation after fix applied ──
    if reeval:
        existing_fix_list = state.get("fix_list", [])
        # Mark applied fixes and recompute score
        ncci_result = check_ptp_edits(cpt_code, other_cpts)
        # On reeval, assume prior auth has been obtained
        denial_score = compute_risk_score(
            cpt=cpt_code,
            payer=payer,
            ncci_result=ncci_result,
            prior_auth_obtained=True,
            units=units
        )
        denial_score["note_analysis"] = "Prior auth attached. Risk reduced after fix applied."

        updated_fixes = [
            {**fix, "applied": True} for fix in existing_fix_list
        ]

        return {
            "ncci_result": {**ncci_result, "mue_check": check_mue(cpt_code, units)},
            "denial_score": denial_score,
            "fix_list": updated_fixes,
            "reeval": False,
            "messages": [{"role": "system", "content": "Denial predictor: re-eval complete."}]
        }

    # ── Step 1: NCCI Check ──
    ncci_result = check_ptp_edits(cpt_code, other_cpts)
    mue_check   = check_mue(cpt_code, units)

    # ── Step 2: Risk Score ──
    denial_score = compute_risk_score(
        cpt=cpt_code,
        payer=payer,
        ncci_result=ncci_result,
        prior_auth_obtained=not prior_auth_required,
        units=units
    )

    # ── Step 3: Claude Note Analysis ──
    note_prompt   = build_note_analysis_prompt(
        clinical_note=clinical_note,
        cpt_code=cpt_code,
        icd_code=icd_code,
        payer=payer,
        prior_auth_required=prior_auth_required
    )
    note_analysis = call_claude(note_prompt)
    denial_score["note_analysis"] = note_analysis

    # ── Step 4: Claude Fix List ──
    fix_list = []
    if denial_score["risk_factors"]:
        fix_prompt   = build_fix_list_prompt(
            risk_factors=denial_score["risk_factors"],
            cpt_code=cpt_code,
            payer=payer
        )
        fix_list_raw = call_claude(fix_prompt)
        fix_list     = parse_fix_list_from_claude(fix_list_raw, denial_score["risk_factors"])

    return {
        "ncci_result":  {**ncci_result, "mue_check": mue_check},
        "denial_score": denial_score,
        "fix_list":     fix_list,
        "reeval":       False,
        "messages":     [{"role": "system", "content": f"Denial predictor: {denial_score['status']} {denial_score['risk_pct']:.0%}"}]
    }