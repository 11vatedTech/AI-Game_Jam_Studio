"""Frame metrics for the critic.

Every metric reports its algorithm version, a confidence value and its known
limitations. That is not decoration: a metric that cannot state where it is
blind will be trusted where it is blind.

Nothing here decides what is good. Thresholds arrive from the art-direction
contract, and a missing threshold means "not gated", never "passed".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
from PIL import Image

RGB_TO_LINEAR = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)


@dataclass(frozen=True)
class MetricOutput:
    value: float | None
    algorithm_version: str
    confidence: float
    limitations: tuple[str, ...]
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def evaluated(self) -> bool:
        return self.value is not None


def load_rgb(path) -> np.ndarray:
    """Decode to float RGB in [0, 1]. This decode is inside the measured budget."""
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def to_float(rgb: np.ndarray) -> np.ndarray:
    return rgb.astype(np.float64) / 255.0


def srgb_to_linear(rgb01: np.ndarray) -> np.ndarray:
    return np.where(rgb01 <= 0.04045, rgb01 / 12.92, ((rgb01 + 0.055) / 1.055) ** 2.4)


def luminance(rgb: np.ndarray) -> np.ndarray:
    """Linear relative luminance — percentiles computed on this are physically meaningful."""
    return srgb_to_linear(to_float(rgb)) @ RGB_TO_LINEAR


# --- individual metrics -----------------------------------------------------


def luminance_percentiles(rgb: np.ndarray) -> MetricOutput:
    y = luminance(rgb).ravel()
    p1, p5, p50, p95, p99 = np.percentile(y, [1, 5, 50, 95, 99])
    return MetricOutput(
        value=float(p5),
        algorithm_version="lum-pct-1",
        confidence=0.95,
        limitations=(
            "Linearisation assumes sRGB primaries; a display with a different transfer curve shifts the floor.",
            "Reports the whole frame; a dark region covering less than 5% of the image will not be seen.",
        ),
        detail={"p1": float(p1), "p5": float(p5), "p50": float(p50), "p95": float(p95), "p99": float(p99)},
    )


def luminance_cause(
    rgb: np.ndarray,
    occupancy: np.ndarray | None,
    floor: float,
    *,
    band_count: int = 8,
    tile: int = 32,
    flat_std: float = 0.002,
) -> MetricOutput:
    """Explain where a frame is dark, and what kind of darkness it is.

    A global percentile says a frame is dark; it cannot say whether the camera is
    looking at unlit stone, at a surface with no detail, or at nothing at all. This
    metric attributes every pixel below the floor to one of three situations, using
    the engine's coverage mask (surfaces present, independent of their lighting) and
    local image detail:

      below rendered geometry   dark where nothing was drawn (a coverage defect)
      on flat geometry          geometry present, no detail readable (material/light)
      on structured geometry    shadow with shape in it (may be intentional)

    It reports a diagnosis with its evidence, and `undetermined` when the inputs
    cannot separate those cases. Its value is never used as a threshold.
    """
    y = luminance(rgb)
    height, width = y.shape
    dark = y < floor
    dark_total = int(dark.sum())
    flat = _detail_free(y, tile, flat_std)

    geometry = None if occupancy is None else _match_mask(occupancy, width, height)

    bands: list[dict[str, Any]] = []
    for index in range(band_count):
        y0 = height * index // band_count
        y1 = height * (index + 1) // band_count
        slab = slice(y0, y1)
        band_dark = dark[slab]
        bands.append(
            {
                "index": index,
                "rows": [y0, y1],
                "p5": float(np.percentile(y[slab], 5)),
                "dark_pixels": int(band_dark.sum()),
                "dark_share": float(band_dark.mean()),
                "geometry_share": None if geometry is None else float(geometry[slab].mean()),
                "flat_share": float(flat[slab].mean()),
            }
        )

    limitations = [
        "Band position is the only separator between sky and unrendered void; a camera pitched far enough to put sky low in frame would swap them.",
        "There is no depth buffer here: occlusion and absence are distinguished only by the engine's coverage mask.",
        "Detail-free regions are found by local standard deviation, so a deliberately smooth gradient is counted as flat.",
    ]

    if geometry is None:
        return MetricOutput(
            None,
            "lum-cause-1",
            0.0,
            tuple(limitations)
            + ("No coverage mask: dark pixels cannot be attributed to surface or background, so no cause is claimed.",),
            detail={
                "floor": floor,
                "dark_share": dark_total / float(y.size),
                "bands": bands,
                "diagnosis": {
                    "kind": "undetermined",
                    "confidence": 0.0,
                    "cannot_distinguish": ["background or geometry", "unlit surface or absent surface"],
                },
            },
        )

    first_geometry = next((b["index"] for b in bands if (b["geometry_share"] or 0.0) >= 0.02), None)
    empty = [b["index"] for b in bands if (b["geometry_share"] or 0.0) < 0.02]
    sky_bands = [i for i in empty if first_geometry is None or i < first_geometry]
    gap_bands = [i for i in empty if first_geometry is not None and i > first_geometry]

    def dark_in(indices: Sequence[int]) -> int:
        return sum(b["dark_pixels"] for b in bands if b["index"] in indices)

    if dark_total:
        gap_share = dark_in(gap_bands) / dark_total
        sky_share = dark_in(sky_bands) / dark_total
        geometry_share = float((dark & geometry).sum()) / dark_total
        flat_share = float((dark & flat).sum()) / dark_total
    else:
        gap_share = sky_share = geometry_share = flat_share = 0.0

    candidates = [
        ("missing_coverage", gap_share),
        ("unlit_flat_surface" if flat_share >= 0.5 else "shadowed_geometry", geometry_share),
        ("dark_sky", sky_share),
    ]
    ranked = sorted(candidates, key=lambda item: item[1], reverse=True)
    kind, dominant = ranked[0]
    runner_up = ranked[1][1]

    if dark_total == 0:
        kind, confidence, dominant = "no_darkness", 0.9, 0.0
    else:
        confidence = min(0.9, 0.55 + 0.35 * dominant)
        if dominant - runner_up < 0.15:
            confidence = min(confidence, 0.5)

    cannot_distinguish: list[str] = []
    if dark_total and dominant - runner_up < 0.15:
        cannot_distinguish.append(f"{ranked[0][0]} and {ranked[1][0]} fit the pixels about equally well")
    if dark_total and gap_share >= 0.1 and sky_share >= 0.1:
        cannot_distinguish.append("sky from unrendered void where both are unsegmented")

    if kind == "missing_coverage":
        basis = [
            f"{gap_share:.2f} of pixels below the floor sit in {len(gap_bands)} band(s) with no rendered geometry: {gap_bands}",
            f"rendered geometry first appears in band {first_geometry}",
        ]
    elif kind == "unlit_flat_surface":
        basis = [
            f"{geometry_share:.2f} of dark pixels lie on rendered geometry",
            f"{flat_share:.2f} of them are in detail-free tiles",
        ]
    elif kind == "shadowed_geometry":
        basis = [
            f"{geometry_share:.2f} of dark pixels lie on rendered geometry",
            f"only {flat_share:.2f} of them are detail-free, so the shadow has structure",
        ]
    elif kind == "dark_sky":
        basis = [f"{sky_share:.2f} of dark pixels sit above all rendered geometry"]
    else:
        basis = ["no pixels below the floor"]

    return MetricOutput(
        value=float(gap_share),
        algorithm_version="lum-cause-1",
        confidence=float(confidence),
        limitations=tuple(limitations) + tuple(cannot_distinguish),
        detail={
            "floor": floor,
            "dark_share": dark_total / float(y.size),
            "dark_over_geometry_share": geometry_share,
            "detail_free_dark_share": flat_share,
            "sky_bands": sky_bands,
            "gap_bands": gap_bands,
            "bands": bands,
            "diagnosis": {
                "kind": kind,
                "confidence": float(confidence),
                "basis": basis,
                "cannot_distinguish": cannot_distinguish,
            },
        },
    )


def warm_share(rgb: np.ndarray, world_mask: np.ndarray | None, band: dict) -> MetricOutput:
    """Fraction of world pixels inside the warm HSV band.

    Numerator: pixels passing classification. Denominator: every world pixel after
    sky/UI exclusion. Using the classified set as the denominator would force the
    ratio to 1.0 and make the metric meaningless.
    """
    if world_mask is None:
        return MetricOutput(None, "warm-share-1", 0.0, ("No world mask supplied; sky and UI cannot be excluded.",))

    hsv = _rgb_to_hsv(to_float(rgb))
    hue, sat, val = hsv[..., 0] * 360.0, hsv[..., 1], hsv[..., 2]
    low, high = band["hue_deg"]
    warm = (hue >= low) & (hue <= high) & (sat >= band["sat_min"]) & (val >= band["val_min"])

    world = world_mask.astype(bool)
    total = int(world.sum())
    if total == 0:
        return MetricOutput(None, "warm-share-1", 0.0, ("World mask selects no pixels.",))

    share = float((warm & world).sum() / total)
    return MetricOutput(
        value=share,
        algorithm_version="warm-share-1",
        confidence=0.85 if band["sat_min"] > 0 else 0.6,
        limitations=(
            "HSV classification is hue-band based; a warm object under strong blue light is undercounted.",
            "Depends entirely on the engine-supplied world mask being correct.",
        ),
        detail={"world_pixels": total, "warm_pixels": int((warm & world).sum())},
    )


def silhouette(with_rgb: np.ndarray, without_rgb: np.ndarray, region: np.ndarray | None) -> MetricOutput:
    """Does the player read against the background they actually stand in?"""
    a, b = to_float(with_rgb), to_float(without_rgb)
    if a.shape != b.shape:
        return MetricOutput(None, "silhouette-1", 0.0, ("Frames differ in size; cannot compare.",))
    la, lb = luminance(with_rgb), luminance(without_rgb)

    present = la - lb > 0.01
    changed = np.abs(la - lb) > 0.005
    if region is not None:
        mask = region.astype(bool)
        present &= mask
        changed &= mask

    union = int((present | changed).sum())
    iou = float((present & changed).sum() / union) if union else 0.0

    region_delta = float(np.mean(np.abs(la - lb)[present])) if present.any() else 0.0
    return MetricOutput(
        value=iou,
        algorithm_version="silhouette-1",
        confidence=0.7,
        limitations=(
            "Assumes the only difference between the two frames is the player; camera motion invalidates it.",
            "IoU rewards a clean occlusion, not a readable pose — a silhouette can be clean and dull.",
        ),
        detail={"iou": iou, "perceptual_delta": region_delta, "player_pixels": int(present.sum())},
    )


def horizon_roll(camera_roll_deg: float | None) -> MetricOutput:
    if camera_roll_deg is None:
        return MetricOutput(
            None,
            "horizon-1",
            0.0,
            ("No camera transform supplied; a horizon estimated from pixels is a guess, so it is refused.",),
        )
    return MetricOutput(
        value=float(abs(camera_roll_deg)),
        algorithm_version="horizon-1",
        confidence=1.0,
        limitations=("Trusts the engine transform; a mis-authored camera rig reports a confident wrong answer.",),
        detail={"camera_roll_deg": float(camera_roll_deg)},
    )


def palette_drift(rgb: np.ndarray, palette: tuple[str, ...], clusters: int = 6) -> MetricOutput:
    """CIELAB ΔE2000 between the image's dominant colours and the declared palette."""
    from skimage.color import deltaE_ciede2000, rgb2lab

    small = _downsample(rgb, 512)
    flat = to_float(small).reshape(-1, 3)
    quantised = (flat * 31).round().astype(np.int32)
    keys, inverse, counts = np.unique(quantised, axis=0, return_inverse=True, return_counts=True)

    order = np.argsort(counts)[::-1][:clusters]
    lab_pixels = rgb2lab(flat.reshape(1, -1, 3)).reshape(-1, 3)
    palette_rgb = np.array([[_hex_to_rgb(value)] for value in palette], dtype=np.float64) / 255.0
    palette_lab = rgb2lab(palette_rgb).reshape(-1, 3)

    weighted, detail = 0.0, []
    total = counts.sum()
    for index in order:
        members = inverse == index
        centroid = lab_pixels[members].mean(axis=0)
        # Compare one centroid against one swatch at a time: broadcasting two arrays
        # of differing length silently collapsed to a scalar in testing.
        distances = np.array(
            [float(np.asarray(deltaE_ciede2000(centroid.reshape(1, 3), swatch.reshape(1, 3))).ravel()[0])
             for swatch in palette_lab],
            dtype=np.float64,
        )
        nearest = int(np.argmin(distances))
        weight = float(counts[index]) / float(total)
        weighted += float(distances[nearest]) * weight
        detail.append({"swatch": palette[nearest], "delta_e": float(distances[nearest]), "weight": weight})

    return MetricOutput(
        value=weighted,
        algorithm_version="palette-de2000-1",
        confidence=0.6,
        limitations=(
            "Compares dominant colours to the palette, not every pixel; a small off-palette highlight is invisible.",
            "Lighting intentionally shifts hue and value, so the declared tolerance must stay modest.",
            "Coarse quantisation (5-bit per channel) can merge distinct swatches.",
        ),
        detail={"clusters": detail},
    )


def clutter(rgb: np.ndarray, focal: np.ndarray | None = None) -> MetricOutput:
    from skimage.filters import sobel

    small = _downsample(rgb, 768)
    y = luminance(small)
    edges = sobel(y)
    edge_density = float((edges > 0.05).mean())

    if focal is not None:
        focal_small = _downsample_mask(focal, small.shape[1], small.shape[0])
        outside = ~focal_small.astype(bool)
    else:
        outside = np.ones_like(y, dtype=bool)

    energy = edges[outside]
    saliency = float(energy.mean() / (edges.max() + 1e-9)) if energy.size else 0.0
    return MetricOutput(
        value=edge_density,
        algorithm_version="clutter-1",
        confidence=0.55,
        limitations=(
            "Edge density is a proxy for visual noise, not for narrative clarity.",
            "Textured stone reads as clutter even when it is the intended material.",
        ),
        detail={"edge_density": edge_density, "saliency": saliency, "focal_region_supplied": focal is not None},
    )


def lantern_dominance(rgb: np.ndarray, lantern_mask: np.ndarray | None) -> MetricOutput:
    if lantern_mask is None:
        return MetricOutput(None, "lantern-1", 0.0, ("No lantern mask supplied; brightness cannot be attributed.",))

    y = luminance(rgb)
    mask = lantern_mask.astype(bool)
    if not mask.any():
        return MetricOutput(None, "lantern-1", 0.0, ("Lantern mask is empty.",))

    lantern_peak = float(np.percentile(y[mask], 99))
    outside = y[~mask]
    outside_peak = float(np.percentile(outside, 99)) if outside.size else 0.0
    gap = lantern_peak - outside_peak
    return MetricOutput(
        value=gap,
        algorithm_version="lantern-1",
        confidence=0.8,
        limitations=(
            "Compares 99th percentiles, so a small specular highlight elsewhere is discounted.",
            "Requires the engine to identify the lantern region honestly.",
        ),
        detail={"lantern_peak": lantern_peak, "outside_peak": outside_peak, "gap": gap},
    )


def event_delta(before_rgb: np.ndarray, after_rgb: np.ndarray) -> MetricOutput:
    if before_rgb.shape != after_rgb.shape:
        return MetricOutput(None, "event-delta-1", 0.0, ("Frames differ in size.",))
    delta = float(np.mean(np.abs(luminance(after_rgb) - luminance(before_rgb))))
    return MetricOutput(
        value=delta,
        algorithm_version="event-delta-1",
        confidence=0.75,
        limitations=(
            "Global mean delta hides a localised but meaningful change.",
            "Camera movement alone produces a delta; pair this with a fixed-camera capture.",
        ),
        detail={"mean_abs_luminance_delta": delta},
    )


# --- helpers ----------------------------------------------------------------


def _rgb_to_hsv(rgb01: np.ndarray) -> np.ndarray:
    return _hsv(rgb01)


def _hsv(rgb01: np.ndarray) -> np.ndarray:
    """Vectorised RGB→HSV without an extra dependency."""
    r, g, b = rgb01[..., 0], rgb01[..., 1], rgb01[..., 2]
    maxc = np.max(rgb01, axis=-1)
    minc = np.min(rgb01, axis=-1)
    delta = maxc - minc
    hue = np.zeros_like(maxc)
    nonzero = delta > 1e-9
    red = nonzero & (maxc == r)
    green = nonzero & (maxc == g) & ~red
    blue = nonzero & ~red & ~green
    hue[red] = ((g - b)[red] / delta[red]) % 6
    hue[green] = ((b - r)[green] / delta[green]) + 2
    hue[blue] = ((r - g)[blue] / delta[blue]) + 4
    hue *= 60.0
    sat = np.where(maxc > 1e-9, delta / np.maximum(maxc, 1e-9), 0.0)
    return np.stack([hue / 360.0, sat, maxc], axis=-1)


def _downsample(rgb: np.ndarray, target: int) -> np.ndarray:
    height, width = rgb.shape[:2]
    scale = target / max(height, width)
    if scale >= 1:
        return rgb
    with Image.fromarray(rgb) as image:
        resized = image.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.BILINEAR)
        return np.asarray(resized, dtype=np.uint8)


def _detail_free(y: np.ndarray, tile: int, flat_std: float) -> np.ndarray:
    """Tiles with no local variation: the signature of fill rather than surface."""
    height, width = y.shape
    rows = max(1, height // tile)
    cols = max(1, width // tile)
    cropped = y[: rows * tile, : cols * tile]
    blocks = cropped.reshape(rows, tile, cols, tile).transpose(0, 2, 1, 3)
    per_tile = blocks.reshape(rows, cols, tile * tile).std(axis=2) < flat_std
    # Pad the tile grid so the repeated map covers a frame whose height or width
    # is not a whole number of tiles.
    pad_rows = 1 if height > rows * tile else 0
    pad_cols = 1 if width > cols * tile else 0
    if pad_rows or pad_cols:
        per_tile = np.pad(per_tile, ((0, pad_rows), (0, pad_cols)), mode="edge")
    return np.repeat(np.repeat(per_tile, tile, axis=0), tile, axis=1)[:height, :width]


def _match_mask(mask: np.ndarray, width: int, height: int) -> np.ndarray:
    mask = np.asarray(mask).astype(bool)
    if mask.shape == (height, width):
        return mask
    return _downsample_mask(mask, width, height)


def _downsample_mask(mask: np.ndarray, width: int, height: int) -> np.ndarray:
    with Image.fromarray((mask.astype(np.uint8) * 255)) as image:
        resized = image.resize((width, height), Image.NEAREST)
        return np.asarray(resized) > 127


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
