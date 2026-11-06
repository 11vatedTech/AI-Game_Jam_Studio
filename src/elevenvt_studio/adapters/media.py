"""Safe local media operations through ffmpeg / ffprobe.

Only argv arrays are ever executed (never a shell), inputs must resolve inside
the managed workspace, outputs are created with no-overwrite semantics, and
every invocation is bounded by an explicit timeout. Transcoding never
overwrites: the destination must not exist.
"""
from __future__ import annotations
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from ..errors import AdapterUnavailable, ValidationError

#: Conservative allowlist of container/codec tokens accepted for transcode targets.
AUDIO_CODECS = {"aac", "mp3", "libopus", "vorbis", "flac", "pcm_s16le", "wav"}
VIDEO_CODECS = {"libx264", "libx265", "libvpx-vp9", "libaom-av1", "mpeg4"}
CONTAINERS = {"mp3", "ogg", "oga", "wav", "flac", "m4a", "mp4", "webm", "mkv"}


class MediaAdapter:
    def __init__(self, workspace: Path, *, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe"):
        self.workspace = workspace.resolve()
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe

    def _executable(self, name: str) -> str:
        found = shutil.which(name) or (str(Path(name).resolve()) if Path(name).is_file() else None)
        if not found:
            raise AdapterUnavailable(f"Media executable not found: {name}")
        return found

    def _inside(self, path: Path) -> Path:
        candidate = path.resolve()
        if candidate != self.workspace and self.workspace not in candidate.parents:
            raise ValidationError("Media path must remain inside the managed workspace")
        return candidate

    @staticmethod
    def _run(exe: str, args: list[str], timeout: int) -> dict:
        if timeout < 1 or timeout > 3600:
            raise ValidationError("Media timeout must be between 1 and 3600 seconds")
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                proc = subprocess.run([exe, *args], stdin=subprocess.DEVNULL,
                                      stdout=out, stderr=err, timeout=timeout,
                                      shell=False, check=False)
            except subprocess.TimeoutExpired as exc:
                raise AdapterUnavailable(f"Media process exceeded timeout of {timeout}s") from exc
            except OSError as exc:
                raise AdapterUnavailable(f"Could not launch media process: {exc}") from exc
            out.seek(0)
            err.seek(0)
            return {"returncode": proc.returncode,
                    "stdout": out.read().decode("utf-8", errors="replace")[-20000:],
                    "stderr": err.read().decode("utf-8", errors="replace")[-20000:]}

    def version(self) -> dict:
        exe = self._executable(self.ffmpeg)
        result = self._run(exe, ["-hide_banner", "-version"], 30)
        first = (result["stdout"] or result["stderr"]).splitlines()
        return {"executable": exe, "version_line": first[0] if first else "", "success": result["returncode"] == 0}

    def probe(self, relative_path: str) -> dict:
        exe = self._executable(self.ffprobe)
        target = self._inside(self.workspace / relative_path)
        if not target.is_file():
            raise ValidationError(f"Media file does not exist: {relative_path}")
        result = self._run(exe, ["-hide_banner", "-v", "error", "-print_format", "json",
                                 "-show_format", "-show_streams", str(target)], 60)
        if result["returncode"] != 0:
            raise AdapterUnavailable("ffprobe could not parse the media file",
                                     details={"stderr": result["stderr"]})
        try:
            report = json.loads(result["stdout"])
        except json.JSONDecodeError as exc:
            raise AdapterUnavailable("ffprobe returned invalid JSON", details={}) from exc
        streams = report.get("streams", [])
        return {"path": relative_path, "format": report.get("format", {}).get("format_name"),
                "duration_seconds": report.get("format", {}).get("duration"),
                "size_bytes": target.stat().st_size,
                "stream_count": len(streams),
                "streams": [{"index": s.get("index"), "codec_type": s.get("codec_type"),
                             "codec_name": s.get("codec_name"),
                             "width": s.get("width"), "height": s.get("height"),
                             "sample_rate": s.get("sample_rate"),
                             "channels": s.get("channels")} for s in streams]}

    def transcode(self, relative_src: str, relative_dst: str, *, audio_codec: str | None = None,
                  video_codec: str | None = None, container: str | None = None,
                  extra_args: list[str] | None = None, timeout: int = 600) -> dict:
        src = self._inside(self.workspace / relative_src)
        dst = self._inside(self.workspace / relative_dst)
        if not src.is_file():
            raise ValidationError(f"Media file does not exist: {relative_src}")
        if dst.exists():
            raise ValidationError("Refusing to overwrite existing media output")
        # No -y: stdin is DEVNULL, so ffmpeg aborts rather than overwriting if the
        # destination appeared after the existence check above.
        args = ["-hide_banner", "-v", "error", "-nostdin", "-i", str(src)]
        if audio_codec:
            if audio_codec not in AUDIO_CODECS:
                raise ValidationError(f"Unsupported audio codec: {audio_codec}")
            args += ["-c:a", audio_codec]
        if video_codec:
            if video_codec not in VIDEO_CODECS:
                raise ValidationError(f"Unsupported video codec: {video_codec}")
            args += ["-c:v", video_codec]
        if container:
            if container not in CONTAINERS:
                raise ValidationError(f"Unsupported container: {container}")
            args += ["-f", container]
        if extra_args:
            if (not isinstance(extra_args, list) or not extra_args
                    or any(not isinstance(x, str) for x in extra_args)):
                raise ValidationError("extra_args must be a non-empty array of strings")
            if len(extra_args) > 24:
                raise ValidationError("extra_args is limited to 24 tokens")
            args += extra_args
        args.append(str(dst))
        exe = self._executable(self.ffmpeg)
        result = self._run(exe, args, timeout)
        if result["returncode"] != 0 or not dst.is_file():
            try:
                dst.unlink(missing_ok=True)
            finally:
                raise AdapterUnavailable("ffmpeg transcode failed", details={"stderr": result["stderr"]})
        return {"src": relative_src, "dst": relative_dst, "size_bytes": dst.stat().st_size,
                "audio_codec": audio_codec, "video_codec": video_codec, "container": container}
