"""The perception tool surface, shared by both MCP servers.

One implementation, two transports: the legacy hand-rolled server used in
development and the official SDK server used in production. Divergence between
those two paths is exactly how a tool "works" in tests and delivers text-only
results to a real agent.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from ..errors import AdapterUnavailable, NotFound, ValidationError
from .bundle import CaptureBundle, MASK_ROLES
from .probe import Identity, ProbeStore
from .transport import DEFAULT_PROFILE, TransportLimitExceeded, TransportProfile, prepare_all

PERCEPTION_TOOL_NAMES = frozenset(
    {
        "perception_capture",
        "perception_get",
        "perception_crop",
        "perception_probe",
        "perception_probe_verify",
    }
)

ROLE_ENUM = [
    "frame",
    "mask_world_visible",
    "mask_player_visible",
    "mask_lantern_visible",
    "mask_lantern_silhouette",
    "mask_lantern_illumination",
    "diff",
]

PERCEPTION_TOOL_SPECS: list[dict] = [
    {
        "name": "perception_capture",
        "description": (
            "Capture the running application and return the images as real image content. "
            "Deterministic captures are authoritative only after repeatability qualification; "
            "live captures are always supervisory and can never satisfy a gate."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["deterministic", "live"]},
                "plan": {
                    "type": "object",
                    "description": "Capture plan: {entries: [{physics_tick, roles, camera, state, seed}]}",
                },
                "roles": {"type": "array", "items": {"type": "string", "enum": ROLE_ENUM}},
            },
            "required": ["mode"],
            "additionalProperties": False,
        },
    },
    {
        "name": "perception_get",
        "description": "Return one artifact from an existing capture as an image block, with its authoritative hash.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "capture_id": {"type": "string"},
                "role": {"type": "string", "enum": ROLE_ENUM},
            },
            "required": ["capture_id", "role"],
            "additionalProperties": False,
        },
    },
    {
        "name": "perception_crop",
        "description": (
            "Return a derivative crop for detail inspection. The authoritative original is unchanged; "
            "the crop records the source capture and hash it came from."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "capture_id": {"type": "string"},
                "role": {"type": "string", "enum": ROLE_ENUM},
                "region": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                    "minItems": 4,
                    "maxItems": 4,
                    "description": "[x, y, width, height] in authoritative pixels",
                },
                "output_size": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 1},
                    "minItems": 2,
                    "maxItems": 2,
                },
            },
            "required": ["capture_id", "role", "region"],
            "additionalProperties": False,
        },
    },
    {
        "name": "perception_probe",
        "description": (
            "Issue a vision challenge. The returned image contains a six-character code that is never "
            "included in any text block. Answer it with perception_probe_verify."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"agent_instance": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "perception_probe_verify",
        "description": "Answer a perception challenge. Single use, expires after 180 seconds.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "challenge_id": {"type": "string"},
                "answer": {"type": "string"},
            },
            "required": ["challenge_id", "answer"],
            "additionalProperties": False,
        },
    },
]


@dataclass
class ToolResponse:
    """Exactly what goes on the wire: text plus images, never structuredContent."""

    text: str
    images: list[dict] = field(default_factory=list)
    payload: dict | None = None


def content_blocks(response: ToolResponse) -> list[dict]:
    blocks: list[dict] = [{"type": "text", "text": response.text}]
    for image in response.images:
        block = {"type": "image", "data": image["data"], "mimeType": image["mimeType"]}
        # annotations are deliberately omitted: audience is an intended-audience
        # hint, and user-only is the wrong signal for a model-facing image.
        blocks.append(block)
    return blocks


class PerceptionTools:
    def __init__(self, service: Any, *, root: Path | None = None, profile: TransportProfile = DEFAULT_PROFILE):
        self.service = service
        self.root = Path(root) if root is not None else Path(service.config.evidence_root) / "captures"
        self.profile = profile
        self.probes = ProbeStore(Path(service.config.evidence_root) / "probes")

    # -- bundle lookup -----------------------------------------------------
    def _bundle_dir(self, capture_id: str) -> Path:
        if not capture_id or "/" in capture_id or "\\" in capture_id or ".." in capture_id:
            raise ValidationError(f"Invalid capture id: {capture_id!r}")
        return self.root / capture_id

    def load(self, capture_id: str) -> CaptureBundle:
        directory = self._bundle_dir(capture_id)
        bundle_path = directory / "bundle.json"
        if not bundle_path.is_file():
            raise NotFound(f"Unknown capture: {capture_id}")
        return CaptureBundle.load(bundle_path, root=directory)

    def _verification(self, bundle: CaptureBundle) -> dict:
        return bundle.verify().to_dict()

    # -- tools -------------------------------------------------------------
    def capture(self, arguments: dict) -> ToolResponse:
        mode = arguments.get("mode")
        if mode not in {"deterministic", "live"}:
            raise ValidationError("mode must be 'deterministic' or 'live'")
        adapter = getattr(self.service, "godot_capture", None)
        if adapter is None:
            raise AdapterUnavailable(
                "No capture adapter is registered for this runtime",
                details={"mode": mode, "expected": "service.godot_capture"},
            )
        bundle = adapter.capture(mode=mode, plan=arguments.get("plan"), roles=arguments.get("roles"))
        return self.describe(bundle, roles=arguments.get("roles") or bundle.roles(), out_dir=bundle.root / "transport")

    def get(self, arguments: dict) -> ToolResponse:
        bundle = self.load(arguments["capture_id"])
        role = arguments["role"]
        if not bundle.has(role):
            raise NotFound(f"Capture {bundle.capture_id} has no artifact {role}")
        return self.describe(bundle, roles=[role], out_dir=bundle.root / "transport")

    def describe(self, bundle: CaptureBundle, *, roles: Sequence[str], out_dir: Path) -> ToolResponse:
        verification = self._verification(bundle)
        if verification["status"] != "verified":
            # An image is still returned: the agent must be able to see the broken
            # frame it is being told about. What it cannot get is an authoritative
            # bundle claiming to be fine.
            failed = [check["name"] for check in verification["checks"] if not check["ok"]]
            text_prefix = "verification: FAILED -> " + ", ".join(failed) + "\n"
        else:
            text_prefix = ""
        result = prepare_all(
            bundle,
            list(roles),
            out_dir=out_dir,
            profile=self.profile,
            verification=verification,
        )
        return ToolResponse(
            text=text_prefix + result.text,
            images=result.blocks,
            payload={"capture": bundle.summary(), "verification": verification},
        )

    def crop(self, arguments: dict) -> ToolResponse:
        from PIL import Image

        bundle = self.load(arguments["capture_id"])
        role = arguments["role"]
        artifact = bundle.artifact(role)
        source = bundle.image_path(role)
        region = arguments.get("region")
        if not isinstance(region, list) or len(region) != 4:
            raise ValidationError("region must be [x, y, width, height]")

        with Image.open(source) as opened:
            opened.load()
            x, y, width, height = (int(value) for value in region)
            if width < 1 or height < 1:
                raise ValidationError("region width and height must be positive")
            if x + width > opened.width or y + height > opened.height:
                raise ValidationError(
                    f"region exceeds the {opened.width}x{opened.height} artifact",
                    details={"region": region},
                )
            crop = opened.crop((x, y, x + width, y + height))
            output_size = arguments.get("output_size")
            if output_size:
                crop = crop.resize((int(output_size[0]), int(output_size[1])), Image.LANCZOS)
            crop_path = bundle.root / "crops" / f"{role}-{uuid.uuid4().hex[:8]}.png"
            crop_path.parent.mkdir(parents=True, exist_ok=True)
            crop.save(crop_path, format="PNG", optimize=True)

        data = crop_path.read_bytes()
        text = "\n".join(
            [
                f"derivative: crop of {role} from capture {bundle.capture_id}",
                f"source_sha256: {artifact['sha256']}",
                f"source_dimensions: {artifact['width']}x{artifact['height']}",
                f"region: {list(region)}",
                f"crop_sha256: {hashlib.sha256(data).hexdigest()}",
                f"crop_dimensions: {crop.width}x{crop.height}",
                "authority: derivative only; the original artifact remains the evidence.",
            ]
        )
        return ToolResponse(
            text=text,
            images=[{"type": "image", "data": base64.b64encode(data).decode("ascii"), "mimeType": "image/png"}],
        )

    def probe(self, arguments: dict) -> ToolResponse:
        identity = Identity(studio_agent_instance=arguments.get("agent_instance"))
        challenge, image = self.probes.issue(identity)
        text = "\n".join(
            [
                f"challenge_id: {challenge.challenge_id}",
                f"expires_at: {challenge.expires_at}",
                "task: read the six characters in the attached image and submit them with perception_probe_verify.",
                "the code appears only in the image; it is not in this text.",
                "this proves delivery and readback, not comprehension.",
            ]
        )
        return ToolResponse(
            text=text,
            images=[{"type": "image", "data": base64.b64encode(image).decode("ascii"), "mimeType": "image/png"}],
        )

    def probe_verify(self, arguments: dict) -> ToolResponse:
        result = self.probes.verify(arguments["challenge_id"], arguments.get("answer", ""))
        return ToolResponse(text=json.dumps(result, indent=2, sort_keys=True), payload=result)


def to_call_tool_result(response: ToolResponse, *, request_id: Any = None):
    """Build an MCP CallToolResult with image content and no structuredContent."""
    from mcp.types import CallToolResult, ImageContent, TextContent

    content: list[Any] = [TextContent(type="text", text=response.text)]
    for image in response.images:
        content.append(ImageContent(type="image", data=image["data"], mime_type=image["mimeType"]))
    return CallToolResult(content=content)
