# Backend and Core AI Operations

## Local startup

1. Copy `.env.example` to `.env` and replace development keys.
2. Start PostgreSQL/pgvector and Redis with `docker compose up -d`.
3. Apply migrations with `alembic upgrade head`.
4. Start the API with `python -m uvicorn apps.api.src.main:app --host 127.0.0.1 --port 8000`.
5. Start the worker in another process with `python -m apps.worker.src.consumer`.

Run `powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1` for the automated migration and health smoke test.

## Production gates

- Use a 32-byte-or-longer JWT verification key and confirmation signing key.
- Set `MOCK_ADAPTERS_ENABLED=false`; install real adapters behind the typed tool interfaces before enabling business operations.
- Set `INTERNAL_EMBEDDINGS_ENABLED=true` and pre-cache the pinned Qwen model in the private worker environment.
- Configure `OBJECT_STORAGE_BACKEND=s3`, bucket, endpoint/region, encryption, lifecycle, and least-privilege credentials.
- Keep `OPENAI_ENABLED=false` until the project, model, and complete request shape are contractually and operationally verified for ZDR. Then set the approved model and `OPENAI_ZDR_VERIFIED=true`.
- Configure the OTLP HTTP trace endpoint, database backups, Redis availability, rate limits, and secret rotation.

Production startup fails when these security requirements are inconsistent.

## Corpus and steward workflow

- Upload UTF-8 Markdown or text through the Documents API. Originals go to object storage; metadata, immutable versions, chunks, annotations, and vectors go to PostgreSQL.
- A version moves through `processing → ready → active`. Publishing archives the prior active version atomically.
- DLP-blocked or malformed content becomes `quarantined`, records `quarantine_reasons`, sets `steward_review_required`, and is never indexed or published.
- Review `qa_metrics` before publishing: content-hash verification, chunk/word/embedding counts, PII annotations, and prompt-injection annotations.
- To retry a corrected document, upload a new immutable version. Do not alter quarantined source rows.

## Re-index and rollback

- Development re-index: call the protected `index/rebuild` endpoint; the worker rebuilds active/ready versions idempotently.
- Production re-index: enqueue equivalent governed ingestion jobs through an operator command or administration service; the demo endpoint is disabled.
- Roll back application code first, then use `alembic downgrade <revision>` only after verifying compatibility and taking a database backup.
- Document versions are immutable. Content rollback publishes a previously reviewed version through a new governed version transition rather than rewriting history.

## Incident controls

- Disable OpenAI immediately with `OPENAI_ENABLED=false` or revoke the service-account key.
- Stop writes by disabling action tools; already-issued confirmation tokens remain subject to expiry, policy-version, identity, hash, and one-time-use validation.
- Inspect content-free audit, trace, and security-event APIs. Prompts, evidence text, raw tool payloads, chain-of-thought, and secrets are intentionally unavailable.
- Stale `RUNNING` jobs are reclaimed after five minutes. Exhausted jobs enter `DEAD` and require operator review before replay.
