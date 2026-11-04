from pathlib import Path
import pytest
from elevenvt_studio.errors import ValidationError
from elevenvt_studio.paths import safe_workspace_path

def test_accepts_relative_path(tmp_path):
    assert safe_workspace_path(tmp_path,"art/hero/texture.png")==tmp_path/"art/hero/texture.png"

def test_rejects_parent_traversal(tmp_path):
    with pytest.raises(ValidationError): safe_workspace_path(tmp_path,"../outside.txt")

def test_rejects_absolute_path(tmp_path):
    with pytest.raises(ValidationError): safe_workspace_path(tmp_path,str((tmp_path/"x").resolve()))

def test_rejects_symlink_escape(tmp_path):
    outside=tmp_path.parent/"outside-studio-test"; outside.mkdir(exist_ok=True)
    link=tmp_path/"link"
    try: link.symlink_to(outside,target_is_directory=True)
    except OSError: pytest.skip("Symlink creation unavailable")
    with pytest.raises(ValidationError): safe_workspace_path(tmp_path,"link/escape.txt")
