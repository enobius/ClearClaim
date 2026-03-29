import os
import tempfile
from pathlib import Path
import sys

from fastapi.testclient import TestClient

TMP_DB = Path(tempfile.gettempdir()) / "clearclaim_test.db"
os.environ["CLEARCLAIM_DB_PATH"] = str(TMP_DB)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app, init_db


class DummyGraph:
    def invoke(self, payload):
        mode = payload.get("mode")
        if mode == "patient":
            return {
                "benefits": {"prior_auth_required": True, "prior_auth_notes": "Auth needed"},
                "cost_estimate": {
                    "total_low": 700,
                    "total_high": 900,
                    "oop_low": 200,
                    "oop_high": 300,
                    "insurance_low": 500,
                    "insurance_high": 600,
                    "explanation": "test",
                    "savings_tips": ["tip1"],
                },
                "cms_rates": {},
                "fee_schedule": {},
                "messages": [],
            }

        if payload.get("reeval"):
            return {
                "denial_score": {"risk_pct": 0.04, "status": "LOW RISK", "risk_factors": [], "note_analysis": "ok"},
                "ncci_result": {"valid": True, "edit_flags": []},
                "fix_list": payload.get("fix_list", []),
                "messages": [],
            }

        return {
            "denial_score": {
                "risk_pct": 0.34,
                "status": "HIGH RISK",
                "risk_factors": [{"description": "missing auth"}],
                "note_analysis": "risk",
            },
            "ncci_result": {"valid": True, "edit_flags": []},
            "fix_list": [{"issue": "missing auth", "action": "attach", "risk_reduction": 0.28, "applied": False}],
            "messages": [],
        }


client = TestClient(app)
init_db()
app.state.graph_app = DummyGraph()


def test_patient_contract():
    response = client.post(
        "/api/v1/patient/estimate",
        json={
            "session_id": "sess_1",
            "mode": "patient",
            "input": {
                "cpt_code": "73721",
                "zip_code": "06604",
                "insurance_type": "aetna_ppo",
                "provider_type": "hospital",
                "urgency": "routine",
                "deductible_status": "partially_met",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "patient"
    assert "cost_estimate" in body["output"]
    ce = body["output"]["cost_estimate"]
    assert ce["total_low"] == ce["insurance_low"] + ce["oop_low"]
    assert ce["total_high"] == ce["insurance_high"] + ce["oop_high"]
    assert "market_total_low" in ce
    assert "market_total_high" in ce


def test_hospital_and_reeval_contract():
    response = client.post(
        "/api/v1/hospital/denial",
        json={
            "session_id": "sess_2",
            "mode": "hospital",
            "input": {
                "cpt_code": "73721",
                "icd_code": "M17.11",
                "payer": "aetna_ppo",
                "clinical_note": "note",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "fix_list" in body["output"]

    run_id = body["run_id"]
    reevaluate = client.post(
        f"/api/v1/hospital/{run_id}/reevaluate",
        json={"base_run_id": run_id, "selected_fix_index": 0, "applied_fixes": body["output"]["fix_list"]},
    )
    assert reevaluate.status_code == 200
    new_body = reevaluate.json()
    assert new_body["output"]["denial_score"]["risk_pct"] <= body["output"]["denial_score"]["risk_pct"]


def test_invalid_payload_422():
    response = client.post(
        "/api/v1/patient/estimate",
        json={"session_id": "x", "mode": "patient", "input": {"cpt_code": "73721"}},
    )
    assert response.status_code == 422
