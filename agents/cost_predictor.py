"""
Cost Predictor Agent — Person 2
=================================
READS:  state["patient_input"] → {cpt_code, zip_code, insurance_type, provider_type}
        state["benefits"]      → {deductible_remaining, coinsurance, prior_auth_required}
WRITES: state["cms_rates"]     → {providers, min_rate, max_rate}
        state["fee_schedule"]  → {medicare_rate, facility_fee, non_facility_fee,
                                   commercial_estimate_low/mid/high}
        state["cost_estimate"] → {total_low, total_high, oop_low, oop_high,
                                   insurance_low, insurance_high, explanation, savings_tips}
        state["messages"]
"""

import json
import os
from dotenv import load_dotenv

load_dotenv()


# ── Data loaders ──────────────────────────────────────────────────────────────

def load_pricing_data():
    path = os.path.join(os.path.dirname(__file__), "../data/pricing_data.json")
    with open(path, "r") as f:
        return json.load(f)

def load_fee_schedule():
    path = os.path.join(os.path.dirname(__file__), "../data/fee_schedule.json")
    with open(path, "r") as f:
        return json.load(f)


# ── CPT → scenario key mapper ─────────────────────────────────────────────────

CPT_TO_SCENARIO = {
    "73721": "knee_mri",
    "71260": "chest_ct",
    "29827": "rotator_cuff_repair",
    "45380": "colonoscopy_biopsy",
    "93306": "echocardiogram",
}

# zip code prefix → state code
ZIP_TO_STATE = {
    "06": "CT",
    "07": "CT",
    "75": "TX",
    "77": "TX",
    "78": "TX",
    "90": "CA",
    "91": "CA",
    "92": "CA",
    "94": "CA",
    "33": "FL",
    "32": "FL",
    "10": "NY",
    "11": "NY",
}

def zip_to_state(zip_code: str) -> str:
    prefix = str(zip_code)[:2]
    return ZIP_TO_STATE.get(prefix, "CT")  # default CT


# ── CMS rates lookup ──────────────────────────────────────────────────────────

def get_cms_rates(cpt_code: str, zip_code: str) -> dict:
    pricing = load_pricing_data()
    state = zip_to_state(zip_code)
    scenarios = pricing.get("scenarios", {})
    scenario_key = CPT_TO_SCENARIO.get(cpt_code)

    if not scenario_key or scenario_key not in scenarios:
        return {"providers": [], "min_rate": 0.0, "max_rate": 0.0, "state": state}

    scenario = scenarios[scenario_key]
    providers = scenario.get("providers", [])

    # Filter by state if possible
    state_providers = [p for p in providers if p.get("provider_state") == state]
    if not state_providers:
        state_providers = providers  # fallback to all providers

    rates = [p["avg_medicare_allowed_amt"] for p in state_providers]
    return {
        "providers": state_providers,
        "min_rate": min(rates) if rates else 0.0,
        "max_rate": max(rates) if rates else 0.0,
        "state": state
    }


# ── Fee schedule lookup ───────────────────────────────────────────────────────

def get_fee_schedule(cpt_code: str, zip_code: str, insurance_type: str) -> dict:
    schedule = load_fee_schedule()
    state = zip_to_state(zip_code)
    fee_data = schedule.get("fee_schedule", {})
    multipliers = schedule.get("commercial_multipliers", {})

    if cpt_code not in fee_data:
        return {
            "medicare_rate": 0.0,
            "facility_fee": 0.0,
            "non_facility_fee": 0.0,
            "commercial_estimate_low": 0.0,
            "commercial_estimate_mid": 0.0,
            "commercial_estimate_high": 0.0,
        }

    cpt_fees = fee_data[cpt_code]
    state_fees = cpt_fees.get("by_state", {}).get(state, {})
    medicare_rate = state_fees.get("fee", cpt_fees.get("national_payment_amount", 0.0))
    facility_fee = state_fees.get("facility_fee", 0.0) or 0.0
    non_facility_fee = state_fees.get("non_facility_fee", 0.0) or 0.0

    # Get commercial multipliers for this payer
    payer_key = insurance_type.replace("_ppo", "").replace("_hmo", "")
    payer_multipliers = multipliers.get(insurance_type,
                        multipliers.get(payer_key,
                        {"low": 1.6, "mid": 1.9, "high": 2.2}))

    return {
        "medicare_rate": medicare_rate,
        "facility_fee": facility_fee,
        "non_facility_fee": non_facility_fee,
        "commercial_estimate_low":  round(medicare_rate * payer_multipliers["low"], 2),
        "commercial_estimate_mid":  round(medicare_rate * payer_multipliers["mid"], 2),
        "commercial_estimate_high": round(medicare_rate * payer_multipliers["high"], 2),
    }


# ── Cost estimate calculator ──────────────────────────────────────────────────

def compute_estimate(fee_schedule: dict, benefits: dict) -> dict:
    """
    Compute out-of-pocket and insurance split from fee schedule + benefits.
    Claude NEVER generates these numbers — pure deterministic math.
    """
    total_low  = fee_schedule["commercial_estimate_low"]
    total_high = fee_schedule["commercial_estimate_high"]

    deductible_remaining = float(benefits.get("deductible_remaining", 0.0))
    coinsurance          = float(benefits.get("coinsurance", 0.20))

    def calc_oop(total: float) -> float:
        oop = min(deductible_remaining, total)
        remainder = total - oop
        oop += remainder * coinsurance
        return round(oop, 2)

    oop_low  = calc_oop(total_low)
    oop_high = calc_oop(total_high)

    return {
        "total_low":      round(total_low, 2),
        "total_high":     round(total_high, 2),
        "oop_low":        oop_low,
        "oop_high":       oop_high,
        "insurance_low":  round(total_low - oop_low, 2),
        "insurance_high": round(total_high - oop_high, 2),
    }


# ── Claude API call ───────────────────────────────────────────────────────────

def call_claude(prompt: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "STUB: Claude explanation unavailable — API key not set."
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
        return f"Explanation unavailable: {str(e)}"


# ── Main Agent Function ───────────────────────────────────────────────────────

def cost_predictor(state: dict) -> dict:
    """
    Main cost predictor agent — called by LangGraph.
    Matches P1's contract exactly.
    """
    from prompts.cost_prompt import build_cost_prompt

    # ── Read inputs ──
    patient_input  = state.get("patient_input", {})
    cpt_code       = str(patient_input.get("cpt_code", "73721")).strip()
    zip_code       = str(patient_input.get("zip_code", "06604")).strip()
    insurance_type = str(patient_input.get("insurance_type", "aetna_ppo")).strip()
    provider_type  = str(patient_input.get("provider_type", "outpatient")).strip()
    benefits       = state.get("benefits", {})

    # ── Step 1: CMS rates lookup ──
    cms_rates = get_cms_rates(cpt_code, zip_code)

    # ── Step 2: Fee schedule lookup ──
    fee_schedule = get_fee_schedule(cpt_code, zip_code, insurance_type)

    # ── Step 3: Compute estimate ──
    estimate = compute_estimate(fee_schedule, benefits)

    # ── Step 4: Claude explanation ──
    pricing = load_pricing_data()
    scenario_key = CPT_TO_SCENARIO.get(cpt_code, "")
    scenario = pricing.get("scenarios", {}).get(scenario_key, {})
    procedure_name = scenario.get("description", f"CPT {cpt_code}")

    state_code = zip_to_state(zip_code)
    provider_name = cms_rates["providers"][0]["provider_name"] if cms_rates["providers"] else ""

    prompt = build_cost_prompt(
        procedure_name=procedure_name,
        cpt_code=cpt_code,
        state_name=state_code,
        medicare_rate=fee_schedule["medicare_rate"],
        commercial_estimate_low=fee_schedule["commercial_estimate_low"],
        commercial_estimate_mid=fee_schedule["commercial_estimate_mid"],
        commercial_estimate_high=fee_schedule["commercial_estimate_high"],
        deductible_remaining=float(benefits.get("deductible_remaining", 0.0)),
        coinsurance=float(benefits.get("coinsurance", 0.20)),
        oop_low=estimate["oop_low"],
        oop_high=estimate["oop_high"],
        prior_auth_required=bool(benefits.get("prior_auth_required", False)),
        provider_name=provider_name,
        submitted_charge=cms_rates["providers"][0]["avg_submitted_chrg_amt"] if cms_rates["providers"] else 0.0,
    )

    claude_response = call_claude(prompt)

    # ── Parse Claude response into explanation + savings_tips ──
    explanation = claude_response
    savings_tips = []

    if "SAVINGS_TIPS:" in claude_response:
        parts = claude_response.split("SAVINGS_TIPS:")
        explanation = parts[0].replace("EXPLANATION:", "").strip()
        tips_raw = parts[1].strip().split("\n")
        savings_tips = [t.strip().lstrip("0123456789.-) ") for t in tips_raw if t.strip()]

    estimate["explanation"]  = explanation
    estimate["savings_tips"] = savings_tips

    return {
        "cms_rates":    cms_rates,
        "fee_schedule": fee_schedule,
        "cost_estimate": estimate,
        "messages": [{"role": "system", "content": f"Cost predictor: {procedure_name} estimate complete."}]
    }
