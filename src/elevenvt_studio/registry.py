from __future__ import annotations
import json
from pathlib import Path
from .errors import ValidationError

class CapabilityRegistry:
    def __init__(self, catalog_dir: Path): self.catalog_dir=catalog_dir; self._items={}; self.load()
    def load(self) -> None:
        self._items={}
        if not self.catalog_dir.exists(): return
        for file in sorted(self.catalog_dir.glob("*.json")):
            raw=json.loads(file.read_text(encoding="utf-8"))
            entries=raw if isinstance(raw,list) else raw.get("capabilities",[])
            for item in entries:
                self.register(item)
    def register(self, item: dict) -> None:
        required=("id","domain","description","side_effect","scope","status")
        missing=[k for k in required if k not in item]
        if missing: raise ValidationError(f"Capability missing fields {missing}: {item.get('id','<unknown>')}")
        if item["id"] in self._items: raise ValidationError(f"Duplicate capability ID: {item['id']}")
        self._items[item["id"]]=item
    def get(self, capability_id: str) -> dict:
        if capability_id not in self._items: raise ValidationError(f"Unknown capability: {capability_id}")
        return self._items[capability_id]
    def list(self, domain: str | None=None) -> list[dict]:
        values=list(self._items.values())
        if domain: values=[v for v in values if v["domain"]==domain]
        return sorted(values,key=lambda x:x["id"])
