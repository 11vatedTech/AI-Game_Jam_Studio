"""End-to-end critic benchmark.

The 3.0 s budget covers decoding, every metric and report serialization — the
work an operator actually waits for — not just the arithmetic. Cold start is a
separate process because imports and first-touch costs are real and are paid by
the first frame of every production run.

p95 is the gate. A fast median with a 9 s tail is a bad critic.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

DEFAULT_CONTRACT = REPO / "Games" / "emberkeep" / "art_direction.json"
DEFAULT_OUTPUT = REPO / "reports" / "evidence" / "productions" / "emberkeep" / "02-manufacture" / "critic_bench.json"


def _one_pass(frames, direction) -> float:
    """Time one full evaluation including report serialization, in milliseconds."""
    from elevenvt_studio.quality import critic

    started = time.perf_counter()
    report = critic.evaluate(frames, direction, job_id="bench")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle)
        path = Path(handle.name)
    elapsed = time.perf_counter() - started
    path.unlink(missing_ok=True)
    return elapsed * 1000.0


def _profile_metrics(frame, direction, repeats: int = 3) -> dict:
    """Per-metric cost. Escalating the implementation without this is guesswork."""
    from elevenvt_studio.quality import metrics

    rgb = metrics.load_rgb(frame.path)
    world = None
    if frame.mask_path is not None:
        import numpy as np
        from PIL import Image

        with Image.open(frame.mask_path) as mask_image:
            world = np.asarray(mask_image.convert("L")) > 127
    calls = {
        "decode": lambda: metrics.load_rgb(frame.path),
        "luminance_floor": lambda: metrics.luminance_percentiles(rgb),
        "warm_share": lambda: metrics.warm_share(rgb, world, direction.threshold("warm_share")),
        "delta_e_max": lambda: metrics.palette_drift(rgb, direction.palette),
        "clutter": lambda: metrics.clutter(rgb, None),
        "lantern_dominance": lambda: metrics.lantern_dominance(rgb, None),
    }
    timings = {}
    for name, call in calls.items():
        try:
            samples = []
            for _ in range(repeats):
                started = time.perf_counter()
                call()
                samples.append((time.perf_counter() - started) * 1000.0)
            timings[name] = round(min(samples), 2)
        except Exception as exc:  # pragma: no cover - diagnostics only
            timings[name] = f"error: {exc}"
    return timings


def _machine() -> dict:
    info = {
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpu_count": __import__("os").cpu_count(),
        "python": platform.python_version(),
    }
    try:
        import psutil

        info["ram_gb"] = round(psutil.virtual_memory().total / 1024**3, 1)
    except ModuleNotFoundError:
        info["ram_gb"] = None
    for module in ("numpy", "skimage", "PIL"):
        try:
            info[module] = __import__(module).__version__
        except Exception:  # pragma: no cover
            info[module] = None
    return info


def _percentiles(samples: list[float]) -> dict:
    ordered = sorted(samples)
    def pick(q: float) -> float:
        if not ordered:
            return 0.0
        index = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
        return round(ordered[index], 2)
    return {
        "median_ms": round(statistics.median(ordered), 2) if ordered else 0.0,
        "p95_ms": pick(0.95),
        "p99_ms": pick(0.99),
        "max_ms": round(max(ordered), 2) if ordered else 0.0,
        "min_ms": round(min(ordered), 2) if ordered else 0.0,
        "samples": len(ordered),
    }


def _single(args) -> int:
    from elevenvt_studio.quality import art_direction, critic

    direction = art_direction.load(Path(args.contract), verify_references=False)
    frames = critic.frames_from_directory(Path(args.frames))
    if not frames:
        print(json.dumps({"error": "no frames found", "frames_dir": args.frames}))
        return 2
    elapsed = _one_pass(frames, direction)
    print(json.dumps({"cold_ms": round(elapsed, 2), "frame_count": len(frames)}))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", default=str(REPO / "reports" / "evidence" / "runs" / "emberkeep-smoke"))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--warm", type=int, default=20)
    parser.add_argument("--budget-ms", type=float, default=3000.0)
    parser.add_argument("--single", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.single:
        return _single(args)

    from elevenvt_studio.quality import art_direction, critic

    direction = art_direction.load(Path(args.contract), verify_references=False)
    frames = critic.frames_from_directory(Path(args.frames))
    if not frames:
        print(f"error: no frames in {args.frames}", file=sys.stderr)
        return 2

    resolution = None
    try:
        from PIL import Image

        with Image.open(frames[0].path) as image:
            resolution = list(image.size)
    except Exception:  # pragma: no cover
        pass

    cold = subprocess.run(
        [sys.executable, __file__, "--single", "--frames", args.frames, "--contract", args.contract],
        capture_output=True,
        text=True,
        check=False,
    )
    cold_payload = json.loads(cold.stdout) if cold.returncode == 0 and cold.stdout.strip() else {}
    cold_ms = cold_payload.get("cold_ms")

    # The budget is per frame, so each frame is timed as its own end-to-end evaluation.
    per_frame_samples: list[float] = []
    for frame in frames:
        for _ in range(max(1, args.warm)):
            per_frame_samples.append(_one_pass([frame], direction))
    stats = _percentiles(per_frame_samples)

    set_totals = [_one_pass(frames, direction) for _ in range(3)]
    set_stats = _percentiles(set_totals)

    meets_budget = cold_ms is not None and stats["p95_ms"] <= args.budget_ms
    profile = _profile_metrics(frames[0], direction) if frames else {}

    result = {
        "budget_ms": args.budget_ms,
        "metric": "end-to-end: file read + decode + all metrics + report JSON write",
        "gate": "p95 <= budget",
        "status": "PASS" if meets_budget else "FAIL",
        "cold_ms": cold_ms,
        "per_frame": stats,
        "whole_frame_set": set_stats,
        "metric_profile_ms": profile,
        "frame_count": len(frames),
        "resolution": resolution,
        "declared_resolution": direction.capture.get("resolution"),
        "frame_set_meets_declared_resolution": resolution == direction.capture.get("resolution"),
        "frames_directory": str(Path(args.frames).resolve()),
        "contract_sha256": direction.sha256,
        "machine": _machine(),
        "limitations": [
            *(
                ["Frame count below the planned 24-frame set weakens the p99 estimate."]
                if len(frames) < 24
                else []
            ),
            *(
                [f"Frames are {resolution}, not the declared {direction.capture.get('resolution')}; "
                 "the budget is stated for 1080p, so this run does not prove the declared case."]
                if resolution != direction.capture.get("resolution")
                else []
            ),
            "Timings are from a shared desktop; background load is not controlled beyond being noted.",
        ],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if meets_budget else 1


if __name__ == "__main__":
    raise SystemExit(main())
