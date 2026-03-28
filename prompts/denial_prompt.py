"""
Denial analysis prompt helpers.

Claude must not generate risk percentages.
Risk values are deterministic and computed in code from denial_rules.json.
"""

from __future__ import annotations

import json
from typing import Any


def build_note_analysis_prompt(
    clinical_note: str,
    cpt_code: str,
    icd_code: str,
    payer: str,
    prior_auth_required: bool,
) -> str:
    return f"""You are a medical billing compliance analyst.

Hard constraints:
- Do not generate denial percentages or risk scores.
- Analyze only documentation quality and denial exposure factors.
- Output plain text only.

Case details:
- CPT: {cpt_code}
- ICD-10: {icd_code}
- Payer: {payer}
- Prior authorization required: {"Yes" if prior_auth_required else "No"}

Clinical note:
{clinical_note}

Return:
1) Whether documentation supports medical necessity.
2) Missing elements that could trigger denial.
3) Prior authorization reminder when required.
"""


def build_fix_list_prompt(risk_factors: list[dict], cpt_code: str, payer: str) -> str:
    factors_text = "\n".join(
        f"- {rf.get('factor_key', 'unknown')}: {rf.get('description', '')}"
        for rf in risk_factors
    )

    return f"""You are a medical billing compliance analyst.

Hard constraints:
- Do not generate denial percentages.
- Return valid JSON only.
- JSON must be an object with key `fix_list`.
- `fix_list` is an array of objects with keys:
  - issue (string)
  - action (string)
  - risk_reduction (number between 0 and 1)

Context:
- CPT: {cpt_code}
- Payer: {payer}
- Risk factors:
{factors_text}

Write specific, actionable fixes. Include concrete steps where possible.
"""


def get_denial_response_config() -> dict:
    """Primary structured output config for Anthropic-style responses API usage.

    Callers should attempt this config first and fallback to strict JSON parsing.
    """
    return {
        "output_version": "responses/v1",
        "max_tokens": 1000,
        "temperature": 0,
    }


def parse_fix_list_response(raw_text: str) -> list[dict[str, Any]]:
    """Parse strict JSON output and normalize required fix_list shape."""
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Fix list response is not valid JSON") from exc

    fix_list = payload.get("fix_list") if isinstance(payload, dict) else None
    if not isinstance(fix_list, list):
        raise ValueError("Fix list response must contain a list under 'fix_list'")

    normalized: list[dict[str, Any]] = []
    for item in fix_list:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "issue": str(item.get("issue", "")).strip(),
                "action": str(item.get("action", "")).strip(),
                "risk_reduction": float(item.get("risk_reduction", 0.0)),
            }
        )

    return normalized
