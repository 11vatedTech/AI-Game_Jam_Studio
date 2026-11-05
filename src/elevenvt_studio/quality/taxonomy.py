"""Failure taxonomy for the trace ledger.

A ledger that records "it failed" teaches nothing. These ten classes are the
smallest set that changes what an operator does next: fix the machine, fix the
dependency, fix the input, get approval, fix the protocol, fix the model, fix
the parameters, wait, free resources — or admit we do not know.

`UNKNOWN` is a real answer. Guessing a category would corrupt the aggregate
statistics the ACES gap analysis is supposed to read.
"""

from __future__ import annotations

import json
import socket
from enum import Enum

from ..errors import (
    AdapterUnavailable,
    ApprovalRequired,
    Conflict,
    NotFound,
    PermissionDenied,
    PostconditionFailed,
    ResourceUnavailable,
    UncertainSideEffect,
    ValidationError,
)


class FailureClass(str, Enum):
    ENVIRONMENT = "ENVIRONMENT"
    DEPENDENCY = "DEPENDENCY"
    INPUT_INVALID = "INPUT_INVALID"
    POLICY_DENIED = "POLICY_DENIED"
    TOOL_PROTOCOL = "TOOL_PROTOCOL"
    MODEL_QUALITY = "MODEL_QUALITY"
    PARAMETER = "PARAMETER"
    TIMEOUT = "TIMEOUT"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    UNKNOWN = "UNKNOWN"


DETECTION_RULES: dict[FailureClass, str] = {
    FailureClass.ENVIRONMENT: "the host or toolchain was missing, wrong-versioned or unreachable",
    FailureClass.DEPENDENCY: "a required service, model or application was absent or errored",
    FailureClass.INPUT_INVALID: "the supplied input violated a declared constraint",
    FailureClass.POLICY_DENIED: "permission policy or a missing approval blocked the call",
    FailureClass.TOOL_PROTOCOL: "the call itself was malformed or the tool answered out of contract",
    FailureClass.MODEL_QUALITY: "the tool ran as specified and produced work that failed review",
    FailureClass.PARAMETER: "a tuning value was wrong while the pipeline was correct",
    FailureClass.TIMEOUT: "the work did not complete within its declared budget",
    FailureClass.RESOURCE_EXHAUSTED: "VRAM, RAM, disk or process slots ran out",
    FailureClass.UNKNOWN: "insufficient evidence to classify — never guessed",
}

_TYPE_MAP: tuple[tuple[type[BaseException], FailureClass], ...] = (
    (PermissionDenied, FailureClass.POLICY_DENIED),
    (ApprovalRequired, FailureClass.POLICY_DENIED),
    (ValidationError, FailureClass.INPUT_INVALID),
    (NotFound, FailureClass.DEPENDENCY),
    (AdapterUnavailable, FailureClass.DEPENDENCY),
    (ConnectionError, FailureClass.DEPENDENCY),
    (socket.timeout, FailureClass.TIMEOUT),
    (TimeoutError, FailureClass.TIMEOUT),
    (MemoryError, FailureClass.RESOURCE_EXHAUSTED),
    (UncertainSideEffect, FailureClass.UNKNOWN),
    (PostconditionFailed, FailureClass.MODEL_QUALITY),
    (Conflict, FailureClass.ENVIRONMENT),
    (json.JSONDecodeError, FailureClass.TOOL_PROTOCOL),
)


def classify(exc: BaseException, context: dict | None = None) -> tuple[FailureClass, str]:
    """Return the class and the evidence that produced it."""
    for exc_type, failure_class in _TYPE_MAP:
        if isinstance(exc, exc_type):
            return failure_class, f"matched {exc_type.__name__}"

    if isinstance(exc, OSError):
        # ENOSPC / EMFILE / ENOMEM are resource problems, not environment problems.
        if exc.errno in (28, 24, 12):
            return FailureClass.RESOURCE_EXHAUSTED, f"OSError errno={exc.errno}"
        return FailureClass.ENVIRONMENT, f"OSError errno={exc.errno}"

    for key, value in (context or {}).items():
        if key == "failure_class" and value in FailureClass._value2member_map_:
            return FailureClass(value), f"declared by caller via {key}"
    return FailureClass.UNKNOWN, f"no rule matched {type(exc).__name__}"


def outcome_for(exc: BaseException) -> str:
    """Policy denials are a different outcome from a failure; the ledger keeps them apart."""
    failure_class, _ = classify(exc)
    if failure_class is FailureClass.POLICY_DENIED:
        return "denied"
    return "failed"
