# data/compute.py
import json
import os
from .data import PROCEDURES, PROVIDER_MULTIPLIERS, URGENCY_MULTIPLIERS
from .mock_benefits import get_remaining_deductible, get_coinsurance

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
with open(os.path.join(_BASE_DIR, "fee_schedule.json"), "r", encoding="utf-8") as f:
    _FEE_DATA = json.load(f)

FEE_SCHEDULE = {
    cpt: {state: info["fee"] for state, info in data["by_state"].items()}
    for cpt, data in _FEE_DATA["fee_schedule"].items()
}

COMMERCIAL_MULTIPLIERS = {
    "PPO": _FEE_DATA["commercial_multipliers"]["aetna_ppo"],
    "PPO_BCBS": _FEE_DATA["commercial_multipliers"]["bcbs_ppo"],
    "HMO": _FEE_DATA["commercial_multipliers"]["unitedhealthcare"],
    "Medicare": {"low": 1.0, "mid": 1.0, "high": 1.0},
    "Medicaid": {"low": 0.7, "mid": 0.8, "high": 0.9},
    "Uninsured": {"low": 2.5, "mid": 3.5, "high": 5.0},
}

STATE_TO_ABBREV = {
    "Connecticut": "CT",
    "Texas": "TX",
    "California": "CA",
    "Florida": "FL",
    "New York": "NY",
}


def compute_estimate(procedure, location, provider, insurance_plan, urgency):
    proc = PROCEDURES.get(procedure)
    if not proc:
        raise ValueError(f"Unknown procedure: {procedure}")

    cpt = proc["cpt"]
    price_low = proc["low"]
    price_high = proc["high"]

    state_abbrev = STATE_TO_ABBREV.get(location)
    state_fees = FEE_SCHEDULE.get(cpt, {})
    state_fee = state_fees.get(state_abbrev)
    if state_fee is None:
        state_fee = _FEE_DATA["fee_schedule"][cpt]["national_payment_amount"]

    provider_mult = PROVIDER_MULTIPLIERS.get(provider, 1.0)
    urgency_mult = URGENCY_MULTIPLIERS.get(urgency, 1.0)

    total_low = round(price_low * provider_mult * urgency_mult)
    total_high = round(price_high * provider_mult * urgency_mult)

    mults = COMMERCIAL_MULTIPLIERS.get(insurance_plan, {"low": 1.0, "mid": 1.5, "high": 2.0})
    insurance_base_low = round(state_fee * mults["low"] * provider_mult)
    insurance_base_high = round(state_fee * mults["high"] * provider_mult)

    remaining_deductible = get_remaining_deductible(insurance_plan)
    coinsurance = get_coinsurance(insurance_plan)

    def calc_oop(total, insurance_base):
        if insurance_plan == "Uninsured":
            return total, 0

        deduct_paid = min(total, remaining_deductible)
        after_deduct = max(0, insurance_base - remaining_deductible)
        patient_share = round(after_deduct * coinsurance)
        insurance_share = round(after_deduct * (1 - coinsurance))
        oop = deduct_paid + patient_share
        return round(oop), round(insurance_share)

    oop_low, insurance_low = calc_oop(total_low, insurance_base_low)
    oop_high, insurance_high = calc_oop(total_high, insurance_base_high)

    return {
        "procedure": procedure,
        "cpt": cpt,
        "location": location,
        "insurance_plan": insurance_plan,
        "total_low": total_low,
        "total_high": total_high,
        "insurance_low": insurance_low,
        "insurance_high": insurance_high,
        "oop_low": oop_low,
        "oop_high": oop_high,
        "remaining_deductible": remaining_deductible,
        "state_medicare_fee": round(state_fee),
    }
