# My Tasco Secure Action Copilot — Bản đề xuất cuối (v3)
## Bản vá kiến trúc đóng các lỗ hổng còn lại + Phân công đội 5 người (3 AIE, 1 BE, 1 FS)

> **Trạng thái:** Final proposal — bộ amendment hợp nhất vào bản v2 "Final Architecture and Implementation Plan"
> **Nguyên tắc:** Không viết lại kiến trúc v2. Tài liệu này gồm (1) 10 bản vá A1–A10 dưới dạng quyết định sẵn sàng merge, (2) phần mở rộng invariant/test, (3) cơ cấu đội và WBS 24 tuần cho 3 AI Engineer, 1 Backend Engineer, 1 Full-stack Engineer, (4) 4 phụ thuộc ngoài phải khởi động ở tuần 1.
> **Hiệu lực:** Mọi mục trong v2 không bị amendment ở đây thay đổi thì giữ nguyên.

---

# PHẦN I — BẢN VÁ KIẾN TRÚC (A1–A10)

## A1 — Đưa reranker vào ma trận egress (vá lỗ hổng invariant)

**Vấn đề:** V2 mục 9.3 cho phép "approved reranker" nhưng ma trận egress 7.3 không có cột reranker. Nếu reranker là hosted API, nội dung chunk Confidential sẽ rời biên giới doanh nghiệp *trước khi* Evidence Capsule và Egress Inspector tồn tại trong pipeline — vòng qua S1/S2 mà test hiện tại không bắt được.

**Quyết định:**

1. **V1 dùng reranker nội bộ.** Cross-encoder đa ngữ/tiếng Việt chạy trên hạ tầng nội bộ (CPU/GPU nhỏ, mô hình cỡ nhỏ là đủ cho rerank top-50 → top-8). Việc chọn model dựa trên benchmark tiếng Việt ở Phase 2. Hosted reranker chỉ được cân nhắc sau GA, cho Public/Internal, sau ZDR review riêng.
2. **Ma trận 7.3 bổ sung cột Reranking:**

| Classification | Reranking |
|---|---|
| Public | Internal; hosted chỉ sau ZDR review riêng |
| Internal | Internal; hosted chỉ sau ZDR review riêng |
| Confidential | Internal bắt buộc |
| Restricted | Internal bắt buộc hoặc không rerank |
| Secret | Không áp dụng (không được index) |

3. **Quy tắc bất biến:** mọi lời gọi reranker không chạy trên hạ tầng nội bộ được coi là model egress — phải đi qua Egress Inspector và tuân cùng quy tắc classification như capsule. Không tồn tại "đường tắt reranking".
4. **Invariant table cập nhật:** S2 bổ sung enforcement point "Reranker gateway". Verification bổ sung: egress spy đặt trên endpoint reranker trong security suite.

**Tác động scope:** thêm 1 model nội bộ nhỏ (reranker, không phải generative LLM) — chi phí vận hành thấp, thuộc sở hữu AIE2/AIE3, đã nằm trong Phase 2.

---

## A2 — Ngưỡng sập cho claim removal + đánh giá verifier

**Vấn đề:** Tier 2 loại claim không được hỗ trợ nhưng không có quy tắc khi phần bị loại quá lớn hoặc là claim trung tâm — câu trả lời còn lại có thể mất mạch lạc hoặc gây hiểu sai. Verifier tự nó là model chưa được đánh giá độ tin. Với văn bản chính sách tiếng Việt, đa số claim là ngữ nghĩa (không phải số/ngày) nên verifier call thực tế xảy ra ở gần như mọi answer Tier 2.

**Quyết định:**

1. **Định nghĩa core claim:** planner đánh dấu intent chính của câu hỏi; schema synthesis yêu cầu mỗi claim gắn `intent_id`. Claim gắn với intent chính là core claim.
2. **Quy tắc sập (fail-to-insufficient):**
   - Bất kỳ core claim nào bị `UNSUPPORTED` hoặc `CONTRADICTED` → toàn bộ run trả `INSUFFICIENT_EVIDENCE`, không trả câu trả lời khuyết lõi.
   - `removed_claims / total_claims > 1/3` (cấu hình theo route) → `INSUFFICIENT_EVIDENCE`.
   - Sau khi loại claim, chạy coherence check deterministic: không còn tham chiếu treo đến claim đã loại; mỗi đoạn trả lời còn giữ ít nhất một claim có evidence. Fail → `INSUFFICIENT_EVIDENCE`.
3. **Verifier phải qua vòng loại trước khi được bật:** benchmark Phase 0/4 có nhánh riêng đo precision/recall của verifier so với nhãn adjudicated. Verifier chỉ bật production khi đạt ngưỡng thống nhất tại baseline. Nếu chưa đạt: Tier 2 tạm chạy deterministic checks + ngưỡng evidence chặt hơn, ghi `degradedReason=VERIFIER_UNAVAILABLE`.
4. **Budget Route C cập nhật:** mặc định 3 model call (plan + synthesis + verify), không phải 2. Wall-clock deadline tính theo con số này.

---

## A3 — Kế toán budget khi escalate Route B → Route C

**Vấn đề:** "Escalate once to Route C" chưa định nghĩa retrieval pass của B có tính vào budget C không, capsule có mang sang không, deadline có reset không.

**Quyết định:**

1. Escalation tối đa **một lần mỗi run**, chỉ theo hướng B → C.
2. Retrieval pass của B **được tính là round 1** của C; sau escalate C chỉ còn 1 refinement round.
3. Capsule tạo ở B **được mang sang** C sau `capsule_revalidate` (cùng `run_id`, `topic_id`, purpose — thỏa lifecycle 10.2). Không re-retrieval nếu revalidate pass.
4. **Một wall-clock deadline duy nhất cho cả run.** Escalation không reset đồng hồ, không reset token/cost budget.
5. Planning call của C sau escalate nhận **evidence summary** (evidence ID + metadata), không gửi lại nội dung capsule — tiết kiệm token và giữ S4.
6. Test bổ sung: escalated run không bao giờ vượt tổng budget của Route C; worst case `t_B + t_plan + t_refine + t_synth + t_verify ≤ ceiling(C)` được kiểm bằng failure-injection.

---

## A4 — Chốt semantics streaming

**Vấn đề:** "Chat streaming" mâu thuẫn ngầm với validation hậu kiểm: không thể stream token cho user rồi rút lại claim đã hiển thị.

**Quyết định (ghi thành ADR):**

1. **V1 không stream token của câu trả lời.** Lý do: Tier 1/2 loại claim sau khi generation hoàn tất; token streaming sẽ hiển thị nội dung chưa validate — vi phạm nguyên tắc "return or stream only validated output".
2. Streaming trong v1 = **status event streaming**: `RETRIEVING`, `CHECKING_SOURCES`, `GENERATING`, `VALIDATING`, `WAITING_CONFIRMATION`; câu trả lời đến **một lần, nguyên khối, sau VALIDATING**.
3. Contract SSE cho frontend: event types `run.status`, `run.answer` (đúng một lần), `run.action_preview`, `run.error`. Contract test khẳng định `run.answer` không bao giờ xuất hiện trước trạng thái `VALIDATING` hoàn tất và không xuất hiện quá một lần.
4. Deferred: streaming theo block-đã-validate (validate từng claim block rồi đẩy dần) — chỉ xem xét sau GA nếu số đo pilot cho thấy chờ nguyên khối gây bỏ dở phiên.

---

## A5 — Bỏ "signed cache", đơn giản hóa failure mode của Policy Engine

**Vấn đề:** "Serve only explicitly public static content from a separately signed cache" khi Policy Engine down là một component mới chưa đặc tả, tự nó mang rủi ro invariant.

**Quyết định:**

1. **Xóa option signed cache.** Failure matrix sửa thành: Policy Engine unavailable → deny toàn bộ read/write mới, trả lỗi retryable, alert mức P1. Không ngoại lệ.
2. Đổi lại, thu hẹp xác suất failure mode này về gần 0 bằng thiết kế: trong modular monolith, **policy evaluation là thư viện in-process** đọc policy snapshot đã version hóa từ PostgreSQL (có cache theo `policy_version`). PDP "unavailable" chỉ đồng nghĩa DB unavailable — cùng blast radius với toàn hệ thống, không phải failure mode mạng riêng. Điều này nhất quán với quyết định monolith ở v2 mục 3.3.

---

## A6 — Định nghĩa chính xác side effect của draft

**Vấn đề:** "Draft creation may occur without confirmation only when it has no external side effect" — chưa định nghĩa external. Nếu `request_create_draft` gọi API My Tasco tạo bản ghi draft hiển thị được trong app gốc, đó là side effect bên ngoài.

**Quyết định:**

1. **Định nghĩa:** side effect bên ngoài = bất kỳ lời gọi nào tới hệ thống upstream (My Tasco hoặc hệ thống khác) tạo, sửa, hoặc xóa bản ghi — kể cả bản ghi mang trạng thái "draft" trong hệ thống gốc.
2. `ActionDraft` của copilot **luôn lưu trong DB nội bộ** (bảng `action_drafts`), không gọi upstream → tạo draft không cần confirmation.
3. Tool `request_create_draft` v1 được định nghĩa lại là **local draft**. Nếu nghiệp vụ yêu cầu draft phải tồn tại trong My Tasco trước khi submit, tool đó đổi tên thành `request_create_confirmed` với `mode: WRITE` và đi Route D đầy đủ.
4. Test bổ sung: mock adapter đánh dấu mọi mutation upstream; suite khẳng định **zero upstream mutation trước khi confirmation token được tiêu thụ** (mở rộng verification của S6).

---

## A7 — Trần latency phía sản phẩm (tách khỏi quality target)

**Vấn đề:** "Deadline configured from measured latency" có rủi ro ratify hiện trạng — đo được bao nhiêu chấp nhận bấy nhiêu, không có ràng buộc từ phía trải nghiệm.

**Quyết định:**

1. Phân biệt hai loại con số: **quality target** (chỉ đặt sau baseline — giữ nguyên v2) và **latency ceiling** (quyết định sản phẩm, đặt trước, hiệu chỉnh sau pilot — vì đây là ràng buộc UX ta *chọn*, không phải đại lượng ta *dự đoán*).
2. Ceiling khởi điểm (P95, product owner phê duyệt thay đổi):

| Route | Ceiling P95 |
|---|---|
| A — Deterministic | 3 giây |
| B — Simple RAG | 10 giây |
| C — Agentic read (kể cả escalated) | 30 giây |
| D — Action preview | 10 giây |
| D — Confirm execution | 8 giây |

3. **Technical deadline = min(product ceiling, budget suy từ số đo).** Vượt deadline → cancel outstanding work, trả partial/insufficient với `degradedReason=DEADLINE_EXCEEDED`.
4. Pilot đo `deadline_hit_rate` theo route; nếu > 5% → tối ưu hoặc điều chỉnh ceiling có phê duyệt, không âm thầm nới.

---

## A8 — Chính sách model OpenAI: pin snapshot, phân tầng theo vai trò, cấm mặc định tính năng mới

**Bối cảnh:** GPT-5.6 (Sol/Terra/Luna) phát hành 09/07/2026 — Sol là flagship giá cao (~$5–6.5/1M input, $30–39/1M output), Terra tương đương tier mini, alias `gpt-5.6` route về Sol và có thể đổi đích. Model quá mới, chưa có track record production.

**Quyết định:**

1. **Pin dated snapshot, cấm alias** trong config registry. Đổi snapshot phải qua eval benchmark + shadow traffic.
2. **Phân tầng model theo vai trò** (điểm khởi đầu để benchmark, không phải kết luận):

| Vai trò | Model khởi điểm | Reasoning effort |
|---|---|---|
| Route B generation | `gpt-5.6-terra` (snapshot) — so sánh với Sol | low vs medium |
| Route C planning | `gpt-5.6-terra` | low |
| Route C synthesis | `gpt-5.6-sol` (snapshot) | medium |
| Verifier (Tier 2) | `gpt-5.6-terra` | low |

   Lý do: verifier là bài kiểm chứng có evidence đầy đủ, planning là bài structured output — không cần frontier model; dồn Sol cho synthesis giữ chất lượng nơi nó tạo giá trị và kiểm soát chi phí.
3. **Cost guardrail:** token budget per-run, cost budget per-tenant/ngày, alert theo project OpenAI. Sol không được dùng ngoài synthesis nếu chưa có eval chứng minh cần thiết.
4. **Mục 11.2 bổ sung cấm-mặc-định** (chỉ dùng sau threat/retention review riêng): Programmatic Tool Calling, Multi-agent (beta), pro mode, cùng danh sách đã có (hosted vector store, file search, web search, remote MCP, computer use, code interpreter, Batch API).

---

## A9 — Quyết định dứt khoát về local model: v1 KHÔNG vận hành local generative LLM

**Vấn đề:** V2 để local model làm nhánh mặc định cho Confidential, fallback khi OpenAI lỗi, và đường xử lý Restricted — nhưng không có kế hoạch chọn model, đánh giá chất lượng tiếng Việt, GPU capacity hay ops owner. Load-bearing nhưng unplanned là rủi ro khả thi lớn nhất còn lại; vận hành một private LLM production-grade cỡ ~1 FTE.

**Quyết định:**

1. **V1 không có local generative model.** (Reranker nội bộ theo A1 và embedding nội bộ vẫn giữ — chúng là model nhỏ, không phải LLM sinh văn bản.)
2. Cập nhật ma trận 7.3 và failure matrix:
   - **Confidential:** deterministic/refuse, hoặc OpenAI khi có preapproved purpose-specific ZDR exception. Bỏ nhánh "otherwise local".
   - **Restricted:** deterministic template only. Không có đường model nào.
   - **OpenAI timeout/outage:** Route B/C trả retryable failure với thông điệp rõ ràng; Route A không bị ảnh hưởng (không dùng model). Bỏ nhánh "use approved local path".
3. Local model chuyển thành hạng mục **sau GA** với ADR riêng (model selection, benchmark tiếng Việt, GPU, ops ownership).
4. **Lợi ích:** giải phóng tương đương ~1 FTE, loại một hệ thống production khỏi phạm vi 24 tuần, và làm failure matrix trung thực hơn (không hứa fallback không tồn tại).

---

## A10 — Bốn phụ thuộc ngoài trở thành hạng mục tuần 1 với owner ngoài nhóm kỹ sư

| # | Hạng mục | Owner đề xuất | Deadline | Fallback nếu trễ |
|---|---|---|---|---|
| 1 | Khởi động đàm phán/xác minh **ZDR contract** với OpenAI cho production project | Procurement/Legal + Engineering Lead | Xong trước tuần 10 (Phase 3) | Phase 3 ship Public-only; Internal giữ feature flag tắt; demo bằng corpus Public |
| 2 | **Quota adjudication** của data steward cho benchmark tiếng Việt | HR/Data Steward Manager | Cam kết từ tuần 2: tối thiểu 2 người × 0.5 ngày/tuần | Giảm benchmark còn 200 case, ưu tiên use case P0; FS xây annotation tool để tăng tốc (xem Phần III) |
| 3 | **Truy cập My Tasco staging + đặc tả OTP/step-up contract** | My Tasco Platform Team | Access trước tuần 8 | Kéo dài mock; dời cutover; OTP flow demo bằng mock có scenario switching |
| 4 | **Mốc cutover mock → real** ghi vào roadmap | Engineering Lead | Read adapters: đầu Phase 4 (tuần 13). Action adapters: đầu Phase 5 (tuần 17). OTP integration test: tuần 15 | Mỗi mốc trượt > 1 tuần → escalate stakeholder, xem xét thu hẹp M4 |

Bốn hạng mục này nằm trong exit criteria của Phase 0: **thiếu owner có tên và deadline cho bất kỳ mục nào → Phase 0 chưa đóng.**

---

# PHẦN II — MỞ RỘNG INVARIANT VÀ TEST SUITE

Không thêm invariant mới (giữ S1–S12); mở rộng enforcement point và verification:

| Invariant | Mở rộng |
|---|---|
| S2 | Enforcement point += Reranker gateway. Verification += egress spy trên endpoint reranker (A1) |
| S4 | Verification += kiểm tra evidence summary khi escalate B→C không chứa nội dung ngoài manifest (A3) |
| S6 | Verification += zero upstream mutation trước khi confirmation token tiêu thụ, kể cả bản ghi "draft" upstream (A6) |

Test suite bổ sung 5 nhóm:

1. **Reranker egress spy** — không chunk Confidential/Restricted nào rời hạ tầng nội bộ qua đường reranking.
2. **Claim-collapse** — core claim bị loại → INSUFFICIENT; tỷ lệ loại vượt ngưỡng → INSUFFICIENT; coherence check bắt tham chiếu treo.
3. **Escalation budget** — run escalated không vượt tổng budget/deadline của Route C.
4. **Streaming contract** — `run.answer` xuất hiện đúng một lần, chỉ sau VALIDATING; không token nào của answer xuất hiện trong `run.status`.
5. **Upstream-mutation-before-confirmation** — mock adapter ghi nhận mọi mutation; suite khẳng định bằng 0 trước confirm.

---

# PHẦN III — CƠ CẤU ĐỘI VÀ PHÂN CÔNG (3 AIE, 1 BE, 1 FS)

## 1. Định danh vai trò

| Mã | Vai trò | Trục sở hữu chính |
|---|---|---|
| **BE** | Backend Engineer | Enforcement backbone: identity/policy, tool & action gateway, adapters, audit, hạ tầng, CI/CD |
| **FS** | Full-stack Engineer | Toàn bộ client (web/Flutter adapter), BFF contract, contract tests, admin UI, annotation tool |
| **AIE1** | AI Engineer — Knowledge | Ingestion, chunking, versioning, classification bootstrap, embedding nội bộ, index |
| **AIE2** | AI Engineer — Retrieval & Agent | Router, planner, state machine, budgets, hybrid retrieval, evidence evaluator, capsule lifecycle |
| **AIE3** | AI Engineer — Model, Guardrails & Evaluation | Model Gateway (OpenAI), Sensitivity Gate/DLP, Egress Inspector, tiered validation, benchmark, security harness |

## 2. Nguyên tắc phân công

1. **BE sở hữu mọi điểm enforcement có side effect** (tool call, write action, policy decision) — các invariant S5, S6, S8, S9 quy về một đầu mối.
2. **Không ai tự chấm bài của mình:** AIE3 xây harness đánh giá retrieval của AIE2 và ingestion của AIE1; AIE2 review guardrail logic của AIE3; BE review mọi enforcement hook do AIE viết.
3. **FS gánh contract tests và BFF surface** để giảm bus-factor của BE — BE tập trung enforcement, không tốn thời gian cho serialization/endpoint shape.
4. **Sensitive path cần double review:** theo Definition of Done v2, mọi thay đổi trên đường Confidential/Restricted/write cần review của BE (enforcement) + AIE3 (egress).
5. **Mỗi invariant có một owner chính** chịu trách nhiệm test xanh trước release:

| Invariant | Owner chính | Reviewer |
|---|---|---|
| S1 unauthorized evidence | AIE2 | AIE3 |
| S2 restricted egress | AIE3 | BE |
| S3 secrets | AIE3 | BE |
| S4 unmanifested content | AIE3 | AIE2 |
| S5 unauthorized tool | BE | AIE2 |
| S6 write w/o confirmation | BE | FS |
| S7 citation outside manifest | AIE3 | AIE2 |
| S8 cross-tenant | BE | AIE1 |
| S9 payroll step-up | BE | AIE3 |
| S10 chain-of-thought | AIE3 | FS |
| S11 pre-gate egress | AIE3 | AIE2 |
| S12 expired evidence | AIE2 | AIE3 |

## 3. Sở hữu module (theo cấu trúc 3.3 của v2)

| Module | Owner | Hỗ trợ |
|---|---|---|
| apps/api | BE | FS (endpoint chat/SSE) |
| apps/worker | BE | AIE1 (ingestion jobs) |
| modules/identity, modules/policy | BE | — |
| modules/knowledge | AIE1 | AIE2 (interface retrieval) |
| modules/agent | AIE2 | — |
| modules/evidence | AIE2 (lifecycle) | AIE3 (egress construction) |
| modules/tools | BE | AIE2 (planner interface) |
| modules/models | AIE3 | — |
| modules/guardrails | AIE3 | BE (vị trí hook) |
| modules/governance | BE (audit) | AIE3 (evaluation) |
| Frontend web + Flutter adapter | FS | — |
| Infra, Docker, CI/CD | BE | FS (pipeline FE) |

## 4. WBS theo phase — 24 tuần

### Phase 0 — Quyết định & baseline (Tuần 1–2)
- **Cả đội:** freeze use case, ADR cho A1–A10, threat model workshop.
- **BE:** skeleton repo monolith, CI khung, môi trường dev, secret management; điều phối hạng mục A10-3/A10-4 với My Tasco Platform Team.
- **FS:** UX flow chính (chat, citation, confirmation, insufficient/denied), draft API/SSE contract theo A4; khởi công **annotation tool** cho steward (đầu tư 2–3 ngày, trả lãi suốt dự án).
- **AIE1:** khảo sát corpus demo, chốt định dạng Phase 2, taxonomy classification cùng steward.
- **AIE2:** finalize purpose taxonomy, spec state machine + budgets (gồm A3), thiết kế route classifier.
- **AIE3:** seed benchmark 200 case cùng steward (A10-2), chốt ma trận egress gồm reranker (A1), kế hoạch chọn snapshot model (A8), khung egress spy.
- **Exit:** mọi P0 có owner/test/enforcement point; 4 hạng mục A10 có owner tên thật và deadline.

### Phase 1 — Nền tảng security & platform (Tuần 3–5)
- **BE:** JWT/IAM SubjectContext, policy engine in-process + policy snapshot (A5), schema PostgreSQL/pgvector + migration, Redis, tool registry, audit metadata, feature flags, mock adapters deterministic, rate limit.
- **FS:** contract tests chạy trên mock, UI shell + auth flow, SSE plumbing theo contract A4.
- **AIE1:** ingestion skeleton, parser cho định dạng demo, layout object storage.
- **AIE2:** state machine skeleton chạy Route A end-to-end trên mock, framework budgets/deadline (A7).
- **AIE3:** Sensitivity Gate v0 (deterministic: regex + pattern PII/payroll/secret), DLP input/output v0, CI security checks, egress spy harness hoạt động.
- **Exit:** test cross-tenant, unauthorized-tool, write-without-confirmation xanh **trước khi** viết bất kỳ code agent nào.

### Phase 2 — Nền tảng tri thức bảo mật (Tuần 6–9)
- **AIE1 (critical path):** versioned ingestion, structure-aware chunking, embedding nội bộ, BM25 + pgvector, classification bootstrap + quarantine.
- **AIE2:** hybrid retrieval ACL-filtered + RRF fusion + result recheck; tuyển chọn **reranker nội bộ** theo A1 cùng AIE3.
- **AIE3:** benchmark retrieval tiếng Việt (Recall@K, NDCG, version accuracy, ACL leakage); báo cáo chọn embedding/reranker; test citation-validity.
- **BE:** enforcement chunk_acl, lưu trữ manifest, document APIs, tích hợp object storage.
- **FS:** admin UI tối thiểu cho document/version, citation viewer v0; hoàn thiện annotation tool — steward bắt đầu adjudicate song song.
- **Exit:** M1 Secure Search đạt gate retrieval/version/citation-validity/access-control.

### Phase 3 — OpenAI Simple RAG + gateways (Tuần 10–12)
- **AIE3 (critical path):** Model Gateway (Responses API, `store:false`, snapshot pinning theo A8), Evidence Capsule Builder, Egress Inspector (gồm quy tắc reranker A1), Tier 1 validation, token/cost metrics, safe failure theo A9.
- **AIE2:** Route B end-to-end, trạng thái insufficient-evidence, hook escalation B→C (flag tắt).
- **BE:** OpenAI projects dev/staging/prod (least privilege, budget, alert, kill switch), wiring cờ ZDR; theo dõi A10-1.
- **FS:** chat UI hoàn chỉnh + status streaming theo A4, các state insufficient/denied/degraded, feedback widget.
- **AIE1:** ingestion QA, mở rộng corpus phục vụ benchmark.
- **Exit:** Route B vượt fallback hiện tại trên benchmark, không vi phạm S1–S12. Nếu ZDR chưa xong: chạy fallback A10-1 (Public-only), Phase vẫn đóng được về mặt kỹ thuật.

### Phase 4 — Bounded Agentic RAG (Tuần 13–16)
- **AIE2 (critical path):** route classifier, planner schema, parallel reads có allow độc lập, evidence evaluator, 2-round retrieval, cancellation, escalation B→C với kế toán A3.
- **AIE3:** Tier 2 validation — claim extraction, deterministic checks, verifier + benchmark verifier + quy tắc claim-collapse (A2).
- **BE:** **cutover read adapters thật** (attendance, requests, staff, news, notifications — A10-4), tích hợp step-up contract, policy matrix từng tool; OTP integration test tuần 15.
- **FS:** agent timeline UI (status mức cao), citation đa nguồn, cancel/retry.
- **AIE1:** entity resolution hỗ trợ query prep, tuning index theo số đo Phase 3.
- **Exit:** case đa nguồn cải thiện đo được so với Route B; mọi loop kết thúc trong budget; adapters thật pass contract tests.

### Phase 5 — Confirmed actions & product UX (Tuần 17–19)
- **BE (critical path):** ActionDraft local theo A6, confirmation token một lần, idempotency, **cutover action adapters thật**, request submit + mark-notification-read.
- **FS:** action preview/confirm UI, OTP step-up flow, state hết hạn/replay/lỗi, accessibility + tiếng Việt UX.
- **AIE2:** Route D trong state machine, purpose-change invalidation của draft và capsule.
- **AIE3:** security test cho action (replay, concurrent confirm, action-hash mismatch, idempotency conflict), DLP trên nội dung preview.
- **AIE1:** dữ liệu eval cho action cases.
- **Exit:** mọi write pass confirmation/replay/concurrency/audit; test A6 (zero upstream mutation trước confirm) xanh.

### Phase 6 — Hardening & pilot (Tuần 20–22)
- **AIE3 (critical path):** chạy full evaluation + security harness, red-team suite, dashboard quality/security, xác nhận verifier gate A2.
- **BE:** load/cost test, failure injection theo failure matrix (đã sửa theo A5/A9), backup/restore, runbook, alert.
- **AIE2:** tuning budget/deadline theo số đo thực so với ceiling A7; đo `deadline_hit_rate`.
- **FS:** polish UX, admin trace viewer, công cụ thu feedback pilot.
- **AIE1:** đưa corpus production, bàn giao workflow steward.
- **Pilot:** shadow traffic → read-only pilot nội bộ nhóm nhỏ.

### Phase 7 — UAT & release có kiểm soát (Tuần 23–24)
- **Cả đội:** sửa lỗi UAT.
- **BE:** canary + rollback drill. **FS:** review UX tiếng Việt + accessibility. **AIE3:** gói sign-off security/privacy (báo cáo S1–S12, egress, red-team). Steward sign-off classification.
- Actions bật per-tenant flag chỉ sau khi read path ổn định qua cửa sổ pilot thỏa thuận.

## 5. Phân tích tải và rủi ro phân công

**BE là bus-factor lớn nhất.** BE sở hữu policy + tools + actions + adapters + infra. Giảm tải đã thiết kế sẵn: FS own BFF/contract tests; AIE3 own logic DLP (BE chỉ own vị trí hook); adapter sinh từ OpenAPI spec nếu My Tasco cung cấp. Nếu BE trượt ở Phase 4–5 (giai đoạn nặng nhất): cancellation chuyển sang AIE2, document APIs chuyển sang FS.

**AIE3 là critical path hai lần** (Phase 3 và Phase 6) và phụ thuộc steward từ Phase 0. Mitigation: annotation tool của FS tăng tốc adjudication; benchmark chia lô — lô 1 (100 case P0) phải xong tuần 4, không chờ đủ 200.

**AIE2 nặng nhất ở Phase 4.** Planner + evaluator + escalation trong 4 tuần là chật. Mitigation: state machine và budgets đã dựng từ Phase 1; Tier 2 hoàn toàn thuộc AIE3, AIE2 không đụng validation.

**FS có chu kỳ tải thấp ở Phase 2** — dùng chủ động cho annotation tool và admin UI, đây là đầu tư trả lãi cho A10-2.

**Quy tắc khi trượt tiến độ:** cắt theo thứ tự (1) hoãn action adapters thật → M4 thu hẹp còn mark-notification-read; (2) hoãn escalation B→C (Route C vẫn vào thẳng qua router); (3) hoãn verifier — Tier 2 chạy deterministic + ngưỡng chặt (đã có đường lùi trong A2). **Không bao giờ cắt:** test invariant, confirmation protocol, Egress Inspector.

## 6. Ánh xạ acceptance criteria (v2 mục 24) → người chứng minh

| Tiêu chí | Người chứng minh |
|---|---|
| 1. Tìm kiếm/hỏi đáp tiếng Việt có citation | AIE2 + AIE1 (benchmark AIE3) |
| 2. Agentic vượt Simple RAG đo được | AIE2 (benchmark AIE3) |
| 3. Không leakage evidence trái phép/cross-tenant | BE + AIE2 |
| 4. Restricted/payroll/OTP/secret không tới OpenAI | AIE3 |
| 5. Validation đúng tier, loại unsupported | AIE3 |
| 6. Write có preview/confirm/idempotency/audit | BE |
| 7. Loop kết thúc trong budget | AIE2 |
| 8. Policy replay deterministic, không CoT | AIE3 + BE |
| 9. Failure matrix đúng hành vi | BE |
| 10. Vận hành được bằng runbook đã test | BE + FS |

---

# PHẦN IV — TÓM TẮT THAY ĐỔI SO VỚI V2

| # | Lỗ hổng | Bản vá | Tác động scope |
|---|---|---|---|
| A1 | Reranker ngoài ma trận egress | Reranker nội bộ v1 + cột egress + egress spy | +nhỏ (model rerank nhỏ, đã trong Phase 2) |
| A2 | Claim removal không có ngưỡng sập; verifier chưa kiểm chứng | Core claim, ngưỡng 1/3, coherence check, verifier gate | +nhỏ (logic deterministic + nhánh benchmark) |
| A3 | Escalation B→C không kế toán budget | Round/capsule carry-over, deadline chung | 0 (định nghĩa, không thêm code lớn) |
| A4 | Streaming mâu thuẫn validation | Status-event streaming, answer nguyên khối | −(đơn giản hơn token streaming) |
| A5 | Signed cache chưa đặc tả | Xóa; policy in-process | −(bỏ một component) |
| A6 | Side effect của draft mơ hồ | Draft local; mọi upstream mutation = Route D | 0 |
| A7 | Không có trần latency UX | Ceiling theo route + deadline = min(...) | 0 |
| A8 | Model mới, alias, chi phí | Pin snapshot, phân tầng Terra/Sol, cấm PTC/Multi-agent mặc định | −(chi phí giảm) |
| A9 | Local LLM load-bearing nhưng unplanned | V1 không local LLM; matrix/failure cập nhật | −−(bỏ ~1 FTE workload) |
| A10 | Phụ thuộc ngoài không có owner | 4 hạng mục tuần 1, owner ngoài nhóm, fallback | 0 (quản trị) |

**Tổng tác động:** scope kỹ thuật giảm ròng (A5, A8, A9 giảm nhiều hơn A1, A2 thêm), trong khi mọi lỗ hổng invariant được đóng bằng cơ chế kiểm thử được. Kế hoạch 24 tuần cho đội 3 AIE + 1 BE + 1 FS là thực thi được với điều kiện bốn hạng mục A10 được khởi động đúng tuần 1.