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
        detail={
            "p1": float(p1),
            "p5": float(p5),
            "p50": float(p50),
            "p95": float(p95),
            "p99": float(p99),
            **_measure(
                numerator=None,
                denominator=int(y.size),
                denominator_semantics="every luminance sample in the frame",
                included=["whole frame"],
            ),
        },
    )


def luminance_cause(
    rgb: np.ndarray,
    occupancy: np.ndarray | None,
    floor: float,
    *,
    band_count: int = 8,
    tile: int = 32,
    flat_std: float = 0.002,
    control_rgb: np.ndarray | None = None,
    contribution_min: float = 0.25,
) -> MetricOutput:
    """Measure why a frame is dark, and claim no more cause than the inputs support.

    Three independent questions, kept apart because they fail apart:

      coverage          is a rendered surface at this pixel?       (needs a coverage mask)
      surface detail    does the region carry readable variation?  (measured from pixels)
      illumination      does scene light reach that surface?       (needs a lights-off control)

    Detail is a property of the pixels; illumination is a property of the lighting rig.
    A smooth near-black surface is low detail whether or not any light reaches it, so
    calling it "unlit" on a variance measurement would be a cause asserted past its
    evidence — the same mistake this metric exists to prevent. Without a control capture
    at identical exposure the illumination dimension stays `undetermined`, and the
    diagnosis reports only what was measured.

    The value is the share of below-floor pixels sitting where nothing was drawn. It is
    never thresholded: a diagnosis explains a verdict, it does not set one.
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
        "Illumination response requires a control capture with the scene lights disabled at identical exposure; one frame cannot separate light from albedo.",
    ]

    gap_bands: list[int] = []
    sky_bands: list[int] = []
    gap_share = sky_share = 0.0
    geometry_share: float | None = None
    first_geometry: int | None = None
    coverage_state = "undetermined"

    if geometry is not None:
        first_geometry = next((b["index"] for b in bands if (b["geometry_share"] or 0.0) >= 0.02), None)
        empty = [b["index"] for b in bands if (b["geometry_share"] or 0.0) < 0.02]
        # Above the first band carrying geometry there is no sky to be above only when
        # geometry exists at all; an entirely empty frame has no sky, only absence.
        sky_bands = [] if first_geometry is None else [i for i in empty if i < first_geometry]
        gap_bands = [i for i in empty if first_geometry is None or i > first_geometry]

        if dark_total:
            # Pixel-level, not band-level: a hole in the middle of a lit band is missing
            # coverage too, and averaging it into the band would hide it.
            sky_rows = 0 if first_geometry is None else bands[first_geometry]["rows"][0]
            uncovered = dark & ~geometry
            sky_share = float(dark[:sky_rows].sum()) / dark_total
            gap_share = float(uncovered[sky_rows:].sum()) / dark_total
            geometry_share = float((dark & geometry).sum()) / dark_total
        coverage_state = "absent" if gap_share >= 0.5 else "present"

    detail_free_share = float((dark & flat).sum()) / dark_total if dark_total else 0.0

    if dark_total == 0:
        detail_state = "undetermined"
    elif detail_free_share >= 0.5:
        detail_state = "low_variance"
    elif detail_free_share <= 0.2:
        detail_state = "detailed"
    else:
        detail_state = "undetermined"

    contribution: float | None = None
    if control_rgb is None:
        illumination_state = "undetermined"
        illumination_basis = (
            "no lights-off control at identical exposure, so light and albedo cannot be separated"
        )
    else:
        region = dark & geometry if geometry is not None else dark
        if not region.any():
            illumination_state = "undetermined"
            illumination_basis = "no pixels below the floor to compare against the control"
        else:
            on = float(y[region].mean())
            off = float(luminance(control_rgb)[region].mean())
            contribution = (on - off) / max(on, 1e-9)
            illumination_state = (
                "low_contribution" if contribution < contribution_min else "adequate_contribution"
            )
            illumination_basis = (
                f"mean luminance over the dark region rises {contribution:.2f} when scene lights are enabled "
                f"({off:.4f} -> {on:.4f})"
            )

    cannot_distinguish: list[str] = []
    if geometry is None:
        cannot_distinguish.append("whether a surface is present at all")
    elif gap_share >= 0.1 and sky_share >= 0.1:
        cannot_distinguish.append("sky from unrendered void where both are unsegmented")
    if dark_total and detail_state == "undetermined":
        cannot_distinguish.append(
            f"low-variance and detailed pixels are both present ({detail_free_share:.2f} detail-free)"
        )
    if dark_total and illumination_state == "undetermined":
        cannot_distinguish.append("a surface too dark to light from light that never reaches it")

    if dark_total == 0:
        kind, claim = "no_darkness", "measured"
        basis = ["no pixels below the floor"]
    elif geometry is None:
        kind, claim = "undetermined", "undetermined"
        basis = ["coverage is unknown: no scene_coverage mask was captured"]
    elif first_geometry is None:
        kind, claim = "missing_coverage", "measured"
        basis = [
            f"no band of {band_count} contains rendered geometry",
            f"{dark_total} pixels below the floor sit where nothing was drawn",
        ]
    elif sky_share >= 0.5:
        kind, claim = "dark_sky", "measured"
        basis = [f"{sky_share:.2f} of dark pixels sit above all rendered geometry"]
    elif gap_share >= 0.5:
        kind, claim = "missing_coverage", "measured"
        basis = [
            f"{gap_share:.2f} of pixels below the floor sit in {len(gap_bands)} band(s) with no rendered geometry: {gap_bands}",
            f"rendered geometry first appears in band {first_geometry}",
        ]
    elif illumination_state == "low_contribution":
        kind, claim = "underlit_surface", "measured"
        basis = [f"{geometry_share:.2f} of dark pixels lie on rendered geometry", illumination_basis]
    elif detail_state == "low_variance":
        kind, claim = "dark_low_detail_surface", "measured"
        basis = [
            f"{geometry_share:.2f} of dark pixels lie on rendered geometry",
            f"{detail_free_share:.2f} of them are in detail-free tiles",
            f"illumination response is {illumination_state}",
        ]
    elif detail_state == "detailed":
        kind, claim = "dark_detailed_surface", "measured"
        basis = [
            f"{geometry_share:.2f} of dark pixels lie on rendered geometry",
            f"only {detail_free_share:.2f} of them are detail-free, so the darkness has structure",
            f"illumination response is {illumination_state}",
        ]
    else:
        kind, claim = "undetermined", "undetermined"
        basis = [
            f"{geometry_share:.2f} of dark pixels lie on rendered geometry",
            f"{detail_free_share:.2f} of them are detail-free, which separates neither case",
        ]

    if claim == "measured" and illumination_state == "undetermined" and kind != "missing_coverage":
        # Coverage and detail are measured; illumination is not. That does not weaken
        # the diagnosis, it bounds it: the kind describes the surface, not the lighting.
        limitations = tuple(limitations) + (
            "The diagnosis describes the surface; it does not attribute the darkness to the lighting rig.",
        )

    return MetricOutput(
        value=None if geometry is None else float(gap_share),
        algorithm_version="lum-cause-2",
        confidence=0.9 if claim == "measured" else 0.0,
        limitations=tuple(limitations) + tuple(cannot_distinguish),
        detail={
            "floor": floor,
            "dark_share": dark_total / float(y.size),
            "bands": bands,
            "coverage": {
                "state": coverage_state,
                "source": "mask_world_occupancy",
                "gap_bands": gap_bands,
                "sky_bands": sky_bands,
                "dark_share_without_geometry": gap_share,
            },
            "surface_detail": {
                "state": detail_state,
                "detail_free_share": detail_free_share,
                "tile_std_threshold": flat_std,
                "source": "local standard deviation of luminance",
            },
            "illumination_response": {
                "state": illumination_state,
                "contribution": contribution,
                "basis": illumination_basis,
                "source": "lights-off control capture at identical exposure",
            },
            "diagnosis": {
                "kind": kind,
                "confidence": claim,
                "basis": basis,
                "cannot_distinguish": cannot_distinguish,
            },
            "dark_over_geometry_share": geometry_share,
            "detail_free_dark_share": detail_free_share,
            **_measure(
                numerator=dark_total,
                denominator=int(y.size),
                denominator_semantics="all frame pixels",
                included=["whole frame"],
            ),
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
        detail={
            "world_pixels": total,
            "warm_pixels": int((warm & world).sum()),
            **_measure(
                numerator=int((warm & world).sum()),
                denominator=total,
                denominator_semantics="pixels selected by the world mask",
                included=["geometry the engine reports as world"],
                excluded=["sky and UI, which the world mask should not select"],
            ),
        },
    )


def warm_share_frame(rgb: np.ndarray, band: dict) -> MetricOutput:
    """Whole-frame warm coverage: warm pixels over every pixel that exists.

    Kept beside `warm_share` because the two answer different questions. The world
    denominator asks "of the scene, how much is warm"; this one asks "of the image the
    player sees, how much is warm". A small dark scene region dilutes the second and not
    the first, so neither can stand in for the other until art direction says which
    one governs the requirement.
    """
    hsv = _rgb_to_hsv(to_float(rgb))
    hue, sat, val = hsv[..., 0] * 360.0, hsv[..., 1], hsv[..., 2]
    low, high = band["hue_deg"]
    warm = (hue >= low) & (hue <= high) & (sat >= band["sat_min"]) & (val >= band["val_min"])

    total = int(warm.size)
    numerator = int(warm.sum())
    return MetricOutput(
        value=float(numerator / total) if total else None,
        algorithm_version="warm-share-frame-1",
        confidence=0.85 if band["sat_min"] > 0 else 0.6,
        limitations=(
            "HSV classification is hue-band based; a warm object under strong blue light is undercounted.",
            "Includes background and sky, so it measures the image rather than the scene.",
        ),
        detail={
            "warm_pixels": numerator,
            **_measure(
                numerator=numerator,
                denominator=total,
                denominator_semantics="all frame pixels, background included",
                included=["whole frame"],
                excluded=[],
            ),
        },
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
        detail={
            "iou": iou,
            "perceptual_delta": region_delta,
            "player_pixels": int(present.sum()),
            **_measure(
                numerator=int((present & changed).sum()),
                denominator=union,
                denominator_semantics="union of pixels the player occupies in either frame",
                included=["with-player and without-player frames"]
                + ([] if region is None else ["the supplied region mask"]),
            ),
        },
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
        detail={
            "camera_roll_deg": float(camera_roll_deg),
            **_measure(
                numerator=None,
                denominator=None,
                denominator_semantics="engine camera transform, not a pixel measurement",
                included=["the rig transform"],
                excluded=["pixels; estimating roll from them is refused"],
            ),
        },
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
        detail={
            "clusters": detail,
            **_measure(
                numerator=None,
                denominator=int(small.shape[0] * small.shape[1]),
                denominator_semantics="sampled pixels (frame downsampled to 512px)",
                included=[f"{clusters} most common quantised colours"],
                excluded=["rare colours below the quantisation count, weighted out by cluster share"],
            ),
        },
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
        detail={
            "edge_density": edge_density,
            "saliency": saliency,
            "focal_region_supplied": focal is not None,
            **_measure(
                numerator=int((edges > 0.05).sum()),
                denominator=int(edges.size),
                denominator_semantics="gradient samples of the frame downsampled to 768px",
                included=["whole frame"] if focal is None else ["pixels outside the focal mask"],
                excluded=[] if focal is None else ["focal region, which is allowed to be busy"],
            ),
        },
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
        detail={
            "lantern_peak": lantern_peak,
            "outside_peak": outside_peak,
            "gap": gap,
            **_measure(
                numerator=None,
                denominator=int(mask.sum()),
                denominator_semantics="pixels inside the lantern mask (the comparison denominator is the frame outside it)",
                included=["lantern mask", "pixels outside the lantern mask"],
            ),
        },
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
        detail={
            "mean_abs_luminance_delta": delta,
            **_measure(
                numerator=None,
                denominator=int(before_rgb.shape[0] * before_rgb.shape[1]),
                denominator_semantics="every pixel common to both frames",
                included=["whole frame", "both frames of the pair"],
            ),
        },
    )


# --- helpers ----------------------------------------------------------------


def _measure(
    *,
    numerator: int | None,
    denominator: int | None,
    denominator_semantics: str,
    included: Sequence[str],
    excluded: Sequence[str] = (),
) -> dict[str, Any]:
    """The disclosure every metric owes a reader who wants to challenge it.

    A ratio without its numerator and denominator is not reproducible: 0.006 could be
    6% of the scene or 0.6% of the image. Reporting both, plus what was deliberately
    left out, lets a later reader disagree with the metric instead of arguing about it.
    """
    return {
        "numerator": numerator,
        "denominator": denominator,
        "denominator_semantics": denominator_semantics,
        "included_regions": list(included),
        "excluded_regions": list(excluded),
    }


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
