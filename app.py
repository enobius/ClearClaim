from __future__ import annotations

import streamlit as st

from graph import build_graph


@st.cache_resource
def get_graph_app():
    return build_graph()


def _currency(value: float) -> str:
    return f"${value:,.0f}"


def render_patient_result(result: dict) -> None:
    cost = result.get("cost_estimate", {})
    benefits = result.get("benefits", {})

    st.subheader("Estimated Cost")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Range", f"{_currency(cost.get('total_low', 0.0))} - {_currency(cost.get('total_high', 0.0))}")
    c2.metric("Out-of-Pocket", f"{_currency(cost.get('oop_low', 0.0))} - {_currency(cost.get('oop_high', 0.0))}")
    c3.metric("Insurance Pays", f"{_currency(cost.get('insurance_low', 0.0))} - {_currency(cost.get('insurance_high', 0.0))}")

    st.subheader("Split")
    max_total = max(float(cost.get("total_high", 0.0)), 1.0)
    oop_pct = min(1.0, float(cost.get("oop_high", 0.0)) / max_total)
    st.progress(oop_pct, text=f"Patient share: {oop_pct:.0%} | Insurance share: {(1 - oop_pct):.0%}")

    if benefits.get("prior_auth_required", False):
        st.warning(f"Prior Authorization Required: {benefits.get('prior_auth_notes', '')}")
    else:
        st.success("No prior authorization required for this plan/CPT.")

    explanation = cost.get("explanation", "")
    if explanation:
        st.subheader("Explanation")
        st.write(explanation)

    tips = cost.get("savings_tips", [])
    if tips:
        st.subheader("Savings Tips")
        for tip in tips:
            st.write(f"- {tip}")


def render_hospital_result(result: dict) -> None:
    denial = result.get("denial_score", {})
    ncci = result.get("ncci_result", {})
    fix_list = result.get("fix_list", [])

    st.subheader("Denial Risk")
    risk_pct = float(denial.get("risk_pct", 0.0))
    status = str(denial.get("status", "LOW RISK"))
    st.metric("Risk", f"{risk_pct:.0%}", status)

    if ncci.get("valid", True):
        st.success("NCCI Check: Valid")
    else:
        st.error("NCCI Check: Invalid")

    flags = ncci.get("edit_flags", [])
    if flags:
        st.write("NCCI Flags")
        for flag in flags:
            st.write(f"- {flag}")

    factors = denial.get("risk_factors", [])
    if factors:
        st.write("Risk Factors")
        for factor in factors:
            st.write(f"- {factor.get('description', factor)}")

    note_analysis = denial.get("note_analysis", "")
    if note_analysis:
        st.subheader("Clinical Note Analysis")
        st.write(note_analysis)

    st.subheader("Fix List")
    if not fix_list:
        st.write("No fixes required.")
    for idx, fix in enumerate(fix_list):
        marker = "[Applied]" if fix.get("applied", False) else "[Pending]"
        st.write(f"{idx + 1}. {marker} {fix.get('issue', '')}")
        st.write(f"Action: {fix.get('action', '')}")
        st.write(f"Risk reduction: {float(fix.get('risk_reduction', 0.0)):.0%}")


def main() -> None:
    st.set_page_config(page_title="ClearClaim", layout="wide")
    st.title("ClearClaim")
    st.caption("Financial clarity for patients. Financial certainty for hospitals.")

    app = get_graph_app()

    if "hospital_result" not in st.session_state:
        st.session_state.hospital_result = None
    if "hospital_payload" not in st.session_state:
        st.session_state.hospital_payload = None
    if "hospital_pre_risk" not in st.session_state:
        st.session_state.hospital_pre_risk = None

    patient_tab, hospital_tab = st.tabs(["Patient Mode", "Hospital Mode"])

    with patient_tab:
        st.subheader("Patient Input")
        if st.button("Load Patient Demo (Knee MRI)", key="patient_demo"):
            st.session_state.patient_demo_loaded = True

        demo_loaded = st.session_state.get("patient_demo_loaded", False)
        with st.form("patient_form"):
            cpt_code = st.text_input("CPT Code", value="73721" if demo_loaded else "")
            zip_code = st.text_input("ZIP Code", value="06604" if demo_loaded else "")
            insurance_type = st.selectbox("Insurance", ["aetna_ppo", "bcbs_ppo", "unitedhealthcare_hmo"], index=0)
            provider_type = st.selectbox("Provider Type", ["hospital", "imaging_center", "asc"], index=0)
            urgency = st.selectbox("Urgency", ["routine", "urgent", "emergency"], index=0)
            deductible_status = st.selectbox("Deductible Status", ["not_met", "partially_met", "fully_met"], index=1)
            submit_patient = st.form_submit_button("Estimate Cost")

        if submit_patient:
            payload = {
                "mode": "patient",
                "patient_input": {
                    "cpt_code": cpt_code,
                    "zip_code": zip_code,
                    "insurance_type": insurance_type,
                    "provider_type": provider_type,
                    "urgency": urgency,
                    "deductible_status": deductible_status,
                },
                "messages": [],
            }
            with st.spinner("Running patient cost workflow..."):
                try:
                    patient_result = app.invoke(payload)
                    render_patient_result(patient_result)
                except Exception as exc:
                    st.error(f"Patient workflow failed: {exc}")

    with hospital_tab:
        st.subheader("Hospital Input")
        if st.button("Load Hospital Demo (Knee MRI)", key="hospital_demo"):
            st.session_state.hospital_demo_loaded = True

        hospital_demo_loaded = st.session_state.get("hospital_demo_loaded", False)
        with st.form("hospital_form"):
            clinical_note = st.text_area(
                "Clinical Note",
                value=(
                    "Patient with right knee pain for 3 months, positive McMurray test, "
                    "medial compartment narrowing on X-ray. MRI requested to evaluate meniscal injury."
                    if hospital_demo_loaded
                    else ""
                ),
                height=140,
            )
            cpt_code_h = st.text_input("CPT Code", value="73721" if hospital_demo_loaded else "")
            icd_code = st.text_input("ICD-10 Code", value="M17.11" if hospital_demo_loaded else "")
            payer = st.selectbox("Payer", ["aetna_ppo", "bcbs_ppo", "unitedhealthcare_hmo"], index=0)
            submit_hospital = st.form_submit_button("Predict Denial Risk")

        if submit_hospital:
            payload = {
                "mode": "hospital",
                "hospital_input": {
                    "cpt_code": cpt_code_h,
                    "icd_code": icd_code,
                    "payer": payer,
                    "clinical_note": clinical_note,
                },
                "messages": [],
            }
            with st.spinner("Running hospital denial workflow..."):
                try:
                    result = app.invoke(payload)
                    st.session_state.hospital_payload = payload
                    st.session_state.hospital_result = result
                    st.session_state.hospital_pre_risk = float(result.get("denial_score", {}).get("risk_pct", 0.0))
                except Exception as exc:
                    st.error(f"Hospital workflow failed: {exc}")

        result = st.session_state.hospital_result
        if result:
            render_hospital_result(result)

            fix_list = result.get("fix_list", [])
            if fix_list:
                options = [f"Fix {i + 1}: {fix.get('issue', '')}" for i, fix in enumerate(fix_list)]
                selected_label = st.selectbox("Fix to Apply", options, key="fix_select")
                selected_idx = options.index(selected_label)

                if st.button("Apply Fix and Recalculate"):
                    try:
                        current_result = st.session_state.hospital_result
                        if not current_result:
                            st.error("No hospital result found. Run denial prediction before applying a fix.")
                            return

                        updated_fixes = [dict(fix) for fix in fix_list]
                        updated_fixes[selected_idx]["applied"] = True

                        reeval_payload = dict(current_result)
                        reeval_payload["fix_list"] = updated_fixes
                        reeval_payload["reeval"] = True
                        reeval_payload["messages"] = []

                        with st.spinner("Re-running denial scoring with applied fix..."):
                            reevaluated = app.invoke(reeval_payload)
                            st.session_state.hospital_result = reevaluated

                        old_risk = float(st.session_state.hospital_pre_risk or 0.0)
                        new_risk = float(reevaluated.get("denial_score", {}).get("risk_pct", 0.0))
                        st.success(f"Risk updated: {old_risk:.0%} -> {new_risk:.0%}")
                    except Exception as exc:
                        st.error(f"Re-evaluation failed: {exc}")

    st.markdown("---")
    st.caption(
        "Transparency: numeric estimates and denial risk are deterministic outputs from project data files. "
        "LLM usage is constrained to explanation and text analysis."
    )


if __name__ == "__main__":
    main()
