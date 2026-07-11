# AIE1 execution plan — Knowledge ingestion

## Outcome

AIE1 delivers a deterministic, versioned, Vietnamese-first ingestion path that converts approved source documents into security-bound chunks ready for BM25 and pgvector indexing. The participant workbook is synthetic demo/evaluation data; it must not be treated as a production identity or authorization authority.

The Phase 2 embedding/index decisions are locked in `docs/AIE1_PHASE2_DESIGN.md`: internal `Qwen/Qwen3-Embedding-0.6B`, 512-dimensional normalized cosine vectors, BM25 + vector retrieval, AIE2-owned RRF/reranking, and OpenAI only after evidence and egress controls.

## Dataset baseline (11 July 2026)

- Primary source: `package/ai_workspace_dataset_vietnamese_participants.xlsm`.
- Primary content sheet: `Documents`; required companion sheet: `Document_Metadata`.
- Expected input: 40 Vietnamese documents, with unique `document_id` values and a metadata row for every document.
- Security fields carried into every chunk: department, classification, and allowed access.
- Supported classification taxonomy: Public, Internal, Confidential, Restricted. `Secret` is not indexable and any unknown value is quarantined.
- Supported access bootstrap values: All, All Employees, Own Department, Executive Only. Production authorization remains the Policy Engine's responsibility.

## Work breakdown and gates

| Stage | AIE1 deliverable | Dependency / reviewer | Exit gate |
|---|---|---|---|
| 0. Corpus baseline | Workbook profile, format decision, taxonomy, validation rules | Data steward; AIE3 evaluates | Counts and joins reproduce workbook validation report |
| 1. Intake | Macro-safe XLSM reader, canonical document/version model, deterministic source hash | BE storage contract | Invalid/mismatched rows quarantine; no partial silent indexing |
| 2. Parsing and chunking | Markdown heading-aware Vietnamese chunks with provenance and security metadata | AIE2 retrieval interface | Stable chunk IDs; no chunk mixes documents, versions, ACLs, or classifications |
| 3. Persistence | Immutable document versions, ingestion jobs, object references, atomic publish | BE migration/object storage | Failed jobs leave previous active version searchable; new version publishes atomically |
| 4. Indexing | Internal embedding adapter, BM25 fields, pgvector writes, index version metadata | AIE2/AIE3 model benchmark | Index can be rebuilt deterministically; Restricted/Confidential never use hosted embeddings |
| 5. QA and tuning | Ingestion QA report, quarantine workflow, entity aliases, corpus expansion | AIE3 benchmark; steward sign-off | M1 gates: version accuracy, citation provenance, ACL isolation, Vietnamese retrieval quality |
| 6. Production handoff | Connector runbook, steward workflow, re-index/rollback procedure | BE operations | Production corpus accepted and rollback drill passes |

## Current implementation slice

The first executable slice includes:

- `modules/knowledge/src/ingestion/workbook.py`: validated `Documents` + `Document_Metadata` intake.
- `modules/knowledge/src/ingestion/chunking.py`: deterministic Markdown-aware chunks.
- `scripts/prepare_aie1_dataset.py`: reproducible JSONL seed artifacts and corpus profile.
- `database/seeds/aie1/`: normalized documents, chunks, quarantine output, and profile.
- `tests/test_aie1_ingestion.py`: corpus contract, metadata propagation, and quarantine tests.
- `modules/knowledge/src/embeddings/qwen3.py`: internal CUDA/CPU Qwen3 inference with pinned revision, 512-dimensional projection, and normalization.
- `apps/worker/src/jobs/ingestion/embed_dataset.py`: runnable batch command with validation, atomic output, dry-run, and provenance manifest.
- `database/seeds/aie1/embeddings.jsonl`: 361 validated synthetic-demo vectors generated from the participant corpus.

## Next implementation sequence

1. Agree with BE on `documents`, `document_versions`, `chunks`, `chunk_acl`, and `ingestion_jobs` schemas; replace the prototype's direct `Chunk.document_id` shape with version-bound foreign keys.
2. Add an ingestion state machine: received → validating → parsing → classifying → chunking → embedding → QA → active/quarantined/failed.
3. Benchmark the implemented 512-dimensional Qwen3 projection against its native 1024-dimensional output and record the AIE3 acceptance decision.
4. Add PostgreSQL full-text/BM25-compatible fields and pgvector bulk upsert under an index version; publication must be atomic.
5. Hand AIE2 a read-only retrieval contract that requires tenant/ACL predicates before scoring and supports result-level reauthorization.
6. Add malformed workbook, duplicate ID, metadata mismatch, version replacement, interrupted publish, and cross-tenant seed tests.

## Definition of done for AIE1

- Every indexed chunk is traceable to source sheet/row, document, immutable version, checksum, heading path, classification, department, and access bootstrap.
- Re-ingesting identical input is idempotent; changed content creates a new immutable version.
- Unknown or inconsistent security metadata fails closed into quarantine.
- Index publication is atomic and rollback-safe.
- Embeddings for Confidential/Restricted data are internal; Restricted content has no hosted-model path.
- AIE3's Vietnamese benchmark and security leakage tests pass, with steward sign-off on classification.
