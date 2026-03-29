import React, { useState, useEffect, useRef } from "react";

/* 
   DESIGN TOKENS  DARK MODE
    */
const T = {
    bg: "#0e0f0d",
    bgSub: "#141512",
    card: "#1a1b18",
    cardAlt: "#222320",
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
    coralBg: "#2d1812",

    amber: "#FFB020",
    amberBg: "#2b2210",

    green: "#78B828",
    red: "#FF4757",
    redBg: "#2b1318",
};

const F = {
    mono: `'JetBrains Mono', 'SF Mono', monospace`,
    body: `'DM Sans', system-ui, sans-serif`,
    display: `'Plus Jakarta Sans', system-ui, sans-serif`,
};

/* 
   GLOBAL STYLES
    */
const Styles = () => (
    <style>{`
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: ${T.bg}; }
    @keyframes fadeUp { from { opacity:0; transform:translateY(18px); } to { opacity:1; transform:translateY(0); } }
    @keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
    @keyframes scaleIn { from { opacity:0; transform:scale(0.92); } to { opacity:1; transform:scale(1); } }
    .au { animation: fadeUp 0.45s ease both; }
    .au1 { animation: fadeUp 0.45s ease 0.06s both; }
    .au2 { animation: fadeUp 0.45s ease 0.12s both; }
    .au3 { animation: fadeUp 0.45s ease 0.18s both; }
    .au4 { animation: fadeUp 0.45s ease 0.24s both; }
    .au5 { animation: fadeUp 0.45s ease 0.30s both; }
    .hovlift { transition: all 0.22s ease; }
    .hovlift:hover { transform: translateY(-3px); box-shadow: 0 12px 40px rgba(0,0,0,0.25); }
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-thumb { background: ${T.border}; border-radius: 3px; }
    @media (max-width: 1100px) {
      .stat-grid { grid-template-columns: 1fr 1fr !important; }
      .hospital-top-grid { grid-template-columns: 1fr 1fr !important; }
      .two-col-grid { grid-template-columns: 1fr !important; }
    }
    @media (max-width: 760px) {
      .app-shell { flex-direction: column; padding: 12px !important; gap: 12px !important; }
      .sidebar {
        width: 100% !important;
        position: static !important;
        top: auto !important;
        align-self: stretch !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        padding: 10px 12px !important;
      }
      .sidebar-logo { margin-bottom: 0 !important; }
      .sidebar-spacer { display: none !important; }
      .main-content { max-width: none !important; width: 100% !important; }
      .stat-grid { grid-template-columns: 1fr !important; }
      .hospital-top-grid { grid-template-columns: 1fr !important; }
    }
  `}</style>
);

/* 
   MINI CHARTS
    */
const Sparkline = ({ data, color, width = 100, height = 32 }) => {
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const pts = data.map((v, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((v - min) / range) * (height - 4) - 2;
        return `${x},${y}`;
    }).join(" ");
    const lastPt = pts.split(" ").pop().split(",");
    return (
        <svg width={width} height={height} style={{ display: "block" }}>
            <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx={parseFloat(lastPt[0])} cy={parseFloat(lastPt[1])} r="3" fill={color} />
        </svg>
    );
};

const MiniBar = ({ data, highlight, color, width = 120, height = 40 }) => {
    const max = Math.max(...data);
    const barW = (width / data.length) - 3;
    return (
        <svg width={width} height={height} style={{ display: "block" }}>
            {data.map((v, i) => {
                const h = (v / max) * (height - 4);
                return (
                    <rect key={i} x={i * (barW + 3)} y={height - h} width={barW} height={h}
                        rx="2" fill={i === highlight ? color : `${color}33`} />
                );
            })}
        </svg>
    );
};

const Donut = ({ pct, color, size = 64, stroke = 7 }) => {
    const r = (size - stroke) / 2;
    const c = 2 * Math.PI * r;
    return (
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={T.border} strokeWidth={stroke} />
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
                strokeDasharray={c} strokeDashoffset={c * (1 - pct / 100)}
                strokeLinecap="round" style={{ transition: "stroke-dashoffset 0.8s ease" }} />
        </svg>
    );
};

/* 
   SIDEBAR
    */
const Sidebar = ({ tab, setTab }) => (
    <div className="sidebar" style={{
        width: 64, background: T.card, borderRadius: 20, padding: "20px 0",
        display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
        position: "sticky", top: 20, alignSelf: "flex-start",
        border: `1px solid ${T.border}`,
    }}>
        <div className="sidebar-logo" style={{
            width: 36, height: 36, borderRadius: 10,
            background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 16, fontWeight: 800, color: "#fff",
            marginBottom: 24, fontFamily: F.display,
        }}>C</div>

        {[
            { key: "patient", icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z" /></svg> },
            { key: "hospital", icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="2" y="6" width="20" height="12" rx="2" /><path d="M12 2v4M12 18v4M6 12h12" /></svg> },
        ].map(it => (
            <button key={it.key} onClick={() => setTab(it.key)} style={{
                width: 44, height: 44, borderRadius: 12,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: tab === it.key ? T.accent : "transparent",
                color: tab === it.key ? "#fff" : T.textMuted,
                border: "none", cursor: "pointer", transition: "all 0.2s ease",
            }}>{it.icon}</button>
        ))}

        <div className="sidebar-spacer" style={{ flex: 1 }} />
        <button style={{ width: 44, height: 44, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", color: T.textDim, border: "none", cursor: "pointer" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="3" /><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" /></svg>
        </button>
    </div>
);

/* 
   INPUT FIELDS
    */
const Field = ({ label, value, mono }) => (
    <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 4, fontFamily: F.mono, letterSpacing: 0.5, textTransform: "uppercase" }}>{label}</div>
        <div style={{
            background: T.bgSub, border: `1px solid ${T.borderSub}`, borderRadius: 10,
            padding: "10px 14px", color: T.text, fontSize: 14,
            fontFamily: mono ? F.mono : F.body, fontWeight: 500,
            display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
            <span>{value}</span>
            <svg width="10" height="6" viewBox="0 0 10 6" fill="none"><path d="M1 1L5 5L9 1" stroke={T.textDim} strokeWidth="1.5" strokeLinecap="round" /></svg>
        </div>
    </div>
);

const NoteField = ({ label, value }) => (
    <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 4, fontFamily: F.mono, letterSpacing: 0.5, textTransform: "uppercase" }}>{label}</div>
        <div style={{ background: T.bgSub, border: `1px solid ${T.borderSub}`, borderRadius: 10, padding: "12px 14px", color: T.textSoft, fontSize: 13, lineHeight: 1.7, minHeight: 100 }}>{value}</div>
    </div>
);

/* 
   CHIPS
    */
const Chip = ({ text, color, icon }) => (
    <span style={{
        display: "inline-flex", alignItems: "center", gap: 4,
        background: `${color}18`, color,
        fontSize: 10, fontWeight: 700, fontFamily: F.mono,
        padding: "3px 10px", borderRadius: 6, letterSpacing: 1, textTransform: "uppercase",
    }}>{icon && <span style={{ fontSize: 10 }}>{icon}</span>}{text}</span>
);

const Trend = ({ value, up }) => (
    <span style={{
        display: "inline-flex", alignItems: "center", gap: 3,
        fontSize: 12, fontWeight: 600, fontFamily: F.mono,
        color: up ? T.teal : T.red,
        background: up ? T.tealBg : T.redBg,
        padding: "2px 8px", borderRadius: 20,
    }}>
        <span style={{ fontSize: 10 }}>{up ? "" : ""}</span> {value}
    </span>
);

/* 
   PATIENT MODE
    */
const PatientTab = () => (
    <div style={{ animation: "fadeUp 0.4s ease both" }}>
        <div className="au" style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
            <div>
                <div style={{ fontSize: 22, fontWeight: 800, fontFamily: F.display, color: T.text }}>Patient Cost Estimator</div>
                <div style={{ fontSize: 13, color: T.textMuted, marginTop: 2 }}>Know what you'll pay before you go</div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
                <Chip text="CPT 73721" color={T.accent} />
                <Chip text="CT / 06604" color={T.textMuted} />
            </div>
        </div>

        {/* STAT CARDS ROW */}
        <div className="au1 stat-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1.1fr", gap: 16, marginBottom: 20 }}>
            {/* Total  accent card */}
            <div className="hovlift" style={{
                background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`,
                borderRadius: 16, padding: "20px 22px", color: "#fff",
                position: "relative", overflow: "hidden",
            }}>
                <div style={{ position: "absolute", top: -20, right: -20, width: 80, height: 80, borderRadius: "50%", background: "rgba(255,255,255,0.08)" }} />
                <div style={{ fontSize: 11, fontFamily: F.mono, letterSpacing: 0.8, opacity: 0.7, marginBottom: 10, textTransform: "uppercase" }}>Estimated total</div>
                <div style={{ fontSize: 36, fontWeight: 800, fontFamily: F.display, lineHeight: 1, marginBottom: 6 }}>$886</div>
                <div style={{ fontSize: 12, opacity: 0.6, fontFamily: F.mono }}>$746  $1,127</div>
                <div style={{ marginTop: 14 }}>
                    <Sparkline data={[466, 620, 750, 886, 920, 1050, 1127]} color="rgba(255,255,255,0.5)" width={110} height={28} />
                </div>
            </div>

            {/* Insurance  coral card */}
            <div className="hovlift" style={{
                background: T.coral, borderRadius: 16, padding: "20px 22px", color: "#fff",
                position: "relative", overflow: "hidden",
            }}>
                <div style={{ position: "absolute", bottom: -10, right: -10, width: 60, height: 60, borderRadius: "50%", background: "rgba(0,0,0,0.12)" }} />
                <div style={{ fontSize: 11, fontFamily: F.mono, letterSpacing: 0.8, opacity: 0.7, marginBottom: 10, textTransform: "uppercase" }}>Insurance covers</div>
                <div style={{ fontSize: 36, fontWeight: 800, fontFamily: F.display, lineHeight: 1, marginBottom: 6 }}>$565</div>
                <div style={{ fontSize: 12, opacity: 0.6, fontFamily: F.mono }}>$453  $757</div>
                <div style={{ marginTop: 14, display: "flex", gap: 12 }}>
                    <div style={{ background: "rgba(0,0,0,0.25)", borderRadius: 6, padding: "4px 10px", fontSize: 20, fontWeight: 800, fontFamily: F.display }}>64%</div>
                    <div style={{ background: "rgba(255,255,255,0.18)", borderRadius: 6, padding: "4px 10px", fontSize: 20, fontWeight: 800, fontFamily: F.display }}>36%</div>
                </div>
                <div style={{ marginTop: 6, display: "flex", gap: 12, fontSize: 10, fontFamily: F.mono, opacity: 0.6 }}>
                    <span> Insured</span><span> You pay</span>
                </div>
            </div>

            {/* You Pay  dark card + bar chart */}
            <div className="hovlift" style={{
                background: T.card, borderRadius: 16, padding: "20px 22px",
                border: `1px solid ${T.border}`,
            }}>
                <div style={{ fontSize: 11, fontFamily: F.mono, letterSpacing: 0.8, color: T.textMuted, marginBottom: 10, textTransform: "uppercase" }}>You pay</div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                    <span style={{ fontSize: 36, fontWeight: 800, fontFamily: F.display, color: T.coral, lineHeight: 1 }}>$321</span>
                    <Trend value="+21%" up={false} />
                </div>
                <div style={{ fontSize: 12, color: T.textDim, fontFamily: F.mono, marginTop: 4 }}>$293  $370</div>
                <div style={{ marginTop: 14 }}>
                    <MiniBar data={[180, 50, 91]} highlight={2} color={T.coral} width={110} height={36} />
                    <div style={{ display: "flex", gap: 12, marginTop: 6, fontSize: 9, fontFamily: F.mono, color: T.textMuted }}>
                        <span>Deductible</span><span>Copay</span><span>Coins.</span>
                    </div>
                </div>
            </div>

            {/* Coverage donut */}
            <div className="hovlift" style={{ background: T.card, borderRadius: 16, padding: "20px 22px", border: `1px solid ${T.border}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ fontSize: 11, fontFamily: F.mono, letterSpacing: 0.8, color: T.textMuted, textTransform: "uppercase" }}>Coverage split</div>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={T.textDim} strokeWidth="2"><path d="M7 17L17 7M17 7H7M17 7v10" /></svg>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 12 }}>
                    <div style={{ position: "relative" }}>
                        <Donut pct={64} color={T.teal} size={72} stroke={8} />
                        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 800, fontFamily: F.display, color: T.text }}>64%</div>
                    </div>
                    <div>
                        {[
                            { label: "Insurer", pct: "64%", color: T.teal },
                            { label: "Deduct.", pct: "20%", color: T.coral },
                            { label: "Coinsur.", pct: "10%", color: T.amber },
                            { label: "Copay", pct: "6%", color: T.textMuted },
                        ].map((r, i) => (
                            <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, fontSize: 11, color: T.textSoft }}>
                                <span style={{ width: 8, height: 8, borderRadius: 3, background: r.color, display: "inline-block" }} />
                                <span style={{ minWidth: 56 }}>{r.label}</span>
                                <span style={{ fontFamily: F.mono, fontWeight: 600, color: T.text }}>{r.pct}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>

        {/* FORM + EXPLANATION */}
        <div className="two-col-grid" style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 16, marginBottom: 20 }}>
            <div className="au2 hovlift" style={{ background: T.card, borderRadius: 16, padding: "22px 24px", border: `1px solid ${T.border}` }}>
                <div style={{ fontSize: 11, fontFamily: F.mono, letterSpacing: 1, color: T.accent, marginBottom: 16, textTransform: "uppercase", fontWeight: 700 }}> Your details</div>
                <Field label="Procedure" value="Knee MRI" />
                <Field label="Location" value="Connecticut" />
                <Field label="Provider" value="Hospital" />
                <Field label="Insurance" value="Aetna PPO" />
                <Field label="Deductible" value="Partially met ($180 rem.)" />
                <Field label="Urgency" value="Routine" />
                <button style={{
                    width: "100%", padding: "13px 0", borderRadius: 10,
                    background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`,
                    color: "#fff", border: "none", fontSize: 14, fontWeight: 600,
                    fontFamily: F.body, cursor: "pointer", marginTop: 4,
                    boxShadow: `0 4px 16px ${T.accent}33`,
                }}>Estimate my costs</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {/* Prior auth */}
                <div className="au3" style={{
                    background: T.amberBg, borderRadius: 14, padding: "14px 18px",
                    border: `1px solid ${T.amber}25`,
                    display: "flex", alignItems: "flex-start", gap: 12,
                }}>
                    <div style={{ width: 28, height: 28, borderRadius: 8, flexShrink: 0, background: `${T.amber}20`, display: "flex", alignItems: "center", justifyContent: "center", color: T.amber, fontSize: 14, fontWeight: 800 }}>!</div>
                    <div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: T.amber, marginBottom: 2 }}>Prior Authorization Required</div>
                        <div style={{ fontSize: 12, color: T.textSoft, lineHeight: 1.6 }}>Aetna PPO requires pre-approval for Knee MRI (CPT 73721) before booking.</div>
                    </div>
                </div>

                {/* AI explanation */}
                <div className="au4 hovlift" style={{ background: T.card, borderRadius: 14, padding: "20px 22px", border: `1px solid ${T.border}`, flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                        <div style={{ width: 24, height: 24, borderRadius: 7, background: `${T.accent}18`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, color: T.accent }}></div>
                        <span style={{ fontSize: 11, fontFamily: F.mono, fontWeight: 700, color: T.textMuted, letterSpacing: 0.8, textTransform: "uppercase" }}>AI Explanation</span>
                    </div>
                    <div style={{ fontSize: 14, color: T.textSoft, lineHeight: 1.85 }}>
                        Your Knee MRI in Connecticut will cost around <strong style={{ color: T.text }}>$886</strong> at the mid-range based on CMS provider payment data.
                        Connecticut Advanced Imaging (Bridgeport) charges $1,842 submitted but Medicare allows $466  commercial insurers typically pay 1.62.2 that rate.
                        With <strong style={{ color: T.text }}>$180</strong> left on your deductible and 20% coinsurance, your out-of-pocket is approximately <strong style={{ color: T.coral }}>$321</strong>.
                    </div>
                </div>
            </div>
        </div>

        {/* SAVINGS TABLE */}
        <div className="au5 hovlift" style={{ background: T.card, borderRadius: 16, padding: "22px 24px", border: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 700, fontFamily: F.display, color: T.text }}>Ways to reduce costs</div>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={T.textDim} strokeWidth="2"><path d="M7 17L17 7M17 7H7M17 7v10" /></svg>
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                    <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                        {["", "Strategy", "Potential savings", "Effort"].map((h, i) => (
                            <th key={i} style={{ textAlign: "left", padding: "8px 12px 10px", fontSize: 10, fontFamily: F.mono, color: T.textDim, letterSpacing: 0.6, textTransform: "uppercase", fontWeight: 600 }}>{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {[
                        { tip: "Use outpatient imaging center instead of hospital", save: "Up to 40%", effort: "Low", color: T.teal },
                        { tip: "Get prior auth before booking appointment", save: "Avoid 100% bill", effort: "Medium", color: T.amber },
                        { tip: "Bundle with other planned procedures this year", save: "Deductible savings", effort: "Low", color: T.teal },
                    ].map((row, i) => (
                        <tr key={i} style={{ borderBottom: i < 2 ? `1px solid ${T.borderSub}` : "none" }}>
                            <td style={{ padding: "14px 12px", width: 40 }}>
                                <div style={{ width: 26, height: 26, borderRadius: 7, background: `${row.color}15`, color: row.color, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 800, fontFamily: F.display }}>{i + 1}</div>
                            </td>
                            <td style={{ padding: "14px 12px", color: T.text, fontWeight: 500 }}>{row.tip}</td>
                            <td style={{ padding: "14px 12px" }}><Chip text={row.save} color={row.color} /></td>
                            <td style={{ padding: "14px 12px", color: T.textMuted, fontFamily: F.mono, fontSize: 11 }}>{row.effort}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    </div>
);

/* 
   HOSPITAL MODE
    */
const HospitalTab = () => {
    const [fixed, setFixed] = useState(false);
    const [anim, setAnim] = useState(false);
    const timersRef = useRef([]);

    useEffect(() => {
        return () => {
            timersRef.current.forEach((id) => clearTimeout(id));
            timersRef.current = [];
        };
    }, []);

    const queueTimeout = (fn, ms) => {
        const id = setTimeout(fn, ms);
        timersRef.current.push(id);
    };

    const toggle = () => {
        setAnim(true);
        queueTimeout(() => {
            setFixed((f) => !f);
            queueTimeout(() => setAnim(false), 350);
        }, 120);
    };
    const riskPct = fixed ? 4 : 34;
    const riskColor = fixed ? T.teal : T.red;
    const riskLabel = fixed ? "LOW RISK" : "HIGH RISK";

    return (
        <div style={{ animation: "fadeUp 0.4s ease both" }}>
            <div className="au" style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                <div>
                    <div style={{ fontSize: 22, fontWeight: 800, fontFamily: F.display, color: T.text }}>Claim Denial Predictor</div>
                    <div style={{ fontSize: 13, color: T.textMuted, marginTop: 2 }}>Catch issues before you submit</div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                    <Chip text="CPT 73721" color={T.accent} />
                    <Chip text="ICD M17.11" color={T.textMuted} />
                </div>
            </div>

            {/* TOP ROW */}
            <div className="au1 hospital-top-grid" style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr 1fr", gap: 16, marginBottom: 20 }}>
                {/* Risk hero */}
                <div className="hovlift" style={{
                    background: fixed ? `linear-gradient(135deg, #0a6e4a, ${T.teal})` : `linear-gradient(135deg, #b5302a, ${T.coral})`,
                    borderRadius: 16, padding: "28px 26px", color: "#fff",
                    position: "relative", overflow: "hidden", transition: "all 0.5s ease",
                }}>
                    <div style={{ position: "absolute", top: -30, right: -30, width: 100, height: 100, borderRadius: "50%", background: "rgba(255,255,255,0.06)" }} />
                    <div style={{ position: "absolute", bottom: -20, left: -20, width: 70, height: 70, borderRadius: "50%", background: "rgba(0,0,0,0.1)" }} />
                    <div style={{ fontSize: 11, fontFamily: F.mono, letterSpacing: 1, opacity: 0.7, marginBottom: 10, textTransform: "uppercase", position: "relative" }}>Denial risk score</div>
                    <div style={{
                        fontSize: 72, fontWeight: 800, fontFamily: F.display, lineHeight: 1,
                        transition: "all 0.5s ease", transform: anim ? "scale(0.8)" : "scale(1)",
                        opacity: anim ? 0.3 : 1, position: "relative",
                    }}>
                        {riskPct}<span style={{ fontSize: 32, fontWeight: 600 }}>%</span>
                    </div>
                    <div style={{ marginTop: 12, position: "relative" }}>
                        <span style={{ background: "rgba(255,255,255,0.15)", color: "#fff", fontSize: 10, fontWeight: 700, fontFamily: F.mono, padding: "4px 12px", borderRadius: 6, letterSpacing: 1.2 }}>{riskLabel}</span>
                    </div>
                </div>

                {/* NCCI */}
                <div className="hovlift" style={{ background: T.card, borderRadius: 16, padding: "22px", border: `1px solid ${T.border}`, display: "flex", flexDirection: "column" }}>
                    <div style={{ fontSize: 11, fontFamily: F.mono, letterSpacing: 0.8, color: T.textMuted, marginBottom: 12, textTransform: "uppercase" }}>NCCI Validation</div>
                    <div style={{ width: 48, height: 48, borderRadius: 12, background: T.tealBg, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, color: T.teal, marginBottom: 12 }}></div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: T.text, marginBottom: 4 }}>All checks passed</div>
                    <div style={{ fontSize: 12, color: T.textMuted, lineHeight: 1.6 }}>CPT 73721 + ICD M17.11 is valid. No edit conflicts.</div>
                </div>

                {/* Risk factors donut */}
                <div className="hovlift" style={{ background: T.card, borderRadius: 16, padding: "22px", border: `1px solid ${T.border}` }}>
                    <div style={{ fontSize: 11, fontFamily: F.mono, letterSpacing: 0.8, color: T.textMuted, marginBottom: 14, textTransform: "uppercase" }}>Risk factors</div>
                    <div style={{ display: "flex", justifyContent: "center", marginBottom: 14, position: "relative" }}>
                        <Donut pct={100 - riskPct} color={riskColor} size={80} stroke={9} />
                        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 800, fontFamily: F.display, color: T.text }}>{fixed ? "1" : "2"}</div>
                    </div>
                    <div style={{ textAlign: "center", fontSize: 12, color: T.textMuted }}>{fixed ? "1 factor (base risk)" : "2 factors identified"}</div>
                    <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 10 }}>
                        <Chip text={fixed ? "Auth " : "No Auth"} color={fixed ? T.teal : T.red} />
                        <Chip text="Base 4%" color={T.textMuted} />
                    </div>
                </div>
            </div>

            {/* FORM + FIXES */}
            <div className="two-col-grid" style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 16 }}>
                <div className="au2 hovlift" style={{ background: T.card, borderRadius: 16, padding: "22px 24px", border: `1px solid ${T.border}` }}>
                    <div style={{ fontSize: 11, fontFamily: F.mono, letterSpacing: 1, color: T.accent, marginBottom: 16, textTransform: "uppercase", fontWeight: 700 }}> Claim details</div>
                    <Field label="CPT Code" value="73721" mono />
                    <Field label="ICD-10 Code" value="M17.11" mono />
                    <Field label="Payer" value="Aetna PPO" />
                    <NoteField label="Clinical note" value="Patient presents with right knee pain for 3 months. Physical exam reveals medial joint line tenderness and positive McMurray test. X-ray shows narrowing of medial compartment. MRI requested to evaluate for meniscal tear and assess cartilage damage prior to treatment planning." />
                    <button style={{
                        width: "100%", padding: "13px 0", borderRadius: 10,
                        background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`,
                        color: "#fff", border: "none", fontSize: 14, fontWeight: 600,
                        fontFamily: F.body, cursor: "pointer", marginTop: 4,
                        boxShadow: `0 4px 16px ${T.accent}33`,
                    }}>Analyze claim</button>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    {!fixed && (
                        <div className="au3" style={{
                            background: T.redBg, borderRadius: 14, padding: "16px 20px",
                            border: `1px solid ${T.red}20`,
                        }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                                <div style={{ width: 8, height: 8, borderRadius: "50%", background: T.red, boxShadow: `0 0 10px ${T.red}66` }} />
                                <span style={{ fontSize: 11, fontFamily: F.mono, fontWeight: 700, color: T.red, letterSpacing: 0.8, textTransform: "uppercase" }}>Issues found</span>
                            </div>
                            <div style={{ fontSize: 13, color: "#f09595", lineHeight: 1.7, paddingLeft: 16, borderLeft: `2px solid ${T.red}30` }}>
                                Prior authorization not on file  Aetna requires auth for advanced imaging (CPT 73721)
                                <div style={{ fontSize: 11, color: T.textMuted, fontFamily: F.mono, marginTop: 4 }}>Risk contribution: +30%</div>
                            </div>
                        </div>
                    )}

                    <div className="au4 hovlift" style={{ background: T.card, borderRadius: 14, padding: "20px 22px", border: `1px solid ${T.border}`, flex: 1 }}>
                        <div style={{ fontSize: 11, fontFamily: F.mono, letterSpacing: 1, color: T.textMuted, marginBottom: 14, textTransform: "uppercase", fontWeight: 700 }}>Fix list</div>
                        <div style={{ background: T.bgSub, borderRadius: 12, padding: 16, border: `1px solid ${T.borderSub}`, marginBottom: 16 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                                <span style={{ fontSize: 14, fontWeight: 700, color: T.text, fontFamily: F.display }}>Obtain prior authorization</span>
                                <Chip text={fixed ? "FIXED" : "28% risk"} color={fixed ? T.teal : T.amber} />
                            </div>
                            <div style={{ fontSize: 12, color: T.textMuted, lineHeight: 1.7 }}>
                                Contact Aetna provider services. Obtain auth number for CPT 73721. Attach to claim field 23 before submission.
                            </div>
                        </div>
                        <button onClick={toggle} style={{
                            width: "100%", padding: "12px 0", borderRadius: 10,
                            fontSize: 13, fontWeight: 600, fontFamily: F.body, cursor: "pointer",
                            transition: "all 0.3s ease",
                            background: fixed ? T.tealBg : `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`,
                            color: fixed ? T.teal : "#fff",
                            border: fixed ? `1px solid ${T.teal}30` : "none",
                            boxShadow: fixed ? "none" : `0 4px 16px ${T.accent}33`,
                        }}>
                            {fixed ? "Reset to original" : "Apply fix - recalculate risk"}
                        </button>
                    </div>

                    {fixed && (
                        <div style={{
                            background: T.tealBg, borderRadius: 14, padding: 16,
                            border: `1px solid ${T.teal}20`,
                            animation: "scaleIn 0.35s ease both",
                        }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                                <Chip text="CLEAN" color={T.teal} icon="" />
                            </div>
                            <div style={{ fontSize: 13, color: T.teal, lineHeight: 1.7, fontWeight: 500 }}>
                                Claim is now clean. Prior auth attached. Risk reduced from <strong>34%  4%</strong>.
                                Patient pays as expected. Hospital gets reimbursed. No surprise bill.
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

/* 
   APP SHELL
    */
export default function App() {
    const [tab, setTab] = useState("patient");

    return (
        <div className="app-shell" style={{ display: "flex", gap: 20, padding: 20, minHeight: "100vh", background: T.bg, fontFamily: F.body, color: T.text }}>
            <Styles />
            <Sidebar tab={tab} setTab={setTab} />
            <div className="main-content" style={{ flex: 1, maxWidth: 1100 }}>
                <div key={tab}>
                    {tab === "patient" ? <PatientTab /> : <HospitalTab />}
                </div>
                <footer style={{ marginTop: 32, padding: "14px 0", borderTop: `1px solid ${T.borderSub}`, display: "flex", gap: 16, fontSize: 11, fontFamily: F.mono, color: T.textDim, flexWrap: "wrap" }}>
                    <span>CMS Price Transparency</span><span style={{ color: T.border }}></span><span>NCCI Coding Rules</span><span style={{ color: T.border }}></span><span>Benefits simulated</span><span style={{ color: T.border }}></span><span>Claude API + LangGraph</span>
                </footer>
            </div>
        </div>
    );
}

