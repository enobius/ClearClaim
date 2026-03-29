import {
  MOCK_HOSPITAL_OUTPUT,
  MOCK_HOSPITAL_REEVAL_OUTPUT,
  MOCK_PATIENT_OUTPUT,
} from "./mockData";

const API_MODE = (import.meta.env.VITE_API_MODE || "live").toLowerCase();
const USE_MOCK_API = API_MODE === "mock";
const NETWORK_DELAY_MS = 180;

const runs = new Map();
const sessions = new Map();

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function nowIso() {
  return new Date().toISOString();
}

function nextRunId() {
  return `run_${Math.random().toString(36).slice(2, 10)}`;
}

function registerRun(envelope) {
  runs.set(envelope.run_id, envelope);
  const existing = sessions.get(envelope.session_id) || [];
  existing.push(envelope.run_id);
  sessions.set(envelope.session_id, existing);
  return envelope;
}

function makeEnvelope({ runId, sessionId, mode, input, output }) {
  const ts = nowIso();
  return {
    run_id: runId,
    session_id: sessionId,
    mode,
    status: "completed",
    workflow_version: "2026-03-29",
    input,
    output,
    warnings: [],
    messages: output?.messages || [],
    created_at: ts,
    completed_at: ts,
  };
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function mockResolve(factory) {
  await wait(NETWORK_DELAY_MS);
  return factory();
}

async function request(path, { method = "GET", body } = {}) {
  if (USE_MOCK_API) {
    return mockResolve(() => {
      if (path === "/api/v1/patient/estimate" && method === "POST") {
        const runId = nextRunId();
        const input = body?.input || {};
        const output = deepClone(MOCK_PATIENT_OUTPUT);
        output.patient_input = {
          cpt_code: input.cpt_code ?? output.patient_input.cpt_code,
          zip_code: input.zip_code ?? output.patient_input.zip_code,
          insurance_type: input.insurance_type ?? output.patient_input.insurance_type,
          provider_type: input.provider_type ?? output.patient_input.provider_type,
          urgency: input.urgency ?? output.patient_input.urgency,
          deductible_status: input.deductible_status ?? output.patient_input.deductible_status,
        };
        const envelope = makeEnvelope({
          runId,
          sessionId: body?.session_id || "sess_mock",
          mode: "patient",
          input,
          output,
        });
        return registerRun(envelope);
      }

      if (path === "/api/v1/hospital/denial" && method === "POST") {
        const runId = nextRunId();
        const input = body?.input || {};
        const output = deepClone(MOCK_HOSPITAL_OUTPUT);
        output.hospital_input = {
          cpt_code: input.cpt_code ?? output.hospital_input.cpt_code,
          icd_code: input.icd_code ?? output.hospital_input.icd_code,
          payer: input.payer ?? output.hospital_input.payer,
          clinical_note: input.clinical_note ?? output.hospital_input.clinical_note,
        };
        const envelope = makeEnvelope({
          runId,
          sessionId: body?.session_id || "sess_mock",
          mode: "hospital",
          input,
          output,
        });
        return registerRun(envelope);
      }

      if (path.startsWith("/api/v1/hospital/") && path.endsWith("/reevaluate") && method === "POST") {
        const runId = path.split("/")[4];
        const prior = runs.get(runId);
        if (!prior) throw new Error("run not found");
        const nextRunIdValue = nextRunId();
        const output = deepClone(MOCK_HOSPITAL_REEVAL_OUTPUT);
        if (Array.isArray(body?.applied_fixes) && body.applied_fixes.length) {
          output.fix_list = body.applied_fixes.map((f, idx) => ({
            ...f,
            applied: body?.selected_fix_index === idx ? true : !!f.applied,
          }));
        }
        const envelope = makeEnvelope({
          runId: nextRunIdValue,
          sessionId: prior.session_id,
          mode: "hospital",
          input: prior.input,
          output,
        });
        return registerRun(envelope);
      }

      if (path.startsWith("/api/v1/runs/") && method === "GET") {
        const runId = path.split("/").pop();
        const run = runs.get(runId);
        if (!run) throw new Error("run not found");
        return deepClone(run);
      }

      if (path.startsWith("/api/v1/sessions/") && method === "GET") {
        const sessionId = path.split("/").pop();
        const runIds = sessions.get(sessionId) || [];
        return {
          session_id: sessionId,
          run_ids: deepClone(runIds),
          runs: runIds.map((id) => deepClone(runs.get(id))).filter(Boolean),
        };
      }

      throw new Error(`Unsupported mock route: ${method} ${path}`);
    });
  }

  const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const requestId = `req_${Math.random().toString(36).slice(2, 12)}`;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", "x-request-id": requestId },
    body: body ? JSON.stringify(body) : undefined,
  });

  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = payload?.detail;
    if (typeof detail === "string") throw new Error(detail);
    if (Array.isArray(detail)) throw new Error(detail.map((d) => d.msg || JSON.stringify(d)).join("; "));
    throw new Error(`Request failed (${res.status})`);
  }
  return payload;
}

export function estimatePatientCost({ sessionId, input }) {
  return request("/api/v1/patient/estimate", {
    method: "POST",
    body: {
      client_request_id: crypto.randomUUID?.() || `req_${Date.now()}`,
      session_id: sessionId,
      mode: "patient",
      input,
      context: { source: "react-web" },
    },
  });
}

export function predictHospitalDenial({ sessionId, input }) {
  return request("/api/v1/hospital/denial", {
    method: "POST",
    body: {
      client_request_id: crypto.randomUUID?.() || `req_${Date.now()}`,
      session_id: sessionId,
      mode: "hospital",
      input,
      context: { source: "react-web" },
    },
  });
}

export function reevaluateHospitalRun({ runId, payload }) {
  return request(`/api/v1/hospital/${runId}/reevaluate`, {
    method: "POST",
    body: payload,
  });
}

export function getRun(runId) {
  return request(`/api/v1/runs/${runId}`);
}

export function getSession(sessionId) {
  return request(`/api/v1/sessions/${sessionId}`);
}
