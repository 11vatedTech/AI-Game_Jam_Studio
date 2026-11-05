"""The live-session token must survive its own protection.

The first version restricted the token file to read-only, which is stricter than
it sounds: the next session could not replace the file, so every live capture
after the first failed before the game ever started. The restriction has to be
tight enough to exclude other local accounts and loose enough that the studio can
rewrite its own token.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from elevenvt_studio.adapters.godot_capture import GodotCaptureAdapter, _reclaim_token_file

_restrict_token_file = GodotCaptureAdapter._restrict_token_file

pytestmark = pytest.mark.skipif(os.name != "nt", reason="ACL behaviour is Windows-specific")


def _acl(path) -> str:
    return subprocess.run(
        ["icacls", str(path)], capture_output=True, text=True, timeout=30
    ).stdout


def test_a_token_can_be_replaced_after_it_has_been_restricted(tmp_path):
    token_file = tmp_path / "token.txt"

    for attempt in range(2):
        _reclaim_token_file(token_file)
        token_file.write_text(f"token-{attempt}", encoding="utf-8")
        restriction = _restrict_token_file(token_file)
        assert restriction["ok"], restriction
        assert token_file.read_text(encoding="utf-8") == f"token-{attempt}"


def test_the_restriction_excludes_other_accounts_without_locking_out_the_owner(tmp_path):
    token_file = tmp_path / "token.txt"
    token_file.write_text("secret", encoding="utf-8")
    assert _restrict_token_file(token_file)["ok"]

    listing = _acl(token_file)
    assert os.environ["USERNAME"] in listing
    for group in ("Everyone", "BUILTIN\\Users", "Authenticated Users"):
        assert group not in listing, f"{group} must not be able to read the session token"
    # Inheritance removed: nothing wider arrives from the parent directory later.
    assert "(I)" not in listing
