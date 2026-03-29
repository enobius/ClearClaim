# data/mock_benefits.py
# ─────────────────────────────────────────────────────────────────────────────
# MOCKED — simulates Availity / Change Healthcare real-time eligibility API
# In production: 270/271 EDI eligibility transactions via Availity or
# Change Healthcare. Requires payer API integration.
# ─────────────────────────────────────────────────────────────────────────────

BENEFITS = {
    "PPO": {
        "payer_name":                 "Aetna",
        "plan_name":                  "Aetna Open Access PPO",
        "individual_deductible":      500,
        "individual_deductible_met":  320,
        "individual_deductible_remaining": 180,
        "out_of_pocket_max":          6000,
        "out_of_pocket_spent":        485,
        "coinsurance_in_network":     0.20,
        "coinsurance_out_of_network": 0.40,
        "copay_specialist":           40,
        "copay_primary":              25,
        "prior_auth_rules": {
            "73721": {"required": True,  "notes": "Prior auth required for advanced imaging (MRI/CT/PET)"},
            "71260": {"required": True,  "notes": "Prior auth required for advanced imaging"},
            "29827": {"required": True,  "notes": "Prior auth required for all elective surgeries"},
            "45380": {"required": False, "notes": "No prior auth for screening/diagnostic colonoscopy"},
            "93306": {"required": False, "notes": "No prior auth for echocardiogram"},
        },
    },

    "PPO_BCBS": {
        "payer_name":                 "Blue Cross Blue Shield",
        "plan_name":                  "Blue Preferred PPO",
        "individual_deductible":      750,
        "individual_deductible_met":  750,
        "individual_deductible_remaining": 0,
        "out_of_pocket_max":          7500,
        "out_of_pocket_spent":        1250,
        "coinsurance_in_network":     0.20,
        "coinsurance_out_of_network": 0.40,
        "copay_specialist":           50,
        "copay_primary":              30,
        "prior_auth_rules": {
            "73721": {"required": True,  "notes": "Prior auth via eviCore for MRI"},
            "71260": {"required": True,  "notes": "Prior auth via eviCore for CT"},
            "29827": {"required": True,  "notes": "Prior auth required, clinical notes needed"},
            "45380": {"required": False, "notes": "No prior auth needed"},
            "93306": {"required": False, "notes": "No prior auth needed"},
        },
    },

    "HMO": {
        "payer_name":                 "UnitedHealthcare",
        "plan_name":                  "UHC Choice Plus HMO",
        "individual_deductible":      1000,
        "individual_deductible_met":  0,
        "individual_deductible_remaining": 1000,
        "out_of_pocket_max":          8500,
        "out_of_pocket_spent":        0,
        "coinsurance_in_network":     0.25,
        "coinsurance_out_of_network": 0.50,
        "copay_specialist":           60,
        "copay_primary":              30,
        "prior_auth_rules": {
            "73721": {"required": True,  "notes": "Prior auth required, must use in-network imaging center"},
            "71260": {"required": True,  "notes": "Prior auth required via Optum"},
            "29827": {"required": True,  "notes": "Prior auth + peer-to-peer review may be needed"},
            "45380": {"required": False, "notes": "Covered as preventive, no auth needed"},
            "93306": {"required": True,  "notes": "Prior auth required for cardiac imaging in HMO"},
        },
    },

    "Medicare": {
        "payer_name":                 "Medicare",
        "plan_name":                  "Medicare Part B",
        "individual_deductible":      226,
        "individual_deductible_met":  0,
        "individual_deductible_remaining": 226,
        "out_of_pocket_max":          None,
        "out_of_pocket_spent":        0,
        "coinsurance_in_network":     0.20,
        "coinsurance_out_of_network": 0.20,
        "copay_specialist":           0,
        "copay_primary":              0,
        "prior_auth_rules": {
            "73721": {"required": False, "notes": "No prior auth for Medicare MRI"},
            "71260": {"required": False, "notes": "No prior auth for Medicare CT"},
            "29827": {"required": False, "notes": "No prior auth for Medicare surgery"},
            "45380": {"required": False, "notes": "Covered as preventive"},
            "93306": {"required": False, "notes": "No prior auth for Medicare echo"},
        },
    },

    "Medicaid": {
        "payer_name":                 "Medicaid",
        "plan_name":                  "State Medicaid",
        "individual_deductible":      0,
        "individual_deductible_met":  0,
        "individual_deductible_remaining": 0,
        "out_of_pocket_max":          None,
        "out_of_pocket_spent":        0,
        "coinsurance_in_network":     0.05,
        "coinsurance_out_of_network": 0.05,
        "copay_specialist":           3,
        "copay_primary":              2,
        "prior_auth_rules": {
            "73721": {"required": True,  "notes": "Prior auth required for all advanced imaging"},
            "71260": {"required": True,  "notes": "Prior auth required for all advanced imaging"},
            "29827": {"required": True,  "notes": "Prior auth required for elective surgery"},
            "45380": {"required": False, "notes": "Covered as preventive"},
            "93306": {"required": False, "notes": "No prior auth"},
        },
    },

    "Uninsured": {
        "payer_name":                 "Self-pay",
        "plan_name":                  "No insurance",
        "individual_deductible":      0,
        "individual_deductible_met":  0,
        "individual_deductible_remaining": 0,
        "out_of_pocket_max":          None,
        "out_of_pocket_spent":        0,
        "coinsurance_in_network":     1.00,
        "coinsurance_out_of_network": 1.00,
        "copay_specialist":           0,
        "copay_primary":              0,
        "prior_auth_rules": {},
    },
}


def get_prior_auth_required(plan_type: str, cpt_code: str) -> bool:
    """Check if prior auth is required for a given plan + CPT code."""
    plan = BENEFITS.get(plan_type, {})
    rules = plan.get("prior_auth_rules", {})
    rule = rules.get(cpt_code, {})
    return rule.get("required", False)


def get_prior_auth_note(plan_type: str, cpt_code: str) -> str:
    """Get the prior auth note for a given plan + CPT code."""
    plan = BENEFITS.get(plan_type, {})
    rules = plan.get("prior_auth_rules", {})
    rule = rules.get(cpt_code, {})
    return rule.get("notes", "")


def get_remaining_deductible(plan_type: str) -> float:
    """Get the remaining deductible for a given plan type."""
    plan = BENEFITS.get(plan_type, {})
    return plan.get("individual_deductible_remaining", 0)


def get_coinsurance(plan_type: str) -> float:
    """Get the in-network coinsurance rate (patient share) for a plan."""
    plan = BENEFITS.get(plan_type, {})
    return plan.get("coinsurance_in_network", 0.20)
