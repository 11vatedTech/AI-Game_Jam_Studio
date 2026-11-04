from __future__ import annotations
import json, os, tomllib
from dataclasses import dataclass
from pathlib import Path
from .errors import ValidationError

@dataclass(frozen=True)
class StudioConfig:
    home: Path
    workspace: Path
    database: Path
    artifact_root: Path
    evidence_root: Path
    policy_file: Path
    comfyui_url: str = "http://127.0.0.1:8188"
    llm_base_url: str = "http://127.0.0.1:20128/v1"
    llm_model: str = ""
    blender_executable: str = "blender"
    godot_executable: str = "godot"

    @classmethod
    def load(cls, home: Path | None = None) -> "StudioConfig":
        chosen = Path(home or os.environ.get("STUDIO_HOME", Path.home() / ".11vated-studio")).expanduser().resolve()
        config_file = chosen / "config.toml"
        values = {}
        if config_file.exists():
            try:
                with config_file.open("rb") as stream: values = tomllib.load(stream)
            except (OSError, tomllib.TOMLDecodeError) as exc:
                raise ValidationError(f"Cannot read {config_file}: {exc}") from exc
        paths, apps, models = values.get("paths", {}), values.get("applications", {}), values.get("models", {})
        def resolve(value: str | Path, default: str) -> Path:
            p = Path(value or default).expanduser()
            return (p if p.is_absolute() else chosen / p).resolve()
        return cls(
            home=chosen, workspace=resolve(paths.get("workspace"), "workspace"),
            database=(chosen / "studio.sqlite3").resolve(),
            artifact_root=resolve(paths.get("artifacts"), "artifacts"),
            evidence_root=resolve(paths.get("evidence"), "evidence"),
            policy_file=resolve(paths.get("policy"), "policy.json"),
            comfyui_url=str(apps.get("comfyui_url", "http://127.0.0.1:8188")).rstrip("/"),
            llm_base_url=str(models.get("openai_compatible_base_url", "http://127.0.0.1:20128/v1")).rstrip("/"),
            llm_model=str(models.get("model", "")), blender_executable=str(apps.get("blender", "blender")),
            godot_executable=str(apps.get("godot", "godot")),
        )
    def ensure_directories(self) -> None:
        for p in (self.home, self.workspace, self.artifact_root, self.evidence_root): p.mkdir(parents=True, exist_ok=True)

def write_default_config(home: Path) -> Path:
    home.mkdir(parents=True, exist_ok=True)
    config_file = home / "config.toml"
    if not config_file.exists():
        config_file.write_text('''# 11vatedTech AI Game Jam Studio local configuration\n[paths]\nworkspace = "workspace"\nartifacts = "artifacts"\nevidence = "evidence"\npolicy = "policy.json"\n\n[applications]\ncomfyui_url = "http://127.0.0.1:8188"\nblender = "blender"\ngodot = "godot"\n\n[models]\nopenai_compatible_base_url = "http://127.0.0.1:20128/v1"\nmodel = ""\n''', encoding="utf-8")
    policy = home / "policy.json"
    if not policy.exists():
        policy.write_text(json.dumps({"version":1,"default_decision":"deny","auto_allow":[
            {"scope":"studio.status","side_effect":"READ"},{"scope":"capability.list","side_effect":"READ"},
            {"scope":"workspace.read","side_effect":"READ"},{"scope":"artifact.read","side_effect":"READ"},
            {"scope":"resource.inspect","side_effect":"READ"},{"scope":"comfyui.inspect","side_effect":"READ"},{"scope":"blender.inspect","side_effect":"READ"},{"scope":"godot.inspect","side_effect":"READ"},{"scope":"workspace.create","side_effect":"CREATE"}],
            "approval_required":["MODIFY","DELETE","EXECUTE","NETWORK","CREDENTIAL","PUBLISH"],
            "blocked_scopes":["secrets.export","arbitrary.shell","unrestricted.filesystem"]}, indent=2), encoding="utf-8")
    return config_file
