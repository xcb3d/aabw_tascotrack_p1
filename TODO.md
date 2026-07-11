# My Tasco Secure Agentic RAG — Implementation TODO

Scaffold is complete. Every item below is a pick-up task for parallel team work.
Ownership follows architecture ownership: **BE / AIE1 / AIE2 / AIE3 / FS**.

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## BE — Backend platform (API composition root, auth, infra)

### Config & composition root
- [ ] Wire real JWT validation in `apps/api/src/dependencies.py::get_current_subject`
- [ ] Implement Idempotency-Key Redis cache/replay in `require_idempotency_key`
- [ ] Configure OpenTelemetry resource + exporters in `apps/api/src/main.py` lifespan
- [ ] Map all HTTPException paths to COP `ErrorEnvelope` (not FastAPI default)
- [ ] Add structured logging middleware that binds `requestId` on every log line

### Database & migrations
- [ ] Author first Alembic revision for Document, Chunk, AuditEvent, AgentRun, Action, Session
- [ ] Enable `pgvector` extension in migration
- [ ] Confirm embedding dimension against model registry (currently 1536)
- [ ] Add ACL / version / status columns to Document
- [ ] Seed non-sensitive demo data under `database/seeds/`

### Documents API (`apps/api/src/routes/documents/`)
- [ ] `listDocuments` — paginated ACL-aware inventory
- [ ] `createDocument` — multipart upload, metadata, enqueue ingestion job
- [ ] `createDocumentVersion` — immutable version + re-ingestion
- [ ] `publishDocument` / `archiveDocument` — status transitions

### Chat / runs API (`apps/api/src/routes/chat/`)
- [ ] `createChatSession` — persist Session, return SessionEnvelope
- [ ] `createAgentRun` — accept run, enqueue worker, return 202 AgentRunEnvelope
- [ ] `getAgentRun` — load owned run state
- [ ] `streamAgentRunEvents` — SSE status-only stream (no answer tokens)
- [ ] `cancelAgentRun` — signal cancellation on state machine

### Actions API (`apps/api/src/routes/actions/`)
- [ ] `getActionPreview` — immutable preview load
- [ ] `confirmAction` — token verify + idempotent execute
- [ ] `rejectAction` — mark rejected without upstream mutation

### Worker infra (`apps/worker/`)
- [ ] Job queue consumer loop (Redis/streams or Postgres SKIP LOCKED)
- [ ] Wire `run_job` / `ingest_job` / `eval_job` entrypoints to queue
- [ ] Graceful shutdown and retry policy

### Tests (BE)
- [ ] Integration health test against `docker compose` Postgres + Redis
- [ ] Contract tests for ErrorEnvelope / App-Code middleware
- [ ] Idempotency key unit tests


## FS — Full-stack / DX / contracts

### Contracts layer
- [ ] Thin re-exports or typed protocols under each `modules/*/contracts/`
- [ ] Keep `openapi.yaml` as source of truth; add codegen later if needed

### Web / Flutter (out of current scaffold scope, tracked for planning)
- [ ] `apps/web` BFF client for chat sessions/runs + SSE
- [ ] Action confirm/reject UX with confirmation token
- [ ] `apps/flutter_adapter` package surface

### DX
- [ ] `.env.example` with non-secret defaults
- [ ] `scripts/` smoke: compose up → migrate → health curl
- [ ] CI: import check, pytest, openai URL grep, ruff/mypy

---

## Shared / cross-cutting checklist

- [x] Monorepo skeleton + FastAPI composition root
- [x] Pydantic schemas from OpenAPI
- [x] Router stubs for all OpenAPI operationIds
- [x] Real `GET /health` (DB + Redis probe)
- [x] Module service stubs
- [x] Worker job stubs
- [x] docker-compose (pgvector + redis)
- [x] pyproject.toml + alembic skeleton
- [x] Placeholder tests + this TODO
- [ ] First real Alembic revision
- [ ] JWT auth end-to-end
- [ ] First end-to-end agent run (create → worker → get/SSE)
- [ ] Security invariants S1–S12 as release gate
