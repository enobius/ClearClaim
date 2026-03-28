"""
Cost explanation prompt helpers.

Claude must only explain deterministic values supplied by code.
Claude must never invent numeric prices, percentages, or ranges.
"""

from __future__ import annotations


def build_cost_prompt(
    procedure_name: str,
    cpt_code: str,
    state_name: str,
    medicare_rate: float,
    commercial_estimate_low: float,
    commercial_estimate_mid: float,
    commercial_estimate_high: float,
    deductible_remaining: float,
    coinsurance: float,
    oop_low: float,
    oop_high: float,
    prior_auth_required: bool,
    provider_name: str = "",
    submitted_charge: float = 0.0,
) -> str:
    return f"""You are a healthcare cost advisor.

Hard constraints:
- Do not generate any new numbers.
- Use only numbers listed below.
- If a value is missing, say it is unavailable.
- Output plain text only (no markdown).

Known numeric values:
- CPT: {cpt_code}
- Medicare allowed amount: ${medicare_rate:,.2f}
- Commercial estimate low: ${commercial_estimate_low:,.2f}
- Commercial estimate mid: ${commercial_estimate_mid:,.2f}
- Commercial estimate high: ${commercial_estimate_high:,.2f}
- Deductible remaining: ${deductible_remaining:,.2f}
- Coinsurance: {coinsurance:.0%}
- Out-of-pocket low: ${oop_low:,.2f}
- Out-of-pocket high: ${oop_high:,.2f}
- Submitted charge: ${submitted_charge:,.2f}

Context:
- Procedure: {procedure_name}
- Location: {state_name}
- Provider: {provider_name}
- Prior authorization required: {"Yes" if prior_auth_required else "No"}

Return exactly two sections in plain text:
EXPLANATION:
2-3 sentences explaining what the patient is likely to pay and why.

SAVINGS_TIPS:
3 concise actionable tips.
"""


def get_cost_response_config() -> dict:
    """Optional model call configuration for structured, deterministic handling."""
    return {
        "max_tokens": 1000,
        "temperature": 0,
        "metadata": {"deterministic_numbers_only": True},
    }
