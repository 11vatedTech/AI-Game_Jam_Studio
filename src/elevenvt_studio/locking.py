from __future__ import annotations
import os, sys
from pathlib import Path
from .errors import Conflict

class ProcessFileLock:
    """Cross-platform advisory process lock for a single durable job ID."""
    def __init__(self,path:Path): self.path=path; self.fd=None
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.fd=os.open(self.path,os.O_CREAT|os.O_RDWR,0o600)
        if os.fstat(self.fd).st_size==0: os.write(self.fd,b"0")
        try:
            if os.name=="nt":
                import msvcrt
                os.lseek(self.fd,0,os.SEEK_SET); msvcrt.locking(self.fd,msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (OSError,BlockingIOError) as exc:
            os.close(self.fd); self.fd=None
            raise Conflict("This job is already being executed by another process",details={"lock_file":str(self.path)}) from exc
        return self
    def __exit__(self,exc_type,exc,tb):
        if self.fd is None: return
        try:
            if os.name=="nt":
                import msvcrt
                os.lseek(self.fd,0,os.SEEK_SET); msvcrt.locking(self.fd,msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.fd,fcntl.LOCK_UN)
        finally:
            os.close(self.fd); self.fd=None
