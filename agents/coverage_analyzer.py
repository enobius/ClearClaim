"""
Coverage Analyzer Agent
=======================
Shared node for both patient and hospital paths.
Loads plan and prior auth rules from data/member_benefits.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "member_benefits.json"
DEFAULT_PLAN = "aetna_ppo"


@tool(parse_docstring=True)
def lookup_member_benefits(plan_key: str, cpt_code: str) -> dict:
    """Lookup plan benefits and prior auth details for a CPT.

    Args:
        plan_key: Insurance plan key (for example aetna_ppo, bcbs_ppo, unitedhealthcare_hmo).
        cpt_code: Procedure CPT code as a 5-digit string.

    Returns:
        A dict containing deductible/coinsurance details and prior authorization requirements.
        Output keys: deductible_remaining, coinsurance, prior_auth_required, prior_auth_notes,
        out_of_pocket_max, out_of_pocket_spent, plan_name, plan_type.
    """

    with DATA_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    plans = payload.get("plans", {})
    selected_key = plan_key if plan_key in plans else DEFAULT_PLAN
    plan = plans.get(selected_key, {})

    benefits = plan.get("benefits", {})
    prior_auth_rules = plan.get("prior_auth_rules", {})
    auth_rule = prior_auth_rules.get(cpt_code, {"required": False, "notes": "No prior auth rule found for this CPT."})

    return {
        "deductible_remaining": float(benefits.get("individual_deductible_remaining", 0.0)),
        "coinsurance": float(benefits.get("coinsurance_in_network", 0.0)),
        "prior_auth_required": bool(auth_rule.get("required", False)),
        "prior_auth_notes": str(auth_rule.get("notes", "")),
        "out_of_pocket_max": float(benefits.get("out_of_pocket_max", 0.0)),
        "out_of_pocket_spent": float(benefits.get("out_of_pocket_spent", 0.0)),
        "plan_name": str(plan.get("plan_name", "Unknown Plan")),
        "plan_type": str(plan.get("plan_type", "Unknown")),
    }


def coverage_analyzer(state: dict) -> dict:
    mode = state.get("mode", "patient")
    patient_input = state.get("patient_input", {})
    hospital_input = state.get("hospital_input", {})

    if mode == "patient":
        raw_plan_key = patient_input.get("insurance_type")
        raw_cpt_code = patient_input.get("cpt_code")
    else:
        raw_plan_key = hospital_input.get("payer")
        raw_cpt_code = hospital_input.get("cpt_code")

    plan_key = str(raw_plan_key).strip() if raw_plan_key is not None else ""
    cpt_code = str(raw_cpt_code).strip() if raw_cpt_code is not None else ""

    if not plan_key:
        plan_key = DEFAULT_PLAN
    if not cpt_code:
        cpt_code = "73721"

    benefits = lookup_member_benefits.invoke({"plan_key": plan_key, "cpt_code": cpt_code})

    return {
        "benefits": benefits,
        "messages": [
            {
                "role": "system",
                "content": f"Coverage analyzer: loaded plan '{plan_key}' for CPT {cpt_code}.",
            }
        ],
    }
