# data/data.py

PROCEDURES = {
    "Knee MRI": {"cpt": "73721", "low": 466, "high": 2785},
    "CT Scan (chest)": {"cpt": "71260", "low": 342, "high": 4150},
    "Rotator Cuff Repair": {"cpt": "29827", "low": 1876, "high": 14200},
    "Colonoscopy with Biopsy": {"cpt": "45380", "low": 511, "high": 3560},
    "Echocardiogram": {"cpt": "93306", "low": 396, "high": 3200},
}

PROVIDER_MULTIPLIERS = {
    "Hospital": 1.00,
    "Private Clinic": 0.75,
    "Urgent Care": 0.85,
    "Emergency Room": 1.60,
}

URGENCY_MULTIPLIERS = {
    "Routine": 1.00,
    "Urgent": 1.20,
    "Emergency": 1.50,
}
