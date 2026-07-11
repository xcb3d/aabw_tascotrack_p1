from dataclasses import dataclass, replace
from enum import Enum, auto


class ExecutionRoute(Enum):
    DETERMINISTIC = auto()
    SIMPLE_RAG = auto()
    AGENTIC_READ = auto()
    CONFIRMED_ACTION = auto()


class RunStatus(Enum):
    RECEIVED = auto()
    SENSITIVITY_CHECKED = auto()
    AUTHORIZED = auto()
    ROUTED = auto()
    DETERMINISTIC = auto()
    RETRIEVING = auto()
    PLANNING = auto()
    EXECUTING_READ_TOOLS = auto()
    EVALUATING_EVIDENCE = auto()
    GENERATING = auto()
    VALIDATING_OUTPUT = auto()
    WAITING_CONFIRMATION = auto()
    EXECUTING_ACTION = auto()
    COMPLETED = auto()
    INSUFFICIENT = auto()
    DENIED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass(frozen=True)
class RunBudget:
    deadline_seconds: int
    model_calls: int
    tool_calls: int
    retrieval_calls: int

    @classmethod
    def deterministic(cls):
        return cls(deadline_seconds=3, model_calls=0, tool_calls=0, retrieval_calls=0)

    @classmethod
    def simple_rag(cls):
        return cls(deadline_seconds=45, model_calls=1, tool_calls=0, retrieval_calls=1)

    @classmethod
    def agentic_read(cls):
        return cls(deadline_seconds=90, model_calls=3, tool_calls=4, retrieval_calls=2)

    @classmethod
    def confirmed_action(cls):
        return cls(deadline_seconds=90, model_calls=2, tool_calls=5, retrieval_calls=2)

    def restrict(self, **limits):
        names = ("deadline_seconds", "model_calls", "tool_calls", "retrieval_calls")
        unknown = set(limits) - set(names)
        if unknown:
            raise ValueError(f"unsupported budget restriction: {', '.join(sorted(unknown))}")

        values = {}
        for name in names:
            value = limits.get(name, getattr(self, name))
            if type(value) is not int:
                raise ValueError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
            if value > getattr(self, name):
                raise ValueError(f"{name} cannot be relaxed")
            values[name] = value
        return replace(self, **values)


@dataclass(frozen=True)
class RunState:
    status: RunStatus
    route: ExecutionRoute | None = None
    budget: RunBudget = RunBudget.deterministic()

    @classmethod
    def new(cls):
        return cls(status=RunStatus.RECEIVED)
