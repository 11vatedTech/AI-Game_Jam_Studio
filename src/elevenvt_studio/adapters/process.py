from __future__ import annotations
import shutil, subprocess, tempfile
from pathlib import Path
from ..errors import AdapterUnavailable, ValidationError

class ProcessAdapter:
    """Safe argv-only process launcher; never invokes a shell or accepts arbitrary executables."""
    def __init__(self, workspace: Path): self.workspace=workspace.resolve()
    def executable(self, configured: str) -> str:
        found=shutil.which(configured)
        if not found and Path(configured).is_file(): found=str(Path(configured).resolve())
        if not found: raise AdapterUnavailable(f"Executable not found: {configured}")
        return found
    @staticmethod
    def _tail(stream, limit=50000):
        stream.flush(); stream.seek(0,2); size=stream.tell(); stream.seek(max(0,size-limit))
        return stream.read().decode("utf-8",errors="replace")
    def run(self, configured: str, args: list[str], *, cwd: Path, timeout: int=900) -> dict:
        if not isinstance(args,list) or any(not isinstance(x,str) for x in args): raise ValidationError("Process arguments must be an array of strings")
        cwd=cwd.resolve()
        if cwd != self.workspace and self.workspace not in cwd.parents: raise ValidationError("Process working directory must remain inside the managed workspace")
        exe=self.executable(configured)
        if timeout < 1 or timeout > 7200: raise ValidationError("Process timeout must be between 1 and 7200 seconds")
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                p=subprocess.run([exe,*args],cwd=cwd,stdin=subprocess.DEVNULL,stdout=stdout_file,stderr=stderr_file,
                                 timeout=timeout,shell=False,check=False)
                stdout=self._tail(stdout_file); stderr=self._tail(stderr_file)
                return {"executable":exe,"argv":[exe,*args],"cwd":str(cwd),"returncode":p.returncode,
                        "stdout":stdout,"stderr":stderr,"success":p.returncode==0}
            except subprocess.TimeoutExpired as exc:
                stdout=self._tail(stdout_file); stderr=self._tail(stderr_file)
                raise AdapterUnavailable(f"Process exceeded timeout of {timeout}s",details={"stdout":stdout,"stderr":stderr,"timeout_seconds":timeout}) from exc
            except OSError as exc: raise AdapterUnavailable(f"Could not launch process: {exc}") from exc
