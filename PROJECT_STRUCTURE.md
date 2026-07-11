# Cấu trúc dự án

```text
.
|-- apps/
|   |-- api/                    # FastAPI endpoints, SSE, BFF
|   |-- worker/                 # Ingestion và agent jobs bất đồng bộ
|   |-- web/                    # Web client
|   `-- flutter_adapter/        # Adapter/package dùng bởi Flutter client
|-- modules/
|   |-- identity/               # JWT/IAM và SubjectContext
|   |-- policy/                 # RBAC/ABAC, purpose, step-up, egress
|   |-- knowledge/              # Ingestion, versioning, secure retrieval
|   |-- agent/                  # Router, state machine, planner, budgets
|   |-- evidence/               # Capsule, manifest, lifecycle, citation
|   |-- tools/                  # Registry, typed adapters, confirmed actions
|   |-- models/                 # OpenAI gateway và prompt/model registry
|   |-- guardrails/             # DLP, injection detection, output validation
|   `-- governance/             # Audit, trace, security event, evaluation
|-- config/                     # Cấu hình versioned, không chứa secret
|-- database/                   # Migration và seed data không nhạy cảm
|-- docs/                       # ADR, threat model, runbook, API docs
|-- evaluation/                 # Dataset/case đánh giá và artifact cục bộ
|-- infra/                      # Docker, Kubernetes, observability
|-- scripts/                    # Script phát triển và vận hành có kiểm soát
`-- tests/                      # Các tầng kiểm thử và invariant S1-S12
```

## Nguyên tắc phụ thuộc

- `apps/*` là composition root; nghiệp vụ nằm trong `modules/*`.
- Module chỉ giao tiếp qua contract công khai, không truy cập trực tiếp phần
  triển khai nội bộ của module khác.
- `identity`, `policy`, `guardrails` và các gateway luôn chạy trước điểm egress
  hoặc mutation tương ứng.
- OpenAI chỉ được gọi qua `modules/models`; adapter My Tasco chỉ nằm trong
  `modules/tools`.
- Test bảo mật S1-S12 nằm trong `tests/security/invariants` và là release gate.
- Prompt, model, policy, schema và dataset là artifact có phiên bản; secret phải
  đến từ secret manager hoặc biến môi trường, không commit vào repository.

## Ánh xạ API

Các router được chia theo tag trong `openapi.yaml`: `system`, `legacy`, `chat`,
`actions`, `documents`, `governance`, và `evaluation`. Contract OpenAPI gốc vẫn
ở thư mục gốc cho đến khi pipeline sinh tài liệu/code được thiết lập.
