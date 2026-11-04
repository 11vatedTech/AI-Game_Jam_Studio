from __future__ import annotations
import json, os, platform, shutil, subprocess, threading
from datetime import datetime, timezone
from pathlib import Path


def _nvidia_smi() -> dict:
    exe=shutil.which("nvidia-smi")
    if not exe: return {"available":False,"reason":"nvidia-smi not found"}
    try:
        p=subprocess.run([exe,"--query-gpu=name,memory.total,memory.used,memory.free,driver_version","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=5,check=True)
        gpus=[]
        for line in p.stdout.strip().splitlines():
            parts=[x.strip() for x in line.split(",")]
            if len(parts)>=5: gpus.append({"name":parts[0],"vram_total_mib":int(parts[1]),"vram_used_mib":int(parts[2]),"vram_free_mib":int(parts[3]),"driver":parts[4]})
        return {"available":True,"gpus":gpus}
    except Exception as exc: return {"available":False,"reason":str(exc)}

def profile(home: Path) -> dict:
    total_ram=available_ram=None
    try:
        import psutil  # optional enhancement; core has no dependency on it
        vm=psutil.virtual_memory(); total_ram=vm.total; available_ram=vm.available
    except Exception: pass
    disk=shutil.disk_usage(home if home.exists() else Path.home())
    return {"captured_at":datetime.now(timezone.utc).isoformat(),"os":platform.platform(),"python":platform.python_version(),
            "architecture":platform.machine(),"cpu":platform.processor(),"cpu_count":os.cpu_count(),
            "ram_total_bytes":total_ram,"ram_available_bytes":available_ram,
            "disk_total_bytes":disk.total,"disk_free_bytes":disk.free,"gpu":_nvidia_smi(),
            "optional_modules":{"psutil":_module("psutil"),"torch":_module("torch"),"PIL":_module("PIL")}}

def _module(name: str) -> bool:
    try: __import__(name); return True
    except Exception: return False

class ResourceGuard:
    """Conservative admission check; it does not reserve GPU memory across processes."""
    def __init__(self, *, min_free_ram_bytes: int=2*1024**3, min_free_vram_mib: int=1536):
        self.min_free_ram_bytes=min_free_ram_bytes; self.min_free_vram_mib=min_free_vram_mib
        self._lock=threading.Lock()
    def check(self, resource: dict) -> tuple[bool,dict]:
        report=profile(Path.home()); reasons=[]
        need_ram=int(resource.get("ram_bytes",0)); need_vram=int(resource.get("vram_mib",0))
        available=report.get("ram_available_bytes")
        if available is not None and available-need_ram < self.min_free_ram_bytes: reasons.append("RAM reserve would be breached")
        gpus=report["gpu"].get("gpus",[])
        if need_vram and gpus and min(g["vram_free_mib"] for g in gpus)-need_vram < self.min_free_vram_mib: reasons.append("VRAM reserve would be breached")
        if need_vram and not gpus: reasons.append("GPU/VRAM cannot be verified")
        return (not reasons, {"reasons":reasons,"profile":report})
