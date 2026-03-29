"""
Cost Predictor Agent
====================
Adapter layer around Part 2 compute logic while preserving main graph/UI contract.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

from part2.Data.compute import compute_estimate
from part2.Data.data import PROCEDURES
from prompts.cost_prompt import build_cost_prompt


ROOT = Path(__file__).resolve().parent.parent
PRICING_DATA_PATH = ROOT / "data" / "pricing_data.json"
FEE_SCHEDULE_PATH = ROOT / "data" / "fee_schedule.json"

ZIP_PREFIX_TO_STATE = {
    "06": ("Connecticut", "CT"),
    "75": ("Texas", "TX"),
    "76": ("Texas", "TX"),
    "77": ("Texas", "TX"),
    "90": ("California", "CA"),
    "91": ("California", "CA"),
    "92": ("California", "CA"),
    "93": ("California", "CA"),
    "94": ("California", "CA"),
    "10": ("New York", "NY"),
    "11": ("New York", "NY"),
    "32": ("Florida", "FL"),
    "33": ("Florida", "FL"),
}

INSURANCE_TO_P2 = {
    "aetna_ppo": "PPO",
    "bcbs_ppo": "PPO_BCBS",
    "unitedhealthcare_hmo": "HMO",
}

PROVIDER_TO_P2 = {
    "hospital": "Hospital",
    "imaging_center": "Private Clinic",
    "asc": "Private Clinic",
}

URGENCY_TO_P2 = {
    "routine": "Routine",
    "urgent": "Urgent",
    "emergency": "Emergency",
}

CPT_TO_PROCEDURE = {details["cpt"]: name for name, details in PROCEDURES.items()}


@lru_cache(maxsize=1)
def _load_pricing_data() -> dict:
    with PRICING_DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_fee_schedule() -> dict:
    with FEE_SCHEDULE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _infer_state(zip_code: str) -> tuple[str, str]:
    prefix = str(zip_code).strip()[:2]
    return ZIP_PREFIX_TO_STATE.get(prefix, ("Connecticut", "CT"))


def _find_scenario_by_cpt(cpt_code: str) -> dict:
    scenarios = _load_pricing_data().get("scenarios", {})
    for scenario in scenarios.values():
        if scenario.get("cpt_code") == cpt_code:
            return scenario
    return {}


def _build_cms_rates(cpt_code: str, state_abbrev: str) -> dict:
    scenario = _find_scenario_by_cpt(cpt_code)
    providers = [
        provider
        for provider in scenario.get("providers", [])
        if provider.get("provider_state") == state_abbrev
    ]

    if not providers:
        providers = scenario.get("providers", [])

    allowed_amounts = [float(p.get("avg_medicare_allowed_amt", 0.0)) for p in providers]
    min_rate = min(allowed_amounts) if allowed_amounts else 0.0
    max_rate = max(allowed_amounts) if allowed_amounts else 0.0

    return {
        "providers": providers,
        "min_rate": min_rate,
        "max_rate": max_rate,
    }


def _build_fee_schedule(cpt_code: str, state_abbrev: str, insurance_type: str) -> dict:
    payload = _load_fee_schedule()
    cpt_block = payload.get("fee_schedule", {}).get(cpt_code, {})
    state_block = cpt_block.get("by_state", {}).get(state_abbrev, {})

    medicare_rate = float(state_block.get("fee", cpt_block.get("national_payment_amount", 0.0)))
    facility_fee = float(state_block.get("facility_fee", 0.0) or 0.0)
    non_facility_fee = float(state_block.get("non_facility_fee", medicare_rate) or medicare_rate)

    multipliers = payload.get("commercial_multipliers", {}).get(
        insurance_type,
        payload.get("commercial_multipliers", {}).get("aetna_ppo", {"low": 1.6, "mid": 1.9, "high": 2.2}),
    )

    return {
        "medicare_rate": medicare_rate,
        "facility_fee": facility_fee,
        "non_facility_fee": non_facility_fee,
        "commercial_estimate_low": round(medicare_rate * float(multipliers.get("low", 1.6)), 2),
        "commercial_estimate_mid": round(medicare_rate * float(multipliers.get("mid", 1.9)), 2),
        "commercial_estimate_high": round(medicare_rate * float(multipliers.get("high", 2.2)), 2),
    }


def _call_claude_explainer(prompt: str) -> tuple[str, list[str]]:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return (
            "Estimate generated from deterministic pricing and benefits data. "
            "Set ANTHROPIC_API_KEY to enable narrative explanation.",
            [
                "Compare imaging center and hospital options in-network.",
                "Confirm prior authorization before scheduling.",
                "Ask for an itemized estimate before the visit.",
            ],
        )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
    except Exception as exc:
        return (
            f"Explanation unavailable from Claude API: {exc}",
            [
                "Compare imaging center and hospital options in-network.",
                "Confirm prior authorization before scheduling.",
                "Ask for an itemized estimate before the visit.",
            ],
        )

    explanation = text
    tips: list[str] = []

    marker = "SAVINGS_TIPS:"
    if marker in text:
        before, after = text.split(marker, 1)
        explanation = before.replace("EXPLANATION:", "").strip()
        for line in after.splitlines():
            cleaned = line.strip().lstrip("- ").strip()
            if cleaned:
                tips.append(cleaned)

    if not tips:
        tips = [
            "Compare imaging center and hospital options in-network.",
            "Confirm prior authorization before scheduling.",
            "Ask for an itemized estimate before the visit.",
        ]

    return explanation, tips[:3]


def _normalize_numeric_token(token: str) -> str:
    token = token.strip().replace(",", "")
    if not token:
        return ""
    if token.endswith("%"):
        base = token[:-1]
        try:
            val = float(base)
            if val.is_integer():
                return f"{int(val)}%"
            return f"{val}%"
        except ValueError:
            return token
    try:
        val = float(token)
        if val.is_integer():
            return str(int(val))
        return f"{val:.6f}".rstrip("0").rstrip(".")
    except ValueError:
        return token


def _extract_numeric_tokens(text: str) -> set[str]:
    matches = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?%?", text or "")
    return {_normalize_numeric_token(m) for m in matches if m.strip()}


def _allowed_numeric_tokens(
    cpt_code: str,
    medicare_rate: float,
    commercial_estimate_low: float,
    commercial_estimate_mid: float,
    commercial_estimate_high: float,
    deductible_remaining: float,
    coinsurance: float,
    oop_low: float,
    oop_high: float,
    submitted_charge: float,
) -> set[str]:
    allowed = {_normalize_numeric_token(str(cpt_code))}

    def add_num(value: float) -> None:
        val = float(value)
        allowed.add(_normalize_numeric_token(str(val)))
        allowed.add(_normalize_numeric_token(f"{val:.2f}"))
        allowed.add(_normalize_numeric_token(str(int(round(val)))))

    for value in (
        medicare_rate,
        commercial_estimate_low,
        commercial_estimate_mid,
        commercial_estimate_high,
        deductible_remaining,
        oop_low,
        oop_high,
        submitted_charge,
    ):
        add_num(value)

    pct = float(coinsurance) * 100
    allowed.add(_normalize_numeric_token(f"{pct}%"))
    allowed.add(_normalize_numeric_token(f"{int(round(pct))}%"))
    return allowed


def _guard_explanation_numbers(explanation: str, allowed_tokens: set[str]) -> tuple[str, bool]:
    observed = _extract_numeric_tokens(explanation)
    for token in observed:
        if token in {"1", "2", "3", "1%", "2%", "3%"}:
            continue
        if token not in allowed_tokens:
            return (
                "Estimate generated from deterministic pricing and benefits data. "
                "Narrative explanation was replaced to enforce numeric integrity.",
                True,
            )
    return explanation, False


def cost_predictor(state: dict) -> dict:
    patient_input = state.get("patient_input", {})
    benefits = state.get("benefits", {})

    cpt_code = str(patient_input.get("cpt_code", "73721")).strip() or "73721"
    zip_code = str(patient_input.get("zip_code", "06604")).strip() or "06604"
    insurance_type = str(patient_input.get("insurance_type", "aetna_ppo")).strip() or "aetna_ppo"
    provider_type = str(patient_input.get("provider_type", "hospital")).strip() or "hospital"
    urgency = str(patient_input.get("urgency", "routine")).strip() or "routine"

    procedure_name = CPT_TO_PROCEDURE.get(cpt_code, "Knee MRI")
    state_name, state_abbrev = _infer_state(zip_code)
    provider_for_p2 = PROVIDER_TO_P2.get(provider_type, "Hospital")
    insurance_for_p2 = INSURANCE_TO_P2.get(insurance_type, "PPO")
    urgency_for_p2 = URGENCY_TO_P2.get(urgency, "Routine")

    # Base compute logic preserved from Part 2.
    computed = compute_estimate(
        procedure=procedure_name,
        location=state_name,
        provider=provider_for_p2,
        insurance_plan=insurance_for_p2,
        urgency=urgency_for_p2,
    )

    cms_rates = _build_cms_rates(cpt_code, state_abbrev)
    fee_schedule = _build_fee_schedule(cpt_code, state_abbrev, insurance_type)
    submitted_charge = float((cms_rates.get("providers") or [{}])[0].get("avg_submitted_chrg_amt", 0.0))

    prompt = build_cost_prompt(
        procedure_name=procedure_name,
        cpt_code=cpt_code,
        state_name=state_name,
        medicare_rate=float(fee_schedule["medicare_rate"]),
        commercial_estimate_low=float(fee_schedule["commercial_estimate_low"]),
        commercial_estimate_mid=float(fee_schedule["commercial_estimate_mid"]),
        commercial_estimate_high=float(fee_schedule["commercial_estimate_high"]),
        deductible_remaining=float(benefits.get("deductible_remaining", computed.get("remaining_deductible", 0.0))),
        coinsurance=float(benefits.get("coinsurance", 0.20)),
        oop_low=float(computed.get("oop_low", 0.0)),
        oop_high=float(computed.get("oop_high", 0.0)),
        prior_auth_required=bool(benefits.get("prior_auth_required", False)),
        provider_name=(cms_rates.get("providers") or [{}])[0].get("provider_name", ""),
        submitted_charge=submitted_charge,
    )

    explanation, savings_tips = _call_claude_explainer(prompt)
    allowed_tokens = _allowed_numeric_tokens(
        cpt_code=cpt_code,
        medicare_rate=fee_schedule["medicare_rate"],
        commercial_estimate_low=fee_schedule["commercial_estimate_low"],
        commercial_estimate_mid=fee_schedule["commercial_estimate_mid"],
        commercial_estimate_high=fee_schedule["commercial_estimate_high"],
        deductible_remaining=float(benefits.get("deductible_remaining", computed.get("remaining_deductible", 0.0))),
        coinsurance=float(benefits.get("coinsurance", 0.20)),
        oop_low=float(computed.get("oop_low", 0.0)),
        oop_high=float(computed.get("oop_high", 0.0)),
        submitted_charge=submitted_charge,
    )
    explanation, drift_detected = _guard_explanation_numbers(explanation, allowed_tokens)

    cost_estimate = {
        "total_low": float(computed.get("total_low", 0.0)),
        "total_high": float(computed.get("total_high", 0.0)),
        "oop_low": float(computed.get("oop_low", 0.0)),
        "oop_high": float(computed.get("oop_high", 0.0)),
        "insurance_low": float(computed.get("insurance_low", 0.0)),
        "insurance_high": float(computed.get("insurance_high", 0.0)),
        "explanation": explanation,
        "savings_tips": savings_tips,
    }

    messages = [
        {
            "role": "system",
            "content": f"Cost predictor: computed Part 2 estimate for CPT {cpt_code} in {state_abbrev}.",
        }
    ]
    if drift_detected:
        messages.append(
            {
                "role": "system",
                "content": "Cost predictor: explanation numeric drift detected and replaced with safe fallback.",
            }
        )

    return {
        "cms_rates": cms_rates,
        "fee_schedule": fee_schedule,
        "cost_estimate": cost_estimate,
        "messages": messages,
    }
