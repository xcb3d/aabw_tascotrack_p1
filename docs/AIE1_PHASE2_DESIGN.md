# AIE1 Phase 2 design — internal embedding and index publication

## 1. Locked decisions

- The embedding model is `Qwen/Qwen3-Embedding-0.6B`, executed only on enterprise-controlled infrastructure.
- The initial searchable representation is a 512-dimensional Matryoshka projection, L2-normalized and compared with cosine distance.
- All indexable classifications use the same internal embedding space. `Secret` content is blocked before chunking and embedding.
- Original and normalized files remain in enterprise object storage. PostgreSQL remains authoritative for documents, versions, ACLs, ingestion state, and audit.
- Pgvector is the first vector index. A separate self-hosted vector engine is a rebuildable projection introduced only when the scale benchmark fails the pgvector gate.
- OpenAI is not an embedder, retriever, router, authorization service, or citation authority. It receives only an approved Evidence Capsule for text generation/planning/verification.
- BM25/vector fusion and internal reranking are owned by AIE2. AIE1 guarantees stable chunk IDs, versioned embeddings, security metadata, and atomic index publication.

The registry entry is `config/models/embedding-qwen3-0.6b.json`. Development may use the symbolic revision, but staging and production must reject `PIN_BEFORE_PRODUCTION` and require an approved immutable model revision.

## 2. Data flow and trust boundaries

```text
source connector
→ file signature/type/malware validation
→ parser/OCR/table extraction
→ UTF-8 and layout normalization
→ classification + ACL mapping
→ immutable document-version resolution
→ structure-aware token chunking
→ PII/secret/injection annotation
→ Qwen3 internal embedding
→ BM25 + pgvector + metadata indexes (not yet active)
→ ingestion QA
→ atomic index-version activation

query
→ authentication + local DLP + purpose/policy decision
→ Qwen3 internal query embedding
→ ACL predicates inside BM25 and vector candidate queries
→ AIE2 RRF fusion and internal reranking
→ result-level policy/version recheck
→ Evidence Manifest and minimal Capsule
→ egress inspection
→ OpenAI generation when classification policy permits
→ claim/schema/output-DLP validation
→ backend-rendered citations
```

No hosted call occurs before the local sensitivity and egress decisions. The embedding service has no external-network route in production.

## 3. Storage and version model

PostgreSQL uses separate logical records rather than the current prototype's document-to-chunk shortcut:

| Record | Required identity and state |
|---|---|
| `documents` | `tenant_id`, stable `document_id`, owner and source connector |
| `document_versions` | `version_id`, source/content hash, effective interval, supersedes ID, parser/ACL/classification versions, lifecycle status |
| `chunks` | stable `chunk_id`, version ID, ordinal, heading/source spans, content hash, annotations, classification |
| `chunk_acl` | tenant, chunk, principal/attribute predicate or ACL reference, ACL version |
| `embedding_refs` | chunk, model ID, immutable revision, dimension, normalization, content hash, index version |
| `ingestion_jobs` | job state, attempt, lease, error code, counters and timestamps; never raw sensitive content in errors |
| `index_versions` | model/chunker/parser/config versions, build status, QA verdict, activation and rollback metadata |

The initial vector column is conceptually `halfvec(512)`. One row is uniquely identified by `(tenant_id, chunk_id, model_revision, output_dimension)`. Vectors are encrypted at rest, tenant-scoped, protected by the same retention/deletion workflow as their source, and treated as sensitive derived data.

Document-version state and ingestion-job state are separate:

```text
job: queued → validating → parsing → chunking → embedding → indexing → qa → succeeded
                                                                        └→ failed

version: draft → pending_classification → ready → active → expired/archived
                           └──────────────────────→ quarantined
```

Only `active` versions in the active index version are searchable. Building a replacement never removes the previous active version. Activation changes one transactional index pointer after QA; rollback restores the previous pointer.

## 4. Embedding contract

AIE1 exposes two internal operations:

```text
embed_documents(TextToEmbed[]) → EmbeddingRecord[]
embed_query(query, tenant_id)   → normalized float[512]
```

Rules:

- Document text is embedded without a query instruction. Query text uses the registry's fixed English retrieval instruction.
- Truncate/project to 512 dimensions according to the model's supported Matryoshka behavior, then L2-normalize.
- Reject NaN/infinite values, incorrect dimensions, empty input, unpinned production revisions, and Secret classification.
- Bind every output to tenant, chunk, document version, content hash, model ID, revision, and index version.
- Batch ingestion is idempotent. Matching content/config reuses the existing vector; any content/model/dimension/normalization change creates a new index build.
- Do not log input text or vectors. Metrics contain counts, duration, model revision, dimensions, failures, and resource utilization only.

## 5. Retrieval handoff to AIE2

AIE1 publishes enough metadata for tenant and ACL predicates to execute before scoring. AIE2 returns this stable score breakdown for evaluation and privileged trace inspection:

| Field | Meaning |
|---|---|
| `bm25_rank` | One-based position in the authorized BM25 list, or null |
| `vector_rank` | One-based position in the authorized vector list, or null |
| `fused_rank` | One-based position after RRF |
| `reranker_score` | Normalized internal reranker score in `[0,1]`, or null in degraded mode |
| `bm25_score` | Raw engine score for diagnostics; never compared directly across queries |
| `vector_similarity` | Cosine similarity for diagnostics |
| `fused_score` | RRF score used before reranking |

RRF uses `k=60` and sums `1 / (k + rank)` for each present candidate list. ACL is never a score. The normal candidate flow is BM25 top 50 plus vector top 50, stable-ID union, RRF ordering, then authorized-union reranking to top 8. If vector search is unavailable, AIE2 uses ACL-filtered BM25 and reports degraded retrieval. If reranking is unavailable, it preserves fused ordering and applies the stricter evidence threshold.

Score details are internal observability data. Public responses may expose one bounded relevance value but not permission reasons, denied-match counts, hidden-source existence, or unrestricted trace data.

## 6. OpenAI generation boundary

OpenAI receives only the approved prompt version, sanitized query, authorized minimal Evidence Capsules, route-specific strict schemas, and a privacy-preserving safety identifier. Requests set `store: false`; sensitive production use additionally requires verified project-level ZDR because `store: false` alone is not ZDR.

- Public: generation allowed after policy and egress checks.
- Internal: allowed only under approved project policy and verified ZDR.
- Confidential: default deny; only an explicit purpose-specific exception under verified ZDR.
- Restricted and Secret: never sent to OpenAI.

Model output is untrusted. The backend validates evidence IDs and claims, renders citations from the manifest, and independently authorizes every tool/action. Hosted vector stores, file search, web search, remote MCP, code interpreter, Batch API, and direct tool mutations remain disabled in v1.

## 7. QA, scale gate, and acceptance

AIE3 evaluates the 512-dimensional decision against the native 1024-dimensional Qwen3 output and the accepted multilingual baseline. The release artifact records Recall@5/20, MRR, NDCG@10, version accuracy, ACL leakage, query P95, chunks/second, peak memory, vector/index bytes, and reranking gain.

Required acceptance:

- Zero cross-tenant or unauthorized candidates reach retrieval output, reranking, capsules, or OpenAI.
- Secret input produces no chunk/vector and a security event; invalid metadata is quarantined.
- Identical input/config is idempotent; changed content or embedding configuration produces a distinct inactive index build.
- Every vector has correct dimension, finite values, expected normalization, and full provenance.
- Atomic activation and rollback pass failure injection; interrupted builds never become searchable.
- 512 dimensions must meet the agreed non-inferiority gate against 1024 on the adjudicated Vietnamese benchmark. If it fails, use 1024 and update the registry/schema before publication.
- Pgvector must meet the measured P95/QPS/recall target with production-like tenant/ACL selectivity. If it fails after partitioning, iterative scans, and half precision, preserve PostgreSQL as source of truth and move the derived index behind the same retrieval contract.

OpenAI data controls: https://developers.openai.com/api/docs/guides/your-data
