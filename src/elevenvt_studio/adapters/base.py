from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AdapterHealth:
    adapter_id: str
    status: str
    version: str | None = None
    details: dict[str,Any] = field(default_factory=dict)
