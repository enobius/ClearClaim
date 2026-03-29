"""
ClearClaim LangGraph orchestration (Person 1 owned).

This file is the shared state and routing contract for the whole team.
Field names are locked to the Unified Build Guide Section 3 contract.
"""

from __future__ import annotations

import operator
import os
import re
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.cost_predictor import cost_predictor as module_cost_predictor
from agents.coverage_analyzer import coverage_analyzer as module_coverage_analyzer
from agents.denial_predictor import denial_predictor as module_denial_predictor
from agents.supervisor import supervisor as module_supervisor


USE_STUB_AGENTS = os.getenv("USE_STUB_AGENTS", "0") == "1"
SUPPORTED_CPTS = {"73721", "71260", "29827", "45380", "93306"}


class PatientInput(TypedDict, total=False):
    cpt_code: str
    zip_code: str
    insurance_type: str
    provider_type: str
    urgency: str
    deductible_status: str


class HospitalInput(TypedDict, total=False):
    cpt_code: str
    icd_code: str
    payer: str
    clinical_note: str


class GraphState(TypedDict, total=False):
    patient_input: PatientInput
    hospital_input: HospitalInput
    mode: Literal["patient", "hospital"]

    cms_rates: dict
    fee_schedule: dict
    benefits: dict
    cost_estimate: dict
    ncci_result: dict
    denial_score: dict
    fix_list: list[dict]

    messages: Annotated[list[dict], operator.add]
    reeval: bool


# Optional local demo stubs (only used when USE_STUB_AGENTS=1)
def cost_predictor_stub(state: GraphState) -> dict:
    return {
        "cms_rates": {
            "providers": [
                {
                    "provider_name": "Connecticut Advanced Imaging",
                    "provider_city": "Bridgeport",
                    "avg_submitted_chrg_amt": 1842.0,
                    "avg_medicare_allowed_amt": 466.30,
                },
                {
                    "provider_name": "St. Vincent's Medical Center",
                    "provider_city": "Bridgeport",
                    "avg_submitted_chrg_amt": 2310.0,
                    "avg_medicare_allowed_amt": 512.47,
                },
            ],
            "min_rate": 466.30,
            "max_rate": 512.47,
        },
        "fee_schedule": {
            "medicare_rate": 466.30,
            "facility_fee": 198.42,
            "non_facility_fee": 466.30,
            "commercial_estimate_low": 746.08,
            "commercial_estimate_mid": 885.97,
            "commercial_estimate_high": 1025.86,
        },
        "cost_estimate": {
            "total_low": 746,
            "total_high": 1127,
            "oop_low": 293,
            "oop_high": 370,
            "insurance_low": 453,
            "insurance_high": 757,
            "explanation": "Demo explanation from stub.",
            "savings_tips": [
                "Use an outpatient imaging center if in-network.",
                "Confirm prior authorization before booking.",
                "Bundle care inside one plan year when possible.",
            ],
        },
        "messages": [{"role": "system", "content": "Cost predictor: demo stub."}],
    }


def denial_predictor_stub(state: GraphState) -> dict:
    if state.get("reeval", False):
        return {
            "ncci_result": {"valid": True, "edit_flags": [], "mue_check": {}},
            "denial_score": {
                "risk_pct": 0.04,
                "status": "LOW RISK",
                "risk_factors": [],
                "note_analysis": "Prior auth attached. Low residual risk.",
            },
            "fix_list": [
                {
                    "issue": "Prior authorization not on file",
                    "action": "Attach auth number in claim field 23.",
                    "risk_reduction": 0.28,
                    "applied": True,
                }
            ],
            "reeval": False,
            "messages": [{"role": "system", "content": "Denial predictor: re-eval stub."}],
        }

    return {
        "ncci_result": {"valid": True, "edit_flags": [], "mue_check": {}},
        "denial_score": {
            "risk_pct": 0.34,
            "status": "HIGH RISK",
            "risk_factors": [
                {
                    "factor_key": "missing_prior_auth",
                    "description": "Prior authorization not obtained or not on file",
                    "risk_increase": 0.30,
                }
            ],
            "note_analysis": "Clinical note is likely adequate, but prior auth is missing.",
        },
        "fix_list": [
            {
                "issue": "Prior authorization not on file",
                "action": "Contact payer and attach auth number in claim field 23.",
                "risk_reduction": 0.28,
                "applied": False,
            }
        ],
        "messages": [{"role": "system", "content": "Denial predictor: demo stub."}],
    }


def coverage_analyzer_stub(state: GraphState) -> dict:
    return {
        "benefits": {
            "deductible_remaining": 180.0,
            "coinsurance": 0.20,
            "prior_auth_required": True,
            "prior_auth_notes": "Prior auth required for advanced imaging (MRI/CT/PET)",
            "out_of_pocket_max": 6000.0,
            "out_of_pocket_spent": 485.0,
            "plan_name": "Aetna Open Access PPO",
            "plan_type": "PPO",
        },
        "messages": [{"role": "system", "content": "Coverage analyzer: demo stub."}],
    }


def _require_fields(payload: dict, required: list[str], label: str) -> None:
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")


def _validate_cpt(cpt_code: str, label: str) -> None:
    value = str(cpt_code).strip()
    if not re.fullmatch(r"\d{5}", value):
        raise ValueError(f"{label} cpt_code must be a 5-digit code.")
    if value not in SUPPORTED_CPTS:
        raise ValueError(
            f"{label} cpt_code '{value}' is not supported in this build. "
            f"Supported CPTs: {', '.join(sorted(SUPPORTED_CPTS))}."
        )


def validate_entry(state: GraphState) -> dict:
    mode = state.get("mode")
    if mode not in ("patient", "hospital"):
        raise ValueError("mode must be 'patient' or 'hospital'")

    if mode == "patient":
        patient_input = state.get("patient_input", {})
        _require_fields(
            patient_input,
            ["cpt_code", "zip_code", "insurance_type", "provider_type", "urgency", "deductible_status"],
            "patient_input",
        )
        _validate_cpt(str(patient_input.get("cpt_code", "")), "patient_input")
    else:
        hospital_input = state.get("hospital_input", {})
        _require_fields(
            hospital_input,
            ["cpt_code", "icd_code", "payer", "clinical_note"],
            "hospital_input",
        )
        _validate_cpt(str(hospital_input.get("cpt_code", "")), "hospital_input")

    return {"messages": [{"role": "system", "content": "Entry validation passed."}]}


def nlp_parser(state: GraphState) -> dict:
    mode = state.get("mode", "patient")
    if mode == "patient":
        patient_input = dict(state.get("patient_input", {}))
        patient_input["cpt_code"] = str(patient_input.get("cpt_code", "")).strip()
        return {"patient_input": patient_input, "messages": [{"role": "system", "content": "NLP parser normalized patient input."}]}

    hospital_input = dict(state.get("hospital_input", {}))
    hospital_input["cpt_code"] = str(hospital_input.get("cpt_code", "")).strip()
    return {"hospital_input": hospital_input, "messages": [{"role": "system", "content": "NLP parser normalized hospital input."}]}


def predictor_guard(state: GraphState) -> dict:
    benefits = state.get("benefits", {})
    if "prior_auth_required" not in benefits:
        raise ValueError("benefits.prior_auth_required is required before predictor routing")

    return {"messages": [{"role": "system", "content": "Predictor guard passed."}]}


def output_writer(state: GraphState) -> dict:
    updates: dict = {"messages": [{"role": "system", "content": "Output normalized for UI."}]}

    cost_estimate = dict(state.get("cost_estimate", {}))
    for key in ["total_low", "total_high", "oop_low", "oop_high", "insurance_low", "insurance_high"]:
        cost_estimate.setdefault(key, 0.0)
    updates["cost_estimate"] = cost_estimate

    denial_score = dict(state.get("denial_score", {}))
    denial_score.setdefault("risk_pct", 0.0)
    denial_score.setdefault("status", "LOW RISK")
    denial_score.setdefault("risk_factors", [])
    denial_score.setdefault("note_analysis", "")
    updates["denial_score"] = denial_score

    updates["ncci_result"] = dict(state.get("ncci_result", {"valid": True, "edit_flags": [], "mue_check": {}}))
    updates["fix_list"] = list(state.get("fix_list", []))

    return updates


def route_by_mode_after_coverage(state: GraphState) -> str:
    return "cost_predictor" if state.get("mode") == "patient" else "denial_predictor"


def should_reeval(state: GraphState) -> str:
    if state.get("mode") == "hospital" and state.get("reeval", False):
        return "denial_predictor"
    return END


def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)

    cost_node = cost_predictor_stub if USE_STUB_AGENTS else module_cost_predictor
    denial_node = denial_predictor_stub if USE_STUB_AGENTS else module_denial_predictor
    coverage_node = coverage_analyzer_stub if USE_STUB_AGENTS else module_coverage_analyzer

    graph.add_node("validate_entry", validate_entry)
    graph.add_node("nlp_parser", nlp_parser)
    graph.add_node("supervisor", module_supervisor)
    graph.add_node("coverage_analyzer", coverage_node)
    graph.add_node("predictor_guard", predictor_guard)
    graph.add_node("cost_predictor", cost_node)
    graph.add_node("denial_predictor", denial_node)
    graph.add_node("output_writer", output_writer)

    graph.add_edge(START, "validate_entry")
    graph.add_edge("validate_entry", "nlp_parser")
    graph.add_edge("nlp_parser", "supervisor")
    graph.add_edge("supervisor", "coverage_analyzer")
    graph.add_edge("coverage_analyzer", "predictor_guard")

    graph.add_conditional_edges(
        "predictor_guard",
        route_by_mode_after_coverage,
        {"cost_predictor": "cost_predictor", "denial_predictor": "denial_predictor"},
    )

    graph.add_edge("cost_predictor", "output_writer")
    graph.add_edge("denial_predictor", "output_writer")

    graph.add_conditional_edges(
        "output_writer",
        should_reeval,
        {"denial_predictor": "denial_predictor", END: END},
    )

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()

    print("=== Patient mode test ===")
    patient_result = app.invoke(
        {
            "mode": "patient",
            "patient_input": {
                "cpt_code": "73721",
                "zip_code": "06604",
                "insurance_type": "aetna_ppo",
                "provider_type": "hospital",
                "urgency": "routine",
                "deductible_status": "partially_met",
            },
            "messages": [],
        }
    )
    ce = patient_result.get("cost_estimate", {})
    print(f"  OOP range: ${ce.get('oop_low', 0):,.0f} - ${ce.get('oop_high', 0):,.0f}")
    print(f"  Prior auth: {patient_result.get('benefits', {}).get('prior_auth_required', '?')}")
    print()

    print("=== Hospital mode test ===")
    hospital_result = app.invoke(
        {
            "mode": "hospital",
            "hospital_input": {
                "cpt_code": "73721",
                "icd_code": "M17.11",
                "payer": "aetna_ppo",
                "clinical_note": "Patient presents with right knee pain for 3 months.",
            },
            "messages": [],
        }
    )
    ds = hospital_result.get("denial_score", {})
    print(f"  Denial risk: {ds.get('risk_pct', 0):.0%} - {ds.get('status', '?')}")
    print(f"  NCCI valid: {hospital_result.get('ncci_result', {}).get('valid', '?')}")
    print(f"  Fixes: {len(hospital_result.get('fix_list', []))}")
    print()

    print("=== Hospital mode re-eval test ===")
    hospital_reeval = app.invoke(
        {
            "mode": "hospital",
            "hospital_input": {
                "cpt_code": "73721",
                "icd_code": "M17.11",
                "payer": "aetna_ppo",
                "clinical_note": "Patient presents with right knee pain for 3 months.",
            },
            "reeval": True,
            "messages": [],
        }
    )
    ds2 = hospital_reeval.get("denial_score", {})
    print(f"  Denial risk after fix: {ds2.get('risk_pct', 0):.0%} - {ds2.get('status', '?')}")
    print()

    print("All smoke tests passed")
