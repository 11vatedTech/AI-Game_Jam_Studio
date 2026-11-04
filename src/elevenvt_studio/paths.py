from __future__ import annotations
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from .errors import ValidationError

def canonical_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))

def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False

def safe_workspace_path(workspace: Path, relative: str, *, allow_root: bool = False) -> Path:
    """Resolve an untrusted path and reject traversal and symlink escapes."""
    if not isinstance(relative, str) or not relative.strip():
        raise ValidationError("A non-empty workspace-relative path is required")
    # Validate both path dialects even when tests run on a different OS than the target.
    windows_item = PureWindowsPath(relative)
    posix_item = PurePosixPath(relative.replace("\\", "/"))
    item = Path(relative)
    if "\x00" in relative or item.is_absolute() or item.drive or windows_item.is_absolute() or windows_item.drive:
        raise ValidationError("Absolute paths are not accepted; use a workspace-relative path")
    if ".." in windows_item.parts or ".." in posix_item.parts:
        raise ValidationError("Parent traversal is not accepted in workspace paths")
    root = canonical_path(workspace)
    candidate = canonical_path(root / item)
    if not is_relative_to(candidate, root):
        raise ValidationError("Path escapes the managed workspace", details={"path": relative})
    probe = candidate
    while not probe.exists() and probe != root:
        probe = probe.parent
    if not is_relative_to(probe.resolve(), root.resolve()):
        raise ValidationError("Path resolves through a symlink outside the managed workspace")
    if candidate == root and not allow_root:
        raise ValidationError("The workspace root itself is not a file target")
    return candidate
