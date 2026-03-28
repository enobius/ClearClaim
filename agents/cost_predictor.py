"""
Cost Predictor Agent — STUB
============================
P2 replaces this file.

Expected contract:
  READS:  state["patient_input"] → {cpt_code, zip_code, insurance_type, provider_type}
          state["mode"]
  WRITES: state["cms_rates"]      → {providers, min_rate, max_rate}
          state["fee_schedule"]    → {medicare_rate, facility_fee, non_facility_fee,
                                      commercial_estimate_low/mid/high}
          state["cost_estimate"]   → {total_low, total_high, oop_low, oop_high,
                                      insurance_low, insurance_high, explanation, savings_tips}
          state["messages"]

Data files used:
  - data/pricing_data.json   (CMS provider rates)
  - data/fee_schedule.json   (Medicare fee schedule + commercial multipliers)

Claude API call:
  - Prompt in prompts/cost_prompt.py
  - Takes real numbers, writes plain-English explanation + savings tips
  - Claude NEVER generates a number — only explains numbers from JSON lookups
"""


def cost_predictor(state: dict) -> dict:
    # STUB — hardcoded Knee MRI demo data
    return {
        "cms_rates": {
            "providers": [
                {"provider_name": "Connecticut Advanced Imaging", "provider_city": "Bridgeport",
                 "avg_submitted_chrg_amt": 1842.0, "avg_medicare_allowed_amt": 466.30},
                {"provider_name": "St. Vincent's Medical Center", "provider_city": "Bridgeport",
                 "avg_submitted_chrg_amt": 2310.0, "avg_medicare_allowed_amt": 512.47},
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
            "explanation": (
                "Your Knee MRI in Connecticut will cost around $886 at the mid-range, "
                "based on CMS provider payment data. Connecticut Advanced Imaging (Bridgeport) "
                "charges $1,842 submitted but Medicare allows $466 — commercial insurers typically "
                "pay 1.6-2.2x that rate. With $180 left on your deductible and 20% coinsurance, "
                "your out-of-pocket is approximately $321."
            ),
            "savings_tips": [
                "Ask for an outpatient imaging center instead of a hospital radiology department — same quality, up to 40% cheaper.",
                "Get prior authorization before booking to avoid full out-of-network billing if your insurer denies the claim.",
                "If you have other medical expenses planned this year, scheduling now helps you meet your deductible sooner.",
            ],
        },
        "messages": [{"role": "system", "content": "Cost predictor: returned demo data (STUB)."}],
    }
