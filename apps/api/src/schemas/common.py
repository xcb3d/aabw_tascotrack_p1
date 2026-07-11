from enum import Enum


class StrEnum(str, Enum):
    """Python 3.10-compatible string enum base."""



class Classification(StrEnum):
    PUBLIC = "Public"
    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    RESTRICTED = "Restricted"


class PermissionDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    BLOCKED = "BLOCKED"
    NO_AUTHORIZED_SOURCE = "NO_AUTHORIZED_SOURCE"


class RunStatus(StrEnum):
    RECEIVED = "RECEIVED"
    SENSITIVITY_CHECKED = "SENSITIVITY_CHECKED"
    AUTHORIZED = "AUTHORIZED"
    ROUTED = "ROUTED"
    RETRIEVING = "RETRIEVING"
    PLANNING = "PLANNING"
    EXECUTING_READ_TOOLS = "EXECUTING_READ_TOOLS"
    EVALUATING_EVIDENCE = "EVALUATING_EVIDENCE"
    GENERATING = "GENERATING"
    VALIDATING_OUTPUT = "VALIDATING_OUTPUT"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    EXECUTING_ACTION = "EXECUTING_ACTION"
    COMPLETED = "COMPLETED"
    INSUFFICIENT = "INSUFFICIENT"
    DENIED = "DENIED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentRoute(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    SIMPLE_RAG = "SIMPLE_RAG"
    AGENTIC_READ = "AGENTIC_READ"
    CONFIRMED_ACTION = "CONFIRMED_ACTION"


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AgentMode(StrEnum):
    AUTO = "auto"
    KNOWLEDGE = "knowledge"
    ACTION_PREVIEW = "action_preview"


class ActionStatus(StrEnum):
    DRAFT = "DRAFT"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class ErrorCode(StrEnum):
    INVALID_REQUEST = "invalid_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    EXPIRED = "expired"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"
