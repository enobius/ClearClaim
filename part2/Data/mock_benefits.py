# data/mock_benefits.py

BENEFITS = {
    "PPO": {
        "individual_deductible_remaining": 180,
        "coinsurance_in_network": 0.20,
        "prior_auth_rules": {
            "73721": {"required": True, "notes": "Prior auth required for advanced imaging (MRI/CT/PET)"},
            "71260": {"required": True, "notes": "Prior auth required for advanced imaging"},
            "29827": {"required": True, "notes": "Prior auth required for all elective surgeries"},
            "45380": {"required": False, "notes": "No prior auth for screening/diagnostic colonoscopy"},
            "93306": {"required": False, "notes": "No prior auth for echocardiogram"},
        },
    },
    "PPO_BCBS": {
        "individual_deductible_remaining": 0,
        "coinsurance_in_network": 0.20,
        "prior_auth_rules": {
            "73721": {"required": True, "notes": "Prior auth via eviCore for MRI"},
            "71260": {"required": True, "notes": "Prior auth via eviCore for CT"},
            "29827": {"required": True, "notes": "Prior auth required, clinical notes needed"},
            "45380": {"required": False, "notes": "No prior auth needed"},
            "93306": {"required": False, "notes": "No prior auth needed"},
        },
    },
    "HMO": {
        "individual_deductible_remaining": 1000,
        "coinsurance_in_network": 0.25,
        "prior_auth_rules": {
            "73721": {"required": True, "notes": "Prior auth required, must use in-network imaging center"},
            "71260": {"required": True, "notes": "Prior auth required via Optum"},
            "29827": {"required": True, "notes": "Prior auth + peer-to-peer review may be needed"},
            "45380": {"required": False, "notes": "Covered as preventive, no auth needed"},
            "93306": {"required": True, "notes": "Prior auth required for cardiac imaging in HMO"},
        },
    },
    "Medicare": {
        "individual_deductible_remaining": 226,
        "coinsurance_in_network": 0.20,
        "prior_auth_rules": {
            "73721": {"required": False, "notes": "No prior auth for Medicare MRI"},
            "71260": {"required": False, "notes": "No prior auth for Medicare CT"},
            "29827": {"required": False, "notes": "No prior auth for Medicare surgery"},
            "45380": {"required": False, "notes": "Covered as preventive"},
            "93306": {"required": False, "notes": "No prior auth for Medicare echo"},
        },
    },
    "Medicaid": {
        "individual_deductible_remaining": 0,
        "coinsurance_in_network": 0.05,
        "prior_auth_rules": {
            "73721": {"required": True, "notes": "Prior auth required for all advanced imaging"},
            "71260": {"required": True, "notes": "Prior auth required for all advanced imaging"},
            "29827": {"required": True, "notes": "Prior auth required for elective surgery"},
            "45380": {"required": False, "notes": "Covered as preventive"},
            "93306": {"required": False, "notes": "No prior auth"},
        },
    },
    "Uninsured": {
        "individual_deductible_remaining": 0,
        "coinsurance_in_network": 1.00,
        "prior_auth_rules": {},
    },
}


def get_prior_auth_required(plan_type: str, cpt_code: str) -> bool:
    plan = BENEFITS.get(plan_type, {})
    rules = plan.get("prior_auth_rules", {})
    rule = rules.get(cpt_code, {})
    return rule.get("required", False)


def get_prior_auth_note(plan_type: str, cpt_code: str) -> str:
    plan = BENEFITS.get(plan_type, {})
    rules = plan.get("prior_auth_rules", {})
    rule = rules.get(cpt_code, {})
    return rule.get("notes", "")


def get_remaining_deductible(plan_type: str) -> float:
    plan = BENEFITS.get(plan_type, {})
    return plan.get("individual_deductible_remaining", 0)


def get_coinsurance(plan_type: str) -> float:
    plan = BENEFITS.get(plan_type, {})
    return plan.get("coinsurance_in_network", 0.20)
