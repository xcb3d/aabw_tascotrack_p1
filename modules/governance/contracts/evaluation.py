from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    title: str
    department: str
    classification: str
    allowed_access: str


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    role: str
    department: str
    status: str


@dataclass(frozen=True)
class PublicEvaluationScenario:
    question_id: str
    user_id: str
    role: str
    department: str
    expected_permission: str
    expected_document_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationResult:
    question_id: str
    expected_permission: str
    actual_permission: str
    expected_document_ids: tuple[str, ...]
    allowed_document_ids: tuple[str, ...]
