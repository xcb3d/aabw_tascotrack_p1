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
    VALIDATING_OUTPUT = auto()
    COMPLETED = auto()
    DENIED = auto()


@dataclass(frozen=True)
class RunBudget:
    deadline_seconds: int
    model_calls: int
    tool_calls: int
    retrieval_calls: int

    @classmethod
    def deterministic(cls):
        return cls(deadline_seconds=3, model_calls=0, tool_calls=0, retrieval_calls=0)

    def restrict(self, **limits):
        values = {}
        for name in ("deadline_seconds", "model_calls", "tool_calls", "retrieval_calls"):
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
