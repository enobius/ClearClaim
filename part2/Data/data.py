# data/data.py
# ─────────────────────────────────────────────────────────────────────────────
# REAL DATA — sourced from CMS Medicare Physician & Other Practitioners 2022
# source: https://data.cms.gov/provider-summary-by-type-of-service/
#         medicare-physician-other-practitioners/
#         medicare-physician-other-practitioners-by-provider-and-service
#
# price_low  = avg_medicare_allowed_amt  (what Medicare considers reasonable)
# price_high = avg_submitted_chrg_amt    (what providers actually bill)
# cpt        = CMS procedure code
# ─────────────────────────────────────────────────────────────────────────────

PROCEDURES = {
    "Knee MRI":                    {"cpt": "73721", "low": 466,  "high": 2785},
    "CT Scan (chest)":             {"cpt": "71260", "low": 342,  "high": 4150},
    "Rotator Cuff Repair":         {"cpt": "29827", "low": 1876, "high": 14200},
    "Colonoscopy with Biopsy":     {"cpt": "45380", "low": 511,  "high": 3560},
    "Echocardiogram":              {"cpt": "93306", "low": 396,  "high": 3200},
}

# ─────────────────────────────────────────────────────────────────────────────
# LOCATION MULTIPLIERS
# Derived from avg_medicare_allowed_amt per state in the CMS dataset.
# Florida = 1.0 baseline. Additional states padded with KFF index estimates.
# ─────────────────────────────────────────────────────────────────────────────

LOCATION_MULTIPLIERS = {
    "California":   3.63,   # CA avg $1,914 — highest in dataset (surgical hub effect)
    "Connecticut":  0.93,   # CT avg $492
    "Florida":      1.00,   # FL avg $527 — baseline
    "New York":     0.78,   # NY avg $413
    "Texas":        0.67,   # TX avg $354

    # Supplemented from KFF health spending index (normalized to FL=1.0)
    "Massachusetts": 1.25,
    "New Jersey":    1.15,
    "Illinois":      1.05,
    "Pennsylvania":  1.02,
    "Georgia":       0.88,
}

# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER MULTIPLIERS
# HARDCODED — industry-standard cost differentials by facility type
# ─────────────────────────────────────────────────────────────────────────────

PROVIDER_MULTIPLIERS = {
    "Hospital":       1.00,   # baseline
    "Private Clinic": 0.75,   # lower overhead, no ER costs
    "Urgent Care":    0.85,   # walk-in, no appointment
    "Emergency Room": 1.60,   # 24/7 staffing + facility fee
}

# ─────────────────────────────────────────────────────────────────────────────
# URGENCY MULTIPLIERS
# HARDCODED — reflects after-hours and priority scheduling fees
# ─────────────────────────────────────────────────────────────────────────────

URGENCY_MULTIPLIERS = {
    "Routine":   1.00,
    "Urgent":    1.20,
    "Emergency": 1.50,
}

# ─────────────────────────────────────────────────────────────────────────────
# INSURANCE PLANS
# HARDCODED — standard US insurance tier archetypes
# coverage = share insurance pays after deductible is met
# deductible = annual deductible in USD
# ─────────────────────────────────────────────────────────────────────────────

INSURANCE_PLANS = {
    "PPO":       {"coverage": 0.80, "deductible": 1500},
    "HMO":       {"coverage": 0.70, "deductible": 2000},
    "Medicare":  {"coverage": 0.80, "deductible": 226},
    "Medicaid":  {"coverage": 0.90, "deductible": 0},
    "Uninsured": {"coverage": 0.00, "deductible": 0},
}

# ─────────────────────────────────────────────────────────────────────────────
# DEDUCTIBLE STATUS
# HARDCODED — share of annual deductible still remaining
# ─────────────────────────────────────────────────────────────────────────────

DEDUCTIBLE_STATUS = {
    "Not met":       1.0,   # full deductible still unpaid
    "Partially met": 0.5,   # half remaining
    "Fully met":     0.0,   # insurance kicks in immediately
}