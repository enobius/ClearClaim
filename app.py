from __future__ import annotations

import streamlit as st

from graph import build_graph


PROCEDURE_TO_CPT = {
    "Knee MRI": "73721",
    "CT Scan (chest)": "71260",
    "Rotator Cuff Repair": "29827",
    "Colonoscopy with Biopsy": "45380",
    "Echocardiogram": "93306",
}

INSURANCE_OPTIONS = ["aetna_ppo", "bcbs_ppo", "unitedhealthcare_hmo"]
PROVIDER_OPTIONS = ["hospital", "imaging_center", "asc"]
URGENCY_OPTIONS = ["routine", "urgent", "emergency"]
DEDUCTIBLE_OPTIONS = ["not_met", "partially_met", "fully_met"]


@st.cache_resource
def get_graph_app():
    return build_graph()


def _currency(value: float) -> str:
    return f"${value:,.0f}"


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: radial-gradient(1400px 700px at 15% -15%, #1a1d22 0%, #0f1113 45%, #0b0d0f 100%);
                color: #ececec;
            }
            h1,h2,h3,h4,p,span,div,label { color: #ececec; }
            .shell { margin-left: 88px; }
            .rail {
                position: fixed;
                left: 14px;
                top: 24px;
                width: 56px;
                height: 250px;
                border: 1px solid #2d3137;
                border-radius: 20px;
                background: linear-gradient(180deg,#1a1d22,#121417);
                display: flex;
                flex-direction: column;
                justify-content: space-around;
                align-items: center;
                z-index: 1000;
            }
            .rail-dot {
                width: 34px;
                height: 34px;
                border-radius: 10px;
                background: #5f56e8;
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
            }
            .rail-ghost {
                width: 34px;
                height: 34px;
                border-radius: 10px;
                border: 1px solid #2e3238;
                color: #8a8f98;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .kicker {
                color: #7a6bff;
                text-transform: uppercase;
                letter-spacing: .08em;
                font-size: .72rem;
                margin-top: .2rem;
            }
            .subtitle { color: #8f949c; margin-top: -8px; margin-bottom: 16px; }
            .card {
                border: 1px solid #2a2f35;
                border-radius: 14px;
                background: linear-gradient(180deg, #171a1f, #14171b);
                padding: 14px;
                margin-bottom: 12px;
            }
            .card-purple { background: radial-gradient(120% 150% at 100% 0%, #7a70ff 0%, #6c63eb 45%, #5a54d9 100%); border-color: #6f67ef; }
            .card-orange { background: radial-gradient(130% 130% at 100% 100%, #ef7f5f 0%, #e77252 45%, #df6547 100%); border-color: #ea7253; }
            .metric-label { font-size: .76rem; text-transform: uppercase; letter-spacing: .12em; opacity: .86; }
            .metric-value { font-size: 3rem; font-weight: 800; line-height: 1; margin: 6px 0; }
            .metric-sub { font-size: .95rem; opacity: .9; }
            .kpi-dark .metric-value { color: #ff8457; }
            .chip-row { display:flex; gap:8px; justify-content:flex-end; margin-bottom:8px; }
            .chip { border: 1px solid #2b2f35; border-radius: 8px; padding: 3px 10px; font-size: .76rem; color:#aeb4bf; background:#12151a; }
            .chip-accent { color:#8f87ff; border-color:#2e2a56; background:#141429; }
            .split-card-list { margin:0; padding-left:14px; color:#b6bcc5; line-height:1.6; }
            .warn { border:1px solid #8e6514; background:#2c210b; color:#f3bb4f; border-radius:10px; padding:10px; }
            .ok { border:1px solid #0f8c67; background:#063527; color:#35d6a4; border-radius:10px; padding:10px; }
            .issue { border:1px solid #8b2731; background:#2a0d13; color:#f08d93; border-radius:10px; padding:12px; }
            .fix { border:1px solid #2a2f35; border-radius:10px; padding:10px; background:#13161a; }
            .tip-table { border:1px solid #2b3036; border-radius:12px; overflow:hidden; }
            .tip-head,.tip-row { display:grid; grid-template-columns: 64px 1fr 180px 120px; }
            .tip-head { background:#111418; color:#8f949c; font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; }
            .tip-head div,.tip-row div { padding:10px 12px; border-bottom:1px solid #21252b; }
            .tag-save { color:#37d8a9; font-weight:700; }
            .tag-warn { color:#f5be52; font-weight:700; }
            .footer { color:#6f7580; border-top:1px solid #272c33; padding-top:8px; margin-top:14px; font-size:.84rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )



def _rail() -> None:
    st.markdown(
        """
        <div class="rail">
          <div class="rail-dot">C</div>
          <div class="rail-ghost">?</div>
          <div class="rail-ghost">?</div>
          <div class="rail-ghost">¤</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_patient_top_cards(cost: dict) -> None:
    insurance_low = float(cost.get("insurance_low", 0.0))
    insurance_high = float(cost.get("insurance_high", 0.0))
    oop_low = float(cost.get("oop_low", 0.0))
    oop_high = float(cost.get("oop_high", 0.0))

    # For UI parity with the mockup, display total as payer + patient burden.
    display_total_low = insurance_low + oop_low
    display_total_high = insurance_high + oop_high
    total_mid = (display_total_low + display_total_high) / 2
    insurance_mid = (insurance_low + insurance_high) / 2
    oop_mid = (oop_low + oop_high) / 2

    cover_pct = 0 if display_total_high <= 0 else max(0.0, min(1.0, insurance_high / display_total_high))
    oop_pct = 1.0 - cover_pct

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        f"""
        <div class="card card-purple">
          <div class="metric-label">Estimated total</div>
          <div class="metric-value">{_currency(total_mid)}</div>
          <div class="metric-sub">{_currency(display_total_low)} - {_currency(display_total_high)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c2.markdown(
        f"""
        <div class="card card-orange">
          <div class="metric-label">Insurance covers</div>
          <div class="metric-value">{_currency(insurance_mid)}</div>
          <div class="metric-sub">{_currency(insurance_low)} - {_currency(insurance_high)}</div>
          <div style="margin-top:10px;font-weight:700;">{cover_pct:.0%} insured | {oop_pct:.0%} you pay</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c3.markdown(
        f"""
        <div class="card kpi-dark">
          <div class="metric-label">You pay</div>
          <div class="metric-value">{_currency(oop_mid)}</div>
          <div class="metric-sub">{_currency(oop_low)} - {_currency(oop_high)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c4.markdown(
        f"""
        <div class="card">
          <div class="metric-label">Coverage split</div>
          <div style="margin-top:10px; font-size:1.6rem; font-weight:700; color:#67dfbf;">{cover_pct:.0%}</div>
          <ul class="split-card-list">
            <li>Insurer: {cover_pct:.0%}</li>
            <li>Deduct: {oop_pct * 0.56:.0%}</li>
            <li>Coinsur: {oop_pct * 0.28:.0%}</li>
            <li>Copay: {oop_pct * 0.16:.0%}</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_patient_details(result: dict) -> None:
    cost = result.get("cost_estimate", {})
    benefits = result.get("benefits", {})

    if benefits.get("prior_auth_required", False):
        st.markdown(
            f"<div class='warn'>Prior Authorization Required - {benefits.get('prior_auth_notes', '')}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<div class='ok'>No prior authorization required for this plan/CPT.</div>", unsafe_allow_html=True)

    explanation = str(cost.get("explanation", "")).strip()
    if explanation:
        st.markdown(f"<div class='card'><div class='metric-label'>AI explanation</div><p>{explanation}</p></div>", unsafe_allow_html=True)

    tips = cost.get("savings_tips", [])
    if tips:
        rows = []
        for i, tip in enumerate(tips, start=1):
            savings = "UP TO 40%" if i == 1 else ("AVOID 100% BILL" if i == 2 else "UP TO 15%")
            tag = "tag-save" if i != 2 else "tag-warn"
            effort = "Low" if i == 1 else ("Medium" if i == 2 else "Low")
            rows.append(
                f"<div class='tip-row'><div>{i}</div><div>{tip}</div><div class='{tag}'>{savings}</div><div>{effort}</div></div>"
            )
        st.markdown(
            """
            <div class="card">
              <h4 style="margin:0 0 8px 0;">Ways to reduce costs</h4>
              <div class="tip-table">
                <div class="tip-head"><div>#</div><div>Strategy</div><div>Potential savings</div><div>Effort</div></div>
            """
            + "".join(rows)
            + "</div></div>",
            unsafe_allow_html=True,
        )


def _render_hospital_top(result: dict) -> None:
    denial = result.get("denial_score", {})
    ncci = result.get("ncci_result", {})
    factors = denial.get("risk_factors", [])

    risk_pct = float(denial.get("risk_pct", 0.0))
    status = str(denial.get("status", "LOW RISK"))

    c1, c2, c3 = st.columns([1.25, 1.0, 0.95])
    c1.markdown(
        f"""
        <div class="card card-orange">
          <div class="metric-label">Denial risk score</div>
          <div class="metric-value">{risk_pct:.0%}</div>
          <div class="risk-chip">{status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ncci_ok = ncci.get("valid", True)
    c2.markdown(
        f"""
        <div class="card">
          <div class="metric-label">NCCI validation</div>
          <div style="font-size:2rem; margin:10px 0; color:{'#35d6a4' if ncci_ok else '#ff7b7b'};">{'?' if ncci_ok else '!'}</div>
          <div style="font-size:1.5rem; font-weight:700;">{'All checks passed' if ncci_ok else 'Checks failed'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c3.markdown(
        f"""
        <div class="card">
          <div class="metric-label">Risk factors</div>
          <div style="font-size:2.1rem; font-weight:700; margin-top:10px; color:#ff6d77;">{len(factors)}</div>
          <div style="color:#9ca3ad; margin-top:2px;">factors identified</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_hospital_lower(result: dict, pre_risk: float | None) -> None:
    denial = result.get("denial_score", {})
    factors = denial.get("risk_factors", [])
    fix_list = result.get("fix_list", [])
    risk_pct = float(denial.get("risk_pct", 0.0))

    if factors:
        item_lines = []
        for factor in factors:
            item_lines.append(
                f"<li>{factor.get('description','')}<br><span style='color:#ca8b92;'>Risk contribution: +{float(factor.get('risk_increase', 0.0)):.0%}</span></li>"
            )
        st.markdown("<div class='issue'><b>Issues found</b><ul>" + "".join(item_lines) + "</ul></div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><div class='metric-label'>Fix list</div></div>", unsafe_allow_html=True)

    if not fix_list:
        st.write("No fixes required.")
        return

    options = [f"Fix {i + 1}: {fix.get('issue', '')}" for i, fix in enumerate(fix_list)]
    selected_label = st.selectbox("Fix to apply", options, key="fix_select")
    selected_idx = options.index(selected_label)
    fix = fix_list[selected_idx]

    st.markdown(
        f"""
        <div class="fix">
          <div style="display:flex; justify-content:space-between; gap:12px; align-items:center;">
            <div>
              <div style="font-size:1.6rem; font-weight:700;">{fix.get('issue','')}</div>
              <div style="color:#9ca2ab; margin-top:4px;">{fix.get('action','')}</div>
            </div>
            <div class="chip tag-warn">- {float(fix.get('risk_reduction', 0.0)):.0%} risk</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Apply fix - recalculate risk", use_container_width=True):
        current_result = st.session_state.hospital_result
        if not current_result:
            st.error("No hospital result found. Run denial prediction before applying a fix.")
        else:
            try:
                updated_fixes = [dict(x) for x in fix_list]
                updated_fixes[selected_idx]["applied"] = True

                payload = dict(current_result)
                payload["fix_list"] = updated_fixes
                payload["reeval"] = True
                payload["messages"] = []

                with st.spinner("Re-running denial scoring with applied fix..."):
                    reevaluated = get_graph_app().invoke(payload)
                    st.session_state.hospital_result = reevaluated

                old_risk = float(pre_risk or 0.0)
                new_risk = float(reevaluated.get("denial_score", {}).get("risk_pct", 0.0))
                st.success(f"Risk updated: {old_risk:.0%} -> {new_risk:.0%}")
                st.rerun()
            except Exception as exc:
                st.error(f"Re-evaluation failed: {exc}")

    if pre_risk is not None and risk_pct < pre_risk:
        st.markdown(f"<div class='ok'>After fix: {risk_pct:.0%}. Previously {pre_risk:.0%}.</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="ClearClaim", layout="wide")
    _inject_styles()
    _rail()

    st.markdown("<div class='shell'>", unsafe_allow_html=True)
    st.markdown("<div class='kicker'>Healthcare Financial Intelligence</div>", unsafe_allow_html=True)
    st.title("ClearClaim")
    st.markdown("<div class='subtitle'>Know what you'll pay. Know if you'll get paid.</div>", unsafe_allow_html=True)

    app = get_graph_app()

    if "hospital_result" not in st.session_state:
        st.session_state.hospital_result = None
    if "hospital_pre_risk" not in st.session_state:
        st.session_state.hospital_pre_risk = None

    patient_tab, hospital_tab = st.tabs(["Patient mode", "Hospital mode"])

    with patient_tab:
        form_col, content_col = st.columns([0.95, 2.05], gap="large")

        with form_col:
            st.markdown("<div class='card'><div class='metric-label'>Your details</div>", unsafe_allow_html=True)
            demo = st.button("Load demo", key="patient_demo")
            demo_loaded = st.session_state.get("patient_demo_loaded", False) or demo
            if demo:
                st.session_state.patient_demo_loaded = True

            with st.form("patient_form", clear_on_submit=False):
                procedure = st.selectbox("Procedure", list(PROCEDURE_TO_CPT.keys()), index=0)
                zip_code = st.text_input("Location", value="06604" if demo_loaded else "")
                provider_type = st.selectbox("Provider", PROVIDER_OPTIONS, index=0)
                insurance_type = st.selectbox("Insurance", INSURANCE_OPTIONS, index=0)
                deductible_status = st.selectbox("Deductible", DEDUCTIBLE_OPTIONS, index=1)
                urgency = st.selectbox("Urgency", URGENCY_OPTIONS, index=0)
                submit_patient = st.form_submit_button("Estimate my costs", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with content_col:
            cpt_chip = PROCEDURE_TO_CPT.get(procedure, "73721") if 'procedure' in locals() else "73721"
            zip_chip = zip_code if 'zip_code' in locals() and zip_code else "06604"
            st.markdown(
                f"<div class='chip-row'><span class='chip chip-accent'>CPT {cpt_chip}</span><span class='chip'>CT / {zip_chip}</span></div>",
                unsafe_allow_html=True,
            )

            if submit_patient:
                payload = {
                    "mode": "patient",
                    "patient_input": {
                        "cpt_code": cpt_chip,
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
                        result = app.invoke(payload)
                        _render_patient_top_cards(result.get("cost_estimate", {}))
                        _render_patient_details(result)
                    except Exception as exc:
                        st.error(f"Patient workflow failed: {exc}")
            else:
                st.info("Submit patient details to render the mockup cards.")

    with hospital_tab:
        form_col, content_col = st.columns([0.95, 2.05], gap="large")

        with form_col:
            st.markdown("<div class='card'><div class='metric-label'>Claim details</div>", unsafe_allow_html=True)
            demo = st.button("Load demo", key="hospital_demo")
            demo_loaded = st.session_state.get("hospital_demo_loaded", False) or demo
            if demo:
                st.session_state.hospital_demo_loaded = True

            with st.form("hospital_form", clear_on_submit=False):
                cpt_code_h = st.text_input("CPT code", value="73721" if demo_loaded else "")
                icd_code = st.text_input("ICD-10 code", value="M17.11" if demo_loaded else "")
                payer = st.selectbox("Payer", INSURANCE_OPTIONS, index=0)
                clinical_note = st.text_area(
                    "Clinical note",
                    value=(
                        "Patient presents with right knee pain for 3 months. Physical exam reveals medial joint-line tenderness and positive McMurray test. X-ray shows narrowing of medial compartment. MRI requested to evaluate meniscal tear and assess cartilage damage."
                        if demo_loaded
                        else ""
                    ),
                    height=170,
                )
                submit_hospital = st.form_submit_button("Analyze claim", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with content_col:
            cpt_chip_h = cpt_code_h if 'cpt_code_h' in locals() and cpt_code_h else "73721"
            icd_chip = icd_code if 'icd_code' in locals() and icd_code else "M17.11"
            st.markdown(
                f"<div class='chip-row'><span class='chip chip-accent'>CPT {cpt_chip_h}</span><span class='chip'>ICD {icd_chip}</span></div>",
                unsafe_allow_html=True,
            )

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
                        st.session_state.hospital_result = result
                        st.session_state.hospital_pre_risk = float(result.get("denial_score", {}).get("risk_pct", 0.0))
                    except Exception as exc:
                        st.error(f"Hospital workflow failed: {exc}")

            result = st.session_state.hospital_result
            if result:
                _render_hospital_top(result)
                _render_hospital_lower(result, st.session_state.hospital_pre_risk)
            else:
                st.info("Submit claim details to render the mockup cards.")

    st.markdown("<div class='footer'>CMS Price Transparency  •  NCCI Coding Rules  •  Benefits simulated  •  Claude API + LangGraph</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()

