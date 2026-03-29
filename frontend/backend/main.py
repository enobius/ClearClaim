from __future__ import annotations

import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional fallback
    load_dotenv = None


class PatientInput(BaseModel):
    procedure: str | None = None
    cpt_code: str
    zip_code: str
    insurance_type: str
    provider_type: str
    urgency: str
    deductible_status: str


class HospitalInput(BaseModel):
    cpt_code: str
    icd_code: str
    payer: str
    clinical_note: str


class RequestContext(BaseModel):
    source: str | None = None
    timezone: str | None = None


class WorkflowRequest(BaseModel):
    client_request_id: str | None = None
    session_id: str = Field(min_length=1)
    mode: Literal["patient", "hospital"]
    input: dict[str, Any]
    context: RequestContext | None = None


class ReevaluateRequest(BaseModel):
    base_run_id: str
    selected_fix_index: int | None = None
    applied_fixes: list[dict[str, Any]] = Field(default_factory=list)


class RunEnvelope(BaseModel):
    run_id: str
    session_id: str
    mode: Literal["patient", "hospital"]
    status: Literal["completed", "failed"]
    workflow_version: str
    input: dict[str, Any]
    output: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    completed_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_clearclaim_root() -> Path:
    env_value = os.getenv("CLEARCLAIM_ROOT")
    if env_value:
        return Path(env_value).resolve()
    here = Path(__file__).resolve()
    candidate_repo_root = here.parents[2]  # .../ClearClaim
    if (candidate_repo_root / "graph.py").exists():
        return candidate_repo_root
    return (candidate_repo_root / "ClearClaim").resolve()


def load_environment() -> None:
    if load_dotenv is None:
        return

    backend_env = Path(__file__).resolve().parent / ".env"
    clearclaim_env = resolve_clearclaim_root() / ".env"

    # Backend-local vars take precedence; ClearClaim .env fills gaps.
    if clearclaim_env.exists():
        load_dotenv(clearclaim_env, override=False)
    if backend_env.exists():
        load_dotenv(backend_env, override=False)


def resolve_db_path() -> Path:
    env_value = os.getenv("CLEARCLAIM_DB_PATH")
    if env_value:
        return Path(env_value).resolve()
    return (Path(__file__).resolve().parent / "data" / "clearclaim.db").resolve()


def connect_db() -> sqlite3.Connection:
    if not hasattr(app.state, "db_path"):
        init_db()
    conn = sqlite3.connect(app.state.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    db_path = resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    app.state.db_path = str(db_path)
    conn = connect_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                workflow_version TEXT NOT NULL,
                input_json TEXT NOT NULL,
                output_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                messages_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runs_session_created
            ON runs (session_id, created_at)
            """
        )
        conn.commit()
    finally:
        conn.close()


def load_graph_app():
    root = resolve_clearclaim_root()
    graph_path = root / "graph.py"
    if not graph_path.exists():
        raise RuntimeError(f"graph.py not found at {graph_path}")
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from graph import build_graph  # type: ignore

    return build_graph()


def invoke_graph(payload: dict[str, Any]) -> dict[str, Any]:
    graph_app = getattr(app.state, "graph_app", None)
    if graph_app is None:
        graph_app = load_graph_app()
        app.state.graph_app = graph_app
    return graph_app.invoke(payload)


def row_to_envelope(row: sqlite3.Row) -> RunEnvelope:
    return RunEnvelope(
        run_id=row["run_id"],
        session_id=row["session_id"],
        mode=row["mode"],
        status=row["status"],
        workflow_version=row["workflow_version"],
        input=json.loads(row["input_json"]),
        output=json.loads(row["output_json"]),
        warnings=json.loads(row["warnings_json"]),
        messages=json.loads(row["messages_json"]),
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


def save_run(envelope: RunEnvelope) -> None:
    conn = connect_db()
    try:
        conn.execute(
            """
            INSERT INTO runs (
                run_id, session_id, mode, status, workflow_version, input_json, output_json,
                warnings_json, messages_json, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                envelope.run_id,
                envelope.session_id,
                envelope.mode,
                envelope.status,
                envelope.workflow_version,
                json.dumps(envelope.input),
                json.dumps(envelope.output),
                json.dumps(envelope.warnings),
                json.dumps(envelope.messages),
                envelope.created_at,
                envelope.completed_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_run_or_none(run_id: str) -> RunEnvelope | None:
    conn = connect_db()
    try:
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return row_to_envelope(row)
    finally:
        conn.close()


def list_session_runs(session_id: str) -> list[RunEnvelope]:
    conn = connect_db()
    try:
        rows = conn.execute(
            "SELECT * FROM runs WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
        return [row_to_envelope(r) for r in rows]
    finally:
        conn.close()


def create_envelope(
    session_id: str,
    mode: Literal["patient", "hospital"],
    request_input: dict[str, Any],
    output: dict[str, Any],
) -> RunEnvelope:
    now = utc_now()
    envelope = RunEnvelope(
        run_id=f"run_{uuid.uuid4().hex[:12]}",
        session_id=session_id,
        mode=mode,
        status="completed",
        workflow_version="2026-03-29",
        input=request_input,
        output=output,
        warnings=[],
        messages=list(output.get("messages", [])),
        created_at=now,
        completed_at=now,
    )
    save_run(envelope)
    return envelope


def enforce_payable_total_contract(output: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    out = dict(output)
    cost_estimate = dict(out.get("cost_estimate", {}))

    insurance_low = float(cost_estimate.get("insurance_low", 0.0))
    insurance_high = float(cost_estimate.get("insurance_high", 0.0))
    oop_low = float(cost_estimate.get("oop_low", 0.0))
    oop_high = float(cost_estimate.get("oop_high", 0.0))

    original_total_low = float(cost_estimate.get("total_low", 0.0))
    original_total_high = float(cost_estimate.get("total_high", 0.0))
    payable_total_low = insurance_low + oop_low
    payable_total_high = insurance_high + oop_high

    corrected = (original_total_low != payable_total_low) or (original_total_high != payable_total_high)

    cost_estimate["market_total_low"] = original_total_low
    cost_estimate["market_total_high"] = original_total_high
    cost_estimate["total_low"] = payable_total_low
    cost_estimate["total_high"] = payable_total_high
    out["cost_estimate"] = cost_estimate
    return out, corrected


app = FastAPI(title="ClearClaim Option A API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:10]}"
    response: Response = await call_next(request)
    response.headers["x-request-id"] = req_id
    return response


@app.on_event("startup")
def startup() -> None:
    load_environment()
    app.state.graph_app = None
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/patient/estimate", response_model=RunEnvelope)
def patient_estimate(req: WorkflowRequest) -> RunEnvelope:
    if req.mode != "patient":
        raise HTTPException(status_code=400, detail="mode must be patient")
    try:
        patient_input = PatientInput.model_validate(req.input).model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    payload = {"mode": "patient", "patient_input": patient_input, "messages": []}
    output = invoke_graph(payload)
    output, corrected = enforce_payable_total_contract(output)
    if corrected:
        messages = list(output.get("messages", []))
        messages.append(
            {
                "role": "system",
                "content": "API: corrected patient total range to payable contract (insurance + oop).",
            }
        )
        output["messages"] = messages
    return create_envelope(req.session_id, "patient", payload["patient_input"], output)


@app.post("/api/v1/hospital/denial", response_model=RunEnvelope)
def hospital_denial(req: WorkflowRequest) -> RunEnvelope:
    if req.mode != "hospital":
        raise HTTPException(status_code=400, detail="mode must be hospital")
    try:
        hospital_input = HospitalInput.model_validate(req.input).model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    payload = {"mode": "hospital", "hospital_input": hospital_input, "messages": []}
    output = invoke_graph(payload)
    return create_envelope(req.session_id, "hospital", payload["hospital_input"], output)


@app.post("/api/v1/hospital/{run_id}/reevaluate", response_model=RunEnvelope)
def hospital_reevaluate(run_id: str, req: ReevaluateRequest) -> RunEnvelope:
    base_run = get_run_or_none(run_id)
    if not base_run:
        raise HTTPException(status_code=404, detail="run not found")
    if base_run.mode != "hospital":
        raise HTTPException(status_code=400, detail="run is not hospital mode")

    current_output = dict(base_run.output)
    fix_list = (
        [dict(fix) for fix in req.applied_fixes]
        if req.applied_fixes
        else [dict(fix) for fix in current_output.get("fix_list", [])]
    )
    if req.selected_fix_index is not None and 0 <= req.selected_fix_index < len(fix_list):
        fix_list[req.selected_fix_index]["applied"] = True

    payload = dict(current_output)
    payload["fix_list"] = fix_list
    payload["reeval"] = True
    payload["messages"] = []

    output = invoke_graph(payload)
    return create_envelope(base_run.session_id, "hospital", base_run.input, output)


@app.get("/api/v1/runs/{run_id}", response_model=RunEnvelope)
def get_run(run_id: str) -> RunEnvelope:
    run = get_run_or_none(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.get("/api/v1/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    runs = list_session_runs(session_id)
    return {
        "session_id": session_id,
        "run_ids": [r.run_id for r in runs],
        "runs": [r.model_dump() for r in runs],
    }
