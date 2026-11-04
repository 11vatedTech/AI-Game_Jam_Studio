from __future__ import annotations
import json, logging, re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone

_SECRET=re.compile(r"(?i)(api[_-]?key|token|password|authorization|secret)(\s*[:=]\s*)([^\s,;]+)")

def redact(value: str) -> str: return _SECRET.sub(r"\1\2[REDACTED]",value)

class JsonFormatter(logging.Formatter):
    def format(self,record):
        item={"timestamp":datetime.now(timezone.utc).isoformat(),"level":record.levelname,"logger":record.name,
              "message":redact(record.getMessage())}
        if hasattr(record,"job_id"): item["job_id"]=record.job_id
        if hasattr(record,"task_id"): item["task_id"]=record.task_id
        if record.exc_info: item["exception"]=redact(self.formatException(record.exc_info))
        return json.dumps(item,ensure_ascii=False)

def configure_logging(home:Path) -> logging.Logger:
    logger=logging.getLogger("elevenvt_studio")
    if logger.handlers: return logger
    log_dir=home/"logs"; log_dir.mkdir(parents=True,exist_ok=True)
    handler=RotatingFileHandler(log_dir/"studio.jsonl",maxBytes=10*1024*1024,backupCount=5,encoding="utf-8")
    handler.setFormatter(JsonFormatter()); logger.addHandler(handler); logger.setLevel(logging.INFO); logger.propagate=False
    return logger
