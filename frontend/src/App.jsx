import React, { useMemo, useState } from "react";
import {
  estimatePatientCost,
  predictHospitalDenial,
  reevaluateHospitalRun,
} from "./api";

const T = {
  bg: "#0e0f0d",
  bgSub: "#141512",
  card: "#1a1b18",
  border: "#2c2d28",
  borderSub: "#242520",
  text: "#f0eedf",
  textSoft: "#b5b3a4",
  textMuted: "#7d7b6e",
  textDim: "#4e4d44",
  accent: "#6C5CE7",
  accentAlt: "#8B7FF5",
  teal: "#00D2A0",
  tealBg: "#0b2920",
  coral: "#FF6B4A",
  amber: "#FFB020",
  amberBg: "#2b2210",
  red: "#FF4757",
  redBg: "#2b1318",
};

const F = {
  mono: "'JetBrains Mono', 'SF Mono', monospace",
  body: "'DM Sans', system-ui, sans-serif",
  display: "'Plus Jakarta Sans', system-ui, sans-serif",
};

const Styles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: ${T.bg}; }
    @keyframes fadeUp { from { opacity:0; transform:translateY(18px); } to { opacity:1; transform:translateY(0); } }
    .au { animation: fadeUp 0.45s ease both; }
    .au1 { animation: fadeUp 0.45s ease 0.06s both; }
    .au2 { animation: fadeUp 0.45s ease 0.12s both; }
    .au3 { animation: fadeUp 0.45s ease 0.18s both; }
    .au4 { animation: fadeUp 0.45s ease 0.24s both; }
    .hovlift { transition: transform 0.2s ease, box-shadow 0.2s ease; }
    .hovlift:hover { transform: translateY(-3px); box-shadow: 0 12px 40px rgba(0,0,0,0.25); }
    @media (max-width: 1100px) {
      .stat-grid { grid-template-columns: 1fr 1fr !important; }
      .hospital-top-grid { grid-template-columns: 1fr 1fr !important; }
      .two-col-grid { grid-template-columns: 1fr !important; }
    }
    @media (min-width: 1400px) {
      .two-col-grid {
        grid-template-columns: minmax(340px, 420px) 1fr !important;
      }
      .stat-grid {
        grid-template-columns: repeat(4, minmax(180px, 1fr)) !important;
      }
      .hospital-top-grid {
        grid-template-columns: minmax(300px, 1.5fr) 1fr 1fr !important;
      }
    }
    @media (max-width: 760px) {
      .app-shell { flex-direction: column; padding: 12px !important; gap: 12px !important; }
      .sidebar { width: 100% !important; position: static !important; flex-direction: row !important; justify-content: space-between !important; padding: 10px 12px !important; }
      .sidebar-logo { margin-bottom: 0 !important; }
      .sidebar-spacer { display: none !important; }
      .main-content { max-width: none !important; width: 100% !important; }
      .stat-grid { grid-template-columns: 1fr !important; }
      .hospital-top-grid { grid-template-columns: 1fr !important; }
    }
    @media (max-width: 480px) {
      .app-shell { padding: 8px !important; gap: 8px !important; }
      .sidebar { border-radius: 14px !important; }
      .sidebar button { width: 38px !important; height: 38px !important; border-radius: 10px !important; }
    }
  `}</style>
);

const demoPatient = {
  procedure: "Knee MRI",
  cpt_code: "73721",
  zip_code: "06604",
  insurance_type: "aetna_ppo",
  provider_type: "hospital",
  urgency: "routine",
  deductible_status: "partially_met",
};

const demoHospital = {
  cpt_code: "73721",
  icd_code: "M17.11",
  payer: "aetna_ppo",
  clinical_note:
    "Patient with right knee pain for 3 months, positive McMurray test, medial compartment narrowing on X-ray. MRI requested to evaluate meniscal injury.",
};

const PROCEDURE_TO_CPT = {
  "Knee MRI": "73721",
  "CT Scan (chest)": "71260",
  "Rotator Cuff Repair": "29827",
  "Colonoscopy with Biopsy": "45380",
  Echocardiogram: "93306",
};

const formatMoney = (value) =>
  `$${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const clamp = (n, min, max) => Math.max(min, Math.min(max, n));

function normalizeInlineText(text) {
  return String(text || "")
    .replace(/\*\*/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function splitBulletLines(text) {
  const normalized = String(text || "").replace(/\s+/g, " ").trim();
  if (!normalized) return [];
  const candidate = normalized
    .replace(/\s+[\u2022]\s+/g, " | ")
    .replace(/\s+[\u2013-]\s+/g, " | ");
  const items = candidate.split("|").map((s) => normalizeInlineText(s)).filter(Boolean);
  return items.length > 1 ? items : [];
}

function parseClinicalNoteSections(raw) {
  const text = String(raw || "").trim();
  if (!text) return [];

  const headingPattern = /\*\*([^*]+)\*\*/g;
  const matches = Array.from(text.matchAll(headingPattern));
  if (!matches.length) {
    return [{ heading: null, body: normalizeInlineText(text), bullets: [] }];
  }

  const sections = [];
  for (let i = 0; i < matches.length; i += 1) {
    const current = matches[i];
    const next = matches[i + 1];
    const heading = normalizeInlineText(current[1] || "").replace(/:+$/, "");
    const start = current.index + current[0].length;
    const end = next ? next.index : text.length;
    const bodyRaw = text.slice(start, end).trim();
    const body = normalizeInlineText(bodyRaw);
    const bullets = splitBulletLines(bodyRaw);
    sections.push({ heading, body, bullets });
  }

  return sections.filter((s) => s.heading || s.body || s.bullets.length);
}

const chipStyle = (color) => ({
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  background: `${color}1A`,
  color,
  fontSize: 10,
  fontWeight: 700,
  fontFamily: F.mono,
  padding: "3px 10px",
  borderRadius: 6,
  letterSpacing: 0.8,
  textTransform: "uppercase",
  maxWidth: "100%",
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
});

const inputBase = {
  width: "100%",
  background: T.bgSub,
  border: `1px solid ${T.borderSub}`,
  borderRadius: 10,
  padding: "10px 12px",
  color: T.text,
  fontSize: 14,
  outline: "none",
};

const labelStyle = {
  fontSize: 11,
  color: T.textMuted,
  marginBottom: 6,
  fontFamily: F.mono,
  letterSpacing: 0.5,
  textTransform: "uppercase",
};

function Chip({ text, color }) {
  return <span style={chipStyle(color)}>{text}</span>;
}

function Sparkline({ data, color }) {
  if (!Array.isArray(data) || data.length < 2) return null;
  const width = 110;
  const height = 28;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Donut({ pct, color, size = 72, stroke = 8 }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const normalized = clamp(pct, 0, 100);
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={T.border} strokeWidth={stroke} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeDasharray={c}
        strokeDashoffset={c * (1 - normalized / 100)}
        strokeLinecap="round"
      />
    </svg>
  );
}

function Sidebar({ tab, setTab }) {
  return (
    <div className="sidebar" style={{ width: 64, background: T.card, borderRadius: 20, padding: "20px 0", display: "flex", flexDirection: "column", alignItems: "center", gap: 4, position: "sticky", top: 20, alignSelf: "flex-start", border: `1px solid ${T.border}` }}>
      <div className="sidebar-logo" style={{ width: 36, height: 36, borderRadius: 10, background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 800, color: "#fff", marginBottom: 24, fontFamily: F.display }}>C</div>
      {["patient", "hospital"].map((key) => (
        <button
          key={key}
          onClick={() => setTab(key)}
          style={{ width: 44, height: 44, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", background: tab === key ? T.accent : "transparent", color: tab === key ? "#fff" : T.textMuted, border: "none", cursor: "pointer" }}
        >
          {key === "patient" ? "P" : "H"}
        </button>
      ))}
      <div className="sidebar-spacer" style={{ flex: 1 }} />
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={labelStyle}>{label}</div>
      {children}
    </div>
  );
}

function PatientForm({ form, setForm, loading, onSubmit }) {
  const update = (key) => (e) => setForm((s) => ({ ...s, [key]: e.target.value }));

  return (
    <form
      onSubmit={onSubmit}
      className="au2 hovlift"
      style={{ background: T.card, borderRadius: 16, padding: "22px 24px", border: `1px solid ${T.border}`, height: "100%" }}
    >
      <div style={{ ...labelStyle, color: T.accent, marginBottom: 16, fontWeight: 700 }}>Patient input</div>
      <Field label="Procedure">
        <select value={form.procedure} onChange={update("procedure")} style={inputBase}>
          {Object.keys(PROCEDURE_TO_CPT).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="ZIP Code"><input value={form.zip_code} onChange={update("zip_code")} style={inputBase} /></Field>
      <Field label="Insurance">
        <select value={form.insurance_type} onChange={update("insurance_type")} style={inputBase}>
          <option value="aetna_ppo">aetna_ppo</option>
          <option value="bcbs_ppo">bcbs_ppo</option>
          <option value="unitedhealthcare_hmo">unitedhealthcare_hmo</option>
        </select>
      </Field>
      <Field label="Provider Type">
        <select value={form.provider_type} onChange={update("provider_type")} style={inputBase}>
          <option value="hospital">hospital</option>
          <option value="imaging_center">imaging_center</option>
          <option value="asc">asc</option>
        </select>
      </Field>
      <Field label="Urgency">
        <select value={form.urgency} onChange={update("urgency")} style={inputBase}>
          <option value="routine">routine</option>
          <option value="urgent">urgent</option>
          <option value="emergency">emergency</option>
        </select>
      </Field>
      <Field label="Deductible Status">
        <select value={form.deductible_status} onChange={update("deductible_status")} style={inputBase}>
          <option value="not_met">not_met</option>
          <option value="partially_met">partially_met</option>
          <option value="fully_met">fully_met</option>
        </select>
      </Field>
      <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
        <button type="button" onClick={() => setForm(demoPatient)} style={btnSecondary}>Load demo</button>
        <button type="submit" disabled={loading} style={btnPrimary}>{loading ? "Running patient cost workflow..." : "Estimate Cost"}</button>
      </div>
    </form>
  );
}

function PatientResults({ result, submittedInput }) {
  if (!result) return null;
  const cost = result.cost_estimate || {};
  const benefits = result.benefits || {};
  const totalLow = Number(cost.total_low || 0);
  const totalHigh = Number(cost.total_high || 0);
  const marketTotalLow = Number(cost.market_total_low || 0);
  const marketTotalHigh = Number(cost.market_total_high || 0);
  const insuranceLow = Number(cost.insurance_low || 0);
  const insuranceHigh = Number(cost.insurance_high || 0);
  const oopLow = Number(cost.oop_low || 0);
  const oopHigh = Number(cost.oop_high || 0);
  const totalMid = (totalLow + totalHigh) / 2;
  const insuranceMid = (insuranceLow + insuranceHigh) / 2;
  const oopMid = (oopLow + oopHigh) / 2;
  const patientPct = totalHigh > 0 ? clamp((oopHigh / totalHigh) * 100, 0, 100) : 0;
  const insurancePct = 100 - patientPct;
  const spark = [totalLow, oopLow, insuranceLow, totalHigh];

  return (
    <>
      <div className="au1 stat-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1.1fr", gap: 16, marginBottom: 20 }}>
        <div className="hovlift" style={{ background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`, borderRadius: 16, padding: "20px 22px", color: "#fff" }}>
          <div style={smallLight}>Estimated total</div>
          <div style={heroNum}>{formatMoney(totalMid)}</div>
          <div style={subLight}>{formatMoney(totalLow)} - {formatMoney(totalHigh)}</div>
          {marketTotalHigh > 0 && (
            <div style={{ ...subLight, opacity: 0.8 }}>
              Market range: {formatMoney(marketTotalLow)} - {formatMoney(marketTotalHigh)}
            </div>
          )}
          <div style={{ marginTop: 14 }}><Sparkline data={spark} color="rgba(255,255,255,0.6)" /></div>
        </div>
        <div className="hovlift" style={{ background: T.coral, borderRadius: 16, padding: "20px 22px", color: "#fff" }}>
          <div style={smallLight}>Insurance pays</div>
          <div style={heroNum}>{formatMoney(insuranceMid)}</div>
          <div style={subLight}>{formatMoney(insuranceLow)} - {formatMoney(insuranceHigh)}</div>
          <div style={{ marginTop: 10 }}><Chip text={`${insurancePct.toFixed(0)}% share`} color="#fff" /></div>
        </div>
        <div className="hovlift" style={{ background: T.card, borderRadius: 16, padding: "20px 22px", border: `1px solid ${T.border}` }}>
          <div style={smallDark}>Out-of-pocket</div>
          <div style={{ ...heroNum, color: T.coral }}>{formatMoney(oopMid)}</div>
          <div style={subDark}>{formatMoney(oopLow)} - {formatMoney(oopHigh)}</div>
          <div style={{ marginTop: 10 }}><Chip text={`${patientPct.toFixed(0)}% share`} color={T.coral} /></div>
        </div>
        <div className="hovlift" style={{ background: T.card, borderRadius: 16, padding: "20px 22px", border: `1px solid ${T.border}` }}>
          <div style={{ ...smallDark, marginBottom: 10 }}>Split</div>
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <div style={{ position: "relative" }}>
              <Donut pct={insurancePct} color={T.teal} />
              <div style={donutCenter}>{insurancePct.toFixed(0)}%</div>
            </div>
            <div style={{ fontSize: 12, color: T.textSoft, lineHeight: 1.8 }}>
              <div>Insurance: <strong style={{ color: T.text }}>{insurancePct.toFixed(0)}%</strong></div>
              <div>Patient: <strong style={{ color: T.text }}>{patientPct.toFixed(0)}%</strong></div>
            </div>
          </div>
        </div>
      </div>

      <div className="two-col-grid" style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 16, marginBottom: 16 }}>
        <div className="hovlift" style={{ background: T.card, borderRadius: 16, padding: "22px 24px", border: `1px solid ${T.border}` }}>
          <div style={{ ...labelStyle, color: T.accent, marginBottom: 14, fontWeight: 700 }}>Your details</div>
          <div style={{ display: "grid", gap: 10 }}>
            <div><div style={labelStyle}>Procedure</div><div style={detailText}>{submittedInput?.procedure || "-"}</div></div>
            <div><div style={labelStyle}>CPT Code</div><div style={detailText}>{submittedInput?.cpt_code || "-"}</div></div>
            <div><div style={labelStyle}>ZIP Code</div><div style={detailText}>{submittedInput?.zip_code || "-"}</div></div>
            <div><div style={labelStyle}>Insurance</div><div style={detailText}>{submittedInput?.insurance_type || "-"}</div></div>
            <div><div style={labelStyle}>Provider Type</div><div style={detailText}>{submittedInput?.provider_type || "-"}</div></div>
            <div><div style={labelStyle}>Deductible Status</div><div style={detailText}>{submittedInput?.deductible_status || "-"}</div></div>
            <div><div style={labelStyle}>Urgency</div><div style={detailText}>{submittedInput?.urgency || "-"}</div></div>
          </div>
        </div>

        <div style={{ display: "grid", gap: 16 }}>
          <div className="au3" style={{ background: benefits.prior_auth_required ? T.amberBg : T.tealBg, borderRadius: 14, padding: "14px 18px", border: `1px solid ${benefits.prior_auth_required ? `${T.amber}33` : `${T.teal}33`}` }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: benefits.prior_auth_required ? T.amber : T.teal, marginBottom: 6 }}>
              {benefits.prior_auth_required ? "Prior Authorization Required" : "No prior authorization required"}
            </div>
            <div style={{ fontSize: 12, color: T.textSoft, lineHeight: 1.6 }}>
              {benefits.prior_auth_required ? benefits.prior_auth_notes || "Prior authorization is required for this plan/CPT." : "No prior authorization required for this plan/CPT."}
            </div>
          </div>

          <div className="au4 hovlift" style={{ background: T.card, borderRadius: 14, padding: "20px 22px", border: `1px solid ${T.border}` }}>
            <div style={{ ...labelStyle, marginBottom: 10 }}>Explanation</div>
            <div style={{ fontSize: 14, color: T.textSoft, lineHeight: 1.8 }}>{cost.explanation || "No explanation returned by backend."}</div>
          </div>
        </div>
      </div>

      {!!(cost.savings_tips || []).length && (
        <div className="hovlift" style={{ background: T.card, borderRadius: 16, padding: "22px 24px", border: `1px solid ${T.border}`, marginBottom: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 700, fontFamily: F.display, color: T.text, marginBottom: 12 }}>Savings tips</div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.borderSub}` }}>
                <th style={{ ...labelStyle, textAlign: "left", paddingBottom: 8 }}>#</th>
                <th style={{ ...labelStyle, textAlign: "left", paddingBottom: 8 }}>Tip</th>
              </tr>
            </thead>
            <tbody>
              {(cost.savings_tips || []).map((tip, i) => (
                <tr key={`${tip}-${i}`} style={{ borderBottom: i < cost.savings_tips.length - 1 ? `1px solid ${T.borderSub}` : "none" }}>
                  <td style={{ padding: "10px 0", width: 40 }}><Chip text={`${i + 1}`} color={T.teal} /></td>
                  <td style={{ padding: "10px 0", color: T.textSoft, fontSize: 14 }}>{tip}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function HospitalForm({ form, setForm, loading, onSubmit }) {
  const update = (key) => (e) => setForm((s) => ({ ...s, [key]: e.target.value }));

  return (
    <form
      onSubmit={onSubmit}
      className="au2 hovlift"
      style={{ background: T.card, borderRadius: 16, padding: "22px 24px", border: `1px solid ${T.border}`, height: "100%" }}
    >
      <div style={{ ...labelStyle, color: T.accent, marginBottom: 16, fontWeight: 700 }}>Hospital input</div>
      <Field label="CPT Code"><input value={form.cpt_code} onChange={update("cpt_code")} style={inputBase} /></Field>
      <Field label="ICD-10 Code"><input value={form.icd_code} onChange={update("icd_code")} style={inputBase} /></Field>
      <Field label="Payer">
        <select value={form.payer} onChange={update("payer")} style={inputBase}>
          <option value="aetna_ppo">aetna_ppo</option>
          <option value="bcbs_ppo">bcbs_ppo</option>
          <option value="unitedhealthcare_hmo">unitedhealthcare_hmo</option>
        </select>
      </Field>
      <Field label="Clinical note">
        <textarea value={form.clinical_note} onChange={update("clinical_note")} rows={6} style={{ ...inputBase, resize: "vertical", fontSize: 13, lineHeight: 1.6 }} />
      </Field>
      <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
        <button type="button" onClick={() => setForm(demoHospital)} style={btnSecondary}>Load demo</button>
        <button type="submit" disabled={loading} style={btnPrimary}>{loading ? "Running hospital denial workflow..." : "Predict Denial Risk"}</button>
      </div>
    </form>
  );
}

function HospitalResults({ result, preRisk, selectedFixIndex, setSelectedFixIndex, onApplyFix, applyingFix }) {
  if (!result) return null;

  const denial = result.denial_score || {};
  const ncci = result.ncci_result || {};
  const fixList = result.fix_list || [];
  const riskPct = clamp(Number(denial.risk_pct || 0) * 100, 0, 100);
  const status = String(denial.status || "LOW RISK");
  const riskColor = status.includes("LOW") ? T.teal : T.red;
  const noteSections = parseClinicalNoteSections(denial.note_analysis);

  return (
    <>
      <div className="au1 hospital-top-grid" style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div className="hovlift" style={{ background: status.includes("LOW") ? `linear-gradient(135deg, #0a6e4a, ${T.teal})` : `linear-gradient(135deg, #b5302a, ${T.coral})`, borderRadius: 16, padding: "28px 26px", color: "#fff" }}>
          <div style={smallLight}>Denial risk</div>
          <div style={{ fontSize: "clamp(44px, 12vw, 72px)", fontWeight: 800, fontFamily: F.display, lineHeight: 1 }}>
            {riskPct.toFixed(0)}
            <span style={{ fontSize: "clamp(22px, 6vw, 32px)", fontWeight: 600 }}>%</span>
          </div>
          <div style={{ marginTop: 10 }}><Chip text={status} color="#fff" /></div>
          {preRisk !== null ? <div style={{ marginTop: 8, fontSize: 12, opacity: 0.75 }}>Baseline: {(preRisk * 100).toFixed(0)}%</div> : null}
        </div>

        <div className="hovlift" style={{ background: T.card, borderRadius: 16, padding: 22, border: `1px solid ${T.border}` }}>
          <div style={smallDark}>NCCI Validation</div>
          <div style={{ marginTop: 12, marginBottom: 8 }}><Chip text={ncci.valid === false ? "Invalid" : "Valid"} color={ncci.valid === false ? T.red : T.teal} /></div>
          <div style={{ fontSize: 12, color: T.textMuted, lineHeight: 1.6 }}>{(ncci.edit_flags || []).length ? `Flags: ${(ncci.edit_flags || []).join(", ")}` : "No edit conflicts."}</div>
        </div>

        <div className="hovlift" style={{ background: T.card, borderRadius: 16, padding: 22, border: `1px solid ${T.border}` }}>
          <div style={smallDark}>Risk factors</div>
          <div style={{ display: "flex", justifyContent: "center", marginTop: 10, position: "relative" }}>
            <Donut pct={100 - riskPct} color={riskColor} size={80} stroke={9} />
            <div style={donutCenter}>{(denial.risk_factors || []).length}</div>
          </div>
          <div style={{ textAlign: "center", fontSize: 12, color: T.textMuted, marginTop: 8 }}>{(denial.risk_factors || []).length ? `${(denial.risk_factors || []).length} factors identified` : "No risk factors reported"}</div>
        </div>
      </div>

      {!!(denial.risk_factors || []).length && (
        <div className="au3" style={{ background: T.redBg, borderRadius: 14, padding: "16px 20px", border: `1px solid ${T.red}33`, marginBottom: 16 }}>
          <div style={{ ...labelStyle, color: T.red, marginBottom: 8 }}>Risk factors</div>
          {(denial.risk_factors || []).map((f, i) => (
            <div key={`${f.factor_key || i}-${i}`} style={{ fontSize: 13, color: "#f09595", lineHeight: 1.7 }}>
              - {f.description || String(f)}
            </div>
          ))}
        </div>
      )}

      {!!denial.note_analysis && (
        <div className="au3" style={{ background: T.card, borderRadius: 14, padding: "16px 20px", border: `1px solid ${T.border}`, marginBottom: 16 }}>
          <div style={{ ...labelStyle, marginBottom: 8 }}>Clinical note analysis</div>
          <div style={{ display: "grid", gap: 12 }}>
            {noteSections.map((section, idx) => (
              <div key={`${section.heading || "section"}-${idx}`}>
                {section.heading ? (
                  <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: section.bullets.length ? 8 : 6 }}>
                    {section.heading}
                  </div>
                ) : null}
                {section.bullets.length ? (
                  <ul style={{ paddingLeft: 18, margin: 0, display: "grid", gap: 6 }}>
                    {section.bullets.map((item, itemIdx) => (
                      <li key={`${item}-${itemIdx}`} style={{ fontSize: 13, color: T.textSoft, lineHeight: 1.6 }}>
                        {item}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div style={{ fontSize: 13, color: T.textSoft, lineHeight: 1.7 }}>{section.body}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="au4 hovlift" style={{ background: T.card, borderRadius: 14, padding: "20px 22px", border: `1px solid ${T.border}` }}>
        <div style={{ ...labelStyle, marginBottom: 14 }}>Fix list</div>
        {(fixList || []).length ? (
          <>
            <Field label="Fix to apply">
              <select value={selectedFixIndex} onChange={(e) => setSelectedFixIndex(Number(e.target.value))} style={inputBase}>
                {fixList.map((fix, i) => <option key={`${fix.issue}-${i}`} value={i}>Fix {i + 1}: {fix.issue || "Untitled"}</option>)}
              </select>
            </Field>
            {fixList.map((fix, i) => (
              <div key={`${fix.issue}-${i}`} style={{ background: T.bgSub, borderRadius: 12, padding: 14, border: `1px solid ${T.borderSub}`, marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: T.text }}>{fix.issue || "Issue"}</span>
                  <Chip text={fix.applied ? "applied" : `-${Math.round(Number(fix.risk_reduction || 0) * 100)}% risk`} color={fix.applied ? T.teal : T.amber} />
                </div>
                <div style={{ fontSize: 12, color: T.textMuted, lineHeight: 1.6 }}>{fix.action || "No action provided."}</div>
              </div>
            ))}
            <button onClick={onApplyFix} disabled={applyingFix} style={{ ...btnPrimary, width: "100%" }}>{applyingFix ? "Re-running denial scoring with applied fix..." : "Apply Fix and Recalculate"}</button>
          </>
        ) : (
          <div style={{ fontSize: 13, color: T.textSoft }}>No fixes required.</div>
        )}
      </div>
    </>
  );
}

const smallLight = { fontSize: 11, fontFamily: F.mono, letterSpacing: 0.8, opacity: 0.7, marginBottom: 10, textTransform: "uppercase" };
const smallDark = { fontSize: 11, fontFamily: F.mono, letterSpacing: 0.8, color: T.textMuted, textTransform: "uppercase" };
const heroNum = {
  fontSize: "clamp(28px, 8vw, 36px)",
  fontWeight: 800,
  fontFamily: F.display,
  lineHeight: 1,
  marginBottom: 6,
};
const subLight = { fontSize: 12, opacity: 0.7, fontFamily: F.mono };
const subDark = { fontSize: 12, color: T.textDim, fontFamily: F.mono };
const donutCenter = { position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 800, fontFamily: F.display, color: T.text };
const detailText = { color: T.text, fontSize: 14, lineHeight: 1.4 };

const btnPrimary = {
  flex: 1,
  padding: "12px 0",
  borderRadius: 10,
  background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`,
  color: "#fff",
  border: "none",
  fontSize: 13,
  fontWeight: 600,
  fontFamily: F.body,
  cursor: "pointer",
};

const btnSecondary = {
  padding: "12px 14px",
  borderRadius: 10,
  background: T.bgSub,
  color: T.text,
  border: `1px solid ${T.borderSub}`,
  fontSize: 13,
  fontWeight: 600,
  fontFamily: F.body,
  cursor: "pointer",
};

export default function App() {
  const [tab, setTab] = useState("patient");
  const [sessionId] = useState(() => `sess_${Math.random().toString(36).slice(2, 10)}`);

  const [patientForm, setPatientForm] = useState({ ...demoPatient });
  const [patientResult, setPatientResult] = useState(null);
  const [patientSubmittedInput, setPatientSubmittedInput] = useState(null);
  const [patientLoading, setPatientLoading] = useState(false);
  const [patientError, setPatientError] = useState("");

  const [hospitalForm, setHospitalForm] = useState({ ...demoHospital });
  const [hospitalEnvelope, setHospitalEnvelope] = useState(null);
  const [hospitalPreRisk, setHospitalPreRisk] = useState(null);
  const [hospitalLoading, setHospitalLoading] = useState(false);
  const [hospitalError, setHospitalError] = useState("");
  const [selectedFixIndex, setSelectedFixIndex] = useState(0);
  const [fixApplying, setFixApplying] = useState(false);
  const [reevalMessage, setReevalMessage] = useState("");

  const hospitalResult = hospitalEnvelope?.output || null;

  const patientChips = useMemo(() => [
    `CPT ${PROCEDURE_TO_CPT[patientForm.procedure] || patientForm.cpt_code || "-"}`,
    `ZIP ${patientForm.zip_code || "-"}`,
    patientForm.procedure || "-",
  ], [patientForm]);

  const hospitalChips = useMemo(() => [
    `CPT ${hospitalForm.cpt_code || "-"}`,
    `ICD ${hospitalForm.icd_code || "-"}`,
    String(hospitalForm.payer || "-").toUpperCase(),
  ], [hospitalForm]);

  const handlePatientSubmit = async (e) => {
    e.preventDefault();
    setPatientError("");
    setPatientLoading(true);
    setPatientResult(null);
    try {
      const cptCode = PROCEDURE_TO_CPT[patientForm.procedure] || "73721";
      const payload = {
        ...patientForm,
        cpt_code: cptCode,
      };
      const envelope = await estimatePatientCost({ sessionId, input: payload });
      setPatientResult(envelope.output || null);
      setPatientSubmittedInput(payload);
    } catch (err) {
      setPatientError(err.message || "Patient workflow failed.");
    } finally {
      setPatientLoading(false);
    }
  };

  const handleHospitalSubmit = async (e) => {
    e.preventDefault();
    setHospitalError("");
    setHospitalLoading(true);
    setReevalMessage("");
    try {
      const envelope = await predictHospitalDenial({ sessionId, input: hospitalForm });
      setHospitalEnvelope(envelope);
      setHospitalPreRisk(Number(envelope?.output?.denial_score?.risk_pct ?? 0));
      setSelectedFixIndex(0);
    } catch (err) {
      setHospitalError(err.message || "Hospital workflow failed.");
    } finally {
      setHospitalLoading(false);
    }
  };

  const handleApplyFix = async () => {
    if (!hospitalEnvelope?.run_id || !hospitalResult) {
      setHospitalError("No hospital result found. Run denial prediction before applying a fix.");
      return;
    }

    const fixList = hospitalResult.fix_list || [];
    if (!fixList.length || selectedFixIndex < 0 || selectedFixIndex >= fixList.length) {
      return;
    }

    const appliedFixes = fixList.map((fix, idx) => ({ ...fix, applied: idx === selectedFixIndex ? true : !!fix.applied }));

    setFixApplying(true);
    setHospitalError("");
    setReevalMessage("");
    try {
      const envelope = await reevaluateHospitalRun({
        runId: hospitalEnvelope.run_id,
        payload: {
          base_run_id: hospitalEnvelope.run_id,
          selected_fix_index: selectedFixIndex,
          applied_fixes: appliedFixes,
        },
      });
      setHospitalEnvelope(envelope);
      const oldRisk = Number(hospitalPreRisk || 0);
      const newRisk = Number(envelope?.output?.denial_score?.risk_pct ?? 0);
      setReevalMessage(`Risk updated: ${(oldRisk * 100).toFixed(0)}% -> ${(newRisk * 100).toFixed(0)}%`);
    } catch (err) {
      setHospitalError(err.message || "Re-evaluation failed.");
    } finally {
      setFixApplying(false);
    }
  };

  return (
    <div className="app-shell" style={{ display: "flex", gap: 20, padding: 20, minHeight: "100dvh", background: T.bg, fontFamily: F.body, color: T.text }}>
      <Styles />
      <Sidebar tab={tab} setTab={setTab} />
      <div className="main-content" style={{ flex: 1, width: "100%", maxWidth: "none", minHeight: "calc(100dvh - 40px)", display: "flex", flexDirection: "column" }}>
        {tab === "patient" ? (
          <div style={{ animation: "fadeUp 0.4s ease both", flex: 1, display: "flex", flexDirection: "column" }}>
            <div className="au" style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 10, flexWrap: "wrap" }}>
              <div>
                <div style={{ fontSize: 22, fontWeight: 800, fontFamily: F.display, color: T.text }}>Patient Cost Estimator</div>
                <div style={{ fontSize: 13, color: T.textMuted, marginTop: 2 }}>Know what you pay before you go</div>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {patientChips.map((chip, idx) => <Chip key={`${chip}-${idx}`} text={chip} color={idx === 0 ? T.accent : T.textMuted} />)}
              </div>
            </div>

            <div className="two-col-grid" style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 16, marginBottom: 20, flex: 1, alignItems: "stretch" }}>
              <PatientForm form={patientForm} setForm={setPatientForm} loading={patientLoading} onSubmit={handlePatientSubmit} />
              <div style={{ display: "flex", flexDirection: "column", gap: 16, minHeight: 0 }}>
                {patientError ? <div style={{ background: T.redBg, border: `1px solid ${T.red}33`, borderRadius: 12, padding: 14, color: "#f3aaaa", fontSize: 13 }}>{patientError}</div> : null}
                {patientLoading ? <div className="au3" style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: 16, color: T.textSoft }}>Running patient cost workflow...</div> : null}
                {patientResult ? (
                  <PatientResults result={patientResult} submittedInput={patientSubmittedInput} />
                ) : (
                  <div className="au3" style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: 18, color: T.textSoft, fontSize: 14 }}>
                    Submit the patient form to render backend-backed estimate cards and details.
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ animation: "fadeUp 0.4s ease both", flex: 1, display: "flex", flexDirection: "column" }}>
            <div className="au" style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 10, flexWrap: "wrap" }}>
              <div>
                <div style={{ fontSize: 22, fontWeight: 800, fontFamily: F.display, color: T.text }}>Claim Denial Predictor</div>
                <div style={{ fontSize: 13, color: T.textMuted, marginTop: 2 }}>Catch issues before you submit</div>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {hospitalChips.map((chip, idx) => <Chip key={`${chip}-${idx}`} text={chip} color={idx === 0 ? T.accent : T.textMuted} />)}
              </div>
            </div>

            <div className="two-col-grid" style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 16, flex: 1, alignItems: "stretch" }}>
              <HospitalForm form={hospitalForm} setForm={setHospitalForm} loading={hospitalLoading} onSubmit={handleHospitalSubmit} />
              <div style={{ display: "flex", flexDirection: "column", gap: 16, minHeight: 0 }}>
                {hospitalError ? <div style={{ background: T.redBg, border: `1px solid ${T.red}33`, borderRadius: 12, padding: 14, color: "#f3aaaa", fontSize: 13 }}>{hospitalError}</div> : null}
                {hospitalLoading ? <div className="au3" style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: 16, color: T.textSoft }}>Running hospital denial workflow...</div> : null}
                {reevalMessage ? <div style={{ background: T.tealBg, border: `1px solid ${T.teal}33`, borderRadius: 12, padding: 14, color: T.teal, fontSize: 13 }}>{reevalMessage}</div> : null}
                {hospitalResult ? (
                  <HospitalResults
                    result={hospitalResult}
                    preRisk={hospitalPreRisk}
                    selectedFixIndex={selectedFixIndex}
                    setSelectedFixIndex={setSelectedFixIndex}
                    onApplyFix={handleApplyFix}
                    applyingFix={fixApplying}
                  />
                ) : (
                  <div className="au3" style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: 18, color: T.textSoft, fontSize: 14 }}>
                    Submit the hospital form to render backend-backed denial analysis and fix list.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <footer style={{ marginTop: "auto", padding: "14px 0", borderTop: `1px solid ${T.borderSub}`, display: "flex", gap: 12, fontSize: 11, fontFamily: F.mono, color: T.textDim, flexWrap: "wrap" }}>
          <span>CMS Price Transparency</span><span style={{ color: T.border }}>|</span><span>NCCI Coding Rules</span><span style={{ color: T.border }}>|</span><span>Benefits simulated</span><span style={{ color: T.border }}>|</span><span>FastAPI + LangGraph</span>
        </footer>
      </div>
    </div>
  );
}

