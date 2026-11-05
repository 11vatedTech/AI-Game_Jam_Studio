"""Deterministic Blender authoring for EMBERKEEP.

These are *authored* meshes with real topology and deliberate material separation, not
reconstructed blobs: the hero lantern needs a transparent glass shell and an emissive core that
image-to-mesh cannot give us, and the architecture needs controlled dimensions for gameplay.

Run:
  blender --background --python scripts/blender/author_assets.py -- --kind lantern --out-dir <dir>
  blender --background --python scripts/blender/author_assets.py -- --kind environment --out-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

TAU = math.tau

# Art bible palette (linear-ish sRGB values used as base colours).
INK = (0.012, 0.020, 0.028, 1.0)
SLATE = (0.055, 0.095, 0.115, 1.0)
MIST = (0.145, 0.235, 0.260, 1.0)
BONE = (0.700, 0.640, 0.560, 1.0)
LANTERN = (1.000, 0.545, 0.155, 1.0)
EMBER = (1.000, 0.260, 0.060, 1.0)
BRASS = (0.310, 0.215, 0.105, 1.0)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=["lantern", "environment", "lamplighter"])
    parser.add_argument("--out-dir", required=True)
    return parser.parse_args(argv)


def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0


def material(name: str, base, *, metallic=0.0, roughness=0.5, emission=None, emission_strength=0.0,
             alpha=1.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = base
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    if emission is not None:
        for key in ("Emission Color", "Emission"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = emission
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        mat.blend_method = "BLEND" if hasattr(mat, "blend_method") else mat.blend_method
        mat.use_backface_culling = False
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
    return mat


def new_object(name: str, bm: bmesh.types.BMesh, mat: bpy.types.Material) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    mesh.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def lathe(name: str, profile: list[tuple[float, float]], mat: bpy.types.Material,
          segments: int = 48, close_bottom=True, close_top=True) -> bpy.types.Object:
    """Revolve an (radius, z) profile around Z. Profile must run bottom → top."""
    bm = bmesh.new()
    verts = [bm.verts.new((max(r, 1e-5), 0.0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    geom = verts + edges
    bmesh.ops.spin(bm, geom=geom, cent=(0, 0, 0), axis=(0, 0, 1), dvec=(0, 0, 0),
                   angle=TAU, steps=segments, use_merge=True, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    if close_bottom and profile[0][0] > 1e-4:
        cap = [v for v in bm.verts if abs(v.co.z - profile[0][1]) < 1e-5]
        if len(cap) > 2:
            try:
                bmesh.ops.contextual_create(bm, geom=cap)
            except Exception:
                pass
    if close_top and profile[-1][0] > 1e-4:
        cap = [v for v in bm.verts if abs(v.co.z - profile[-1][1]) < 1e-5]
        if len(cap) > 2:
            try:
                bmesh.ops.contextual_create(bm, geom=cap)
            except Exception:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_object(name, bm, mat)


def box(name: str, size, location, mat: bpy.types.Material, bevel=0.01, rotation_z=0.0) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    obj = new_object(name, bm, mat)
    obj.location = location
    obj.rotation_euler = (0, 0, rotation_z)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(35)
    return obj


def torus(name: str, major: float, minor: float, mat: bpy.types.Material, location=(0, 0, 0),
          major_segments=40, minor_segments=10) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=major_segments, minor_segments=minor_segments,
                                     location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def arc_bar(name: str, radius: float, thickness: float, mat: bpy.types.Material,
            z: float = 0.0, start=0.0, end=math.pi, plane: str = "XZ") -> bpy.types.Object:
    """Sweep a circular arc. plane='XZ' makes a carry-bail; 'XY' makes a flat hoop."""
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = thickness
    curve.bevel_resolution = 3
    curve.resolution_u = 8
    spline = curve.splines.new("POLY")
    steps = 32
    spline.points.add(steps)
    for i in range(steps + 1):
        a = start + (end - start) * i / steps
        if plane == "XZ":
            co = (math.cos(a) * radius, 0.0, z + math.sin(a) * radius)
        else:
            co = (math.cos(a) * radius, math.sin(a) * radius, z)
        spline.points[i].co = (*co, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return bpy.context.active_object


def apply_bevel(obj: bpy.types.Object, width: float, segments: int = 2, angle=35.0) -> None:
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)


def shade(obj: bpy.types.Object, angle=38.0) -> None:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    except Exception:
        bpy.ops.object.shade_smooth()


def export(objects: list[bpy.types.Object], path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True,
        export_apply=True, export_yup=True, export_normals=True, export_materials="EXPORT",
    )


def stats(objects: list[bpy.types.Object]) -> dict:
    total_tris = 0
    per = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        tris = len(obj.data.loop_triangles)
        total_tris += tris
        per.append({"name": obj.name, "triangles": tris,
                    "materials": [m.name for m in obj.data.materials if m]})
    return {"objects": len(per), "triangles": total_tris, "detail": per}


# --------------------------------------------------------------------------- lantern

def build_lantern() -> list[bpy.types.Object]:
    brass = material("BRASS_AGED", BRASS, metallic=1.0, roughness=0.42)
    stone = material("STONE_WET", SLATE, metallic=0.0, roughness=0.38)
    glass = material("GLASS_LANTERN", (0.92, 0.74, 0.52, 1.0), metallic=0.0, roughness=0.04,
                     alpha=0.12, emission=LANTERN, emission_strength=0.12)
    core = material("EMBER_CORE", LANTERN, metallic=0.0, roughness=1.0,
                    emission=LANTERN, emission_strength=14.0)

    parts: list[bpy.types.Object] = []
    # Base foot: a worn brass plinth with a chamfered lip.
    foot = lathe("Lantern_Foot", [
        (0.000, 0.000), (0.052, 0.000), (0.056, 0.007), (0.050, 0.016),
        (0.044, 0.020), (0.036, 0.048), (0.030, 0.054),
    ], brass, segments=40)
    parts.append(foot)
    # Fuel tank.
    parts.append(lathe("Lantern_Tank", [
        (0.030, 0.052), (0.056, 0.060), (0.062, 0.078), (0.058, 0.100),
        (0.048, 0.108), (0.036, 0.112),
    ], brass, segments=40))
    # Glass globe (transparent shell, slightly emissive so it reads in fog).
    parts.append(lathe("Lantern_Glass", [
        (0.034, 0.112), (0.050, 0.126), (0.064, 0.150), (0.068, 0.172),
        (0.062, 0.196), (0.048, 0.212), (0.034, 0.220),
    ], glass, segments=40, close_bottom=False, close_top=False))
    # Ember core.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.021,
                                         location=(0, 0, 0.168))
    ember = bpy.context.active_object
    ember.name = "Lantern_Core"
    ember.data.materials.append(core)
    parts.append(ember)
    # Crown / vent cap: flared collar, squat dome, finial.
    parts.append(lathe("Lantern_Crown", [
        (0.034, 0.220), (0.050, 0.224), (0.052, 0.234), (0.046, 0.238),
        (0.048, 0.246), (0.040, 0.254), (0.026, 0.262), (0.014, 0.268),
        (0.010, 0.274), (0.000, 0.278),
    ], brass, segments=40))
    # Guard cage: three uprights with wrap-around hoop.
    for i in range(3):
        angle = TAU * i / 3
        bar = box(f"Lantern_Bar_{i}", (0.009, 0.009, 0.150),
                  (math.cos(angle) * 0.074, math.sin(angle) * 0.074, 0.168),
                  brass, bevel=0.0022, rotation_z=angle)
        parts.append(bar)
    parts.append(torus("Lantern_Hoop_Low", 0.072, 0.005, brass, (0, 0, 0.104), 36, 8))
    parts.append(torus("Lantern_Hoop_High", 0.072, 0.005, brass, (0, 0, 0.232), 36, 8))
    # Bail handle: half arc standing up over the crown, the silhouette signature of the prop.
    parts.append(arc_bar("Lantern_Handle", 0.070, 0.0055, brass, z=0.232, plane="XZ"))
    # Small brass collar at handle roots.
    for sx in (-1, 1):
        parts.append(box(f"Lantern_HandleRoot_{sx}", (0.018, 0.016, 0.014),
                         (sx * 0.070, 0, 0.232), brass, bevel=0.002))

    for obj in parts:
        shade(obj, 40.0)
    return parts


# ----------------------------------------------------------------------- environment

def build_lamplighter() -> list[bpy.types.Object]:
    """A cloaked lamplighter whose silhouette reads at 64 px: hood, cloak, hem, boots, lantern arm."""
    cloth = material("CLOTH_DARK", (0.028, 0.042, 0.055, 1.0), metallic=0.0, roughness=0.82)
    trim = material("CLOTH_TRIM", (0.42, 0.375, 0.315, 1.0), metallic=0.0, roughness=0.72)
    leather = material("LEATHER_WORN", (0.075, 0.055, 0.042, 1.0), metallic=0.0, roughness=0.55)

    parts: list[bpy.types.Object] = []
    # Cloak body: narrow at the shoulders, flaring to an uneven hem.
    parts.append(lathe("Lamplighter_Cloak", [
        (0.000, 0.000), (0.300, 0.010), (0.292, 0.180), (0.268, 0.430),
        (0.236, 0.700), (0.214, 0.900), (0.226, 1.050), (0.252, 1.140),
        (0.236, 1.230), (0.150, 1.300), (0.000, 1.330),
    ], cloth, segments=40))
    # Shoulder mantle: a slightly lighter band that catches the rim light.
    parts.append(lathe("Lamplighter_Mantle", [
        (0.238, 1.120), (0.268, 1.150), (0.262, 1.230), (0.232, 1.290), (0.150, 1.320),
    ], trim, segments=40, close_bottom=False))
    # Hood: a deep cowl that hides the face entirely — faces are a rights and craft liability.
    parts.append(lathe("Lamplighter_Hood", [
        (0.150, 1.275), (0.176, 1.360), (0.170, 1.470), (0.140, 1.560),
        (0.092, 1.615), (0.040, 1.640), (0.000, 1.648),
    ], cloth, segments=36))
    # Belt.
    parts.append(torus("Lamplighter_Belt", 0.243, 0.024, leather, (0, 0, 0.960), 36, 8))
    # Boots.
    for sx in (-1, 1):
        parts.append(box(f"Lamplighter_Boot_{sx}", (0.115, 0.250, 0.120),
                         (sx * 0.088, 0.030, 0.060), leather, bevel=0.02))
    # Lantern arm: reaches forward-right to carry the prop.
    arm = box("Lamplighter_Arm", (0.098, 0.098, 0.420), (0.235, -0.115, 0.985), cloth, bevel=0.03)
    arm.rotation_euler = (math.radians(24), 0, math.radians(-16))
    parts.append(arm)
    parts.append(box("Lamplighter_Hand", (0.090, 0.090, 0.090), (0.300, -0.245, 0.815), leather, bevel=0.03))
    # Left arm hangs by the side.
    left = box("Lamplighter_ArmLeft", (0.088, 0.088, 0.400), (-0.245, 0.0, 0.980), cloth, bevel=0.03)
    left.rotation_euler = (0, 0, math.radians(6))
    parts.append(left)

    for obj in parts:
        shade(obj, 42.0)
    return parts


def build_environment() -> list[bpy.types.Object]:
    stone = material("STONE_WET", SLATE, metallic=0.0, roughness=0.34)
    stone_dark = material("STONE_DEEP", INK, metallic=0.0, roughness=0.42)
    stone_light = material("STONE_WORN", MIST, metallic=0.0, roughness=0.30)
    brass = material("BRASS_AGED", BRASS, metallic=1.0, roughness=0.45)

    parts: list[bpy.types.Object] = []
    deck_z = 0.0

    # Main terrace deck, 26 x 22, sitting in water at z = 0.
    deck = box("Deck", (26.0, 22.0, 0.9), (0, 0, deck_z - 0.45), stone, bevel=0.06)
    apply_bevel(deck, 0.05, 3)
    parts.append(deck)

    # Raised inner sanctum platform with steps on its south side.
    parts.append(box("Sanctum", (10.0, 8.0, 0.55), (0, 3.0, deck_z + 0.275), stone_light, bevel=0.05))
    for i in range(3):
        h = 0.18 * (i + 1)
        parts.append(box(f"Step_{i}", (5.2, 0.42, h), (0, -1.4 + 0.42 * (2 - i), deck_z + h / 2),
                         stone_light, bevel=0.03))

    # Perimeter parapet: low wall segments with gaps, so the eye reads ruin, not fence.
    for side, (length, axis) in {"north": (26.0, "x"), "south": (26.0, "x"),
                                 "east": (22.0, "y"), "west": (22.0, "y")}.items():
        segments = 5
        seg_len = length / segments
        for i in range(segments):
            if (i + (0 if side in ("north", "east") else 1)) % 3 == 2:
                continue  # collapsed section
            offset = -length / 2 + seg_len * (i + 0.5)
            height = 0.95 if (i % 2 == 0) else 0.72
            if side == "north":
                loc = (offset, 10.6, deck_z + height / 2)
                size = (seg_len * 0.94, 0.42, height)
            elif side == "south":
                loc = (offset, -10.6, deck_z + height / 2)
                size = (seg_len * 0.94, 0.42, height)
            elif side == "east":
                loc = (12.6, offset, deck_z + height / 2)
                size = (0.42, seg_len * 0.94, height)
            else:
                loc = (-12.6, offset, deck_z + height / 2)
                size = (0.42, seg_len * 0.94, height)
            parts.append(box(f"Parapet_{side}_{i}", size, loc, stone, bevel=0.035))

    # Arch module: a repeating vertical that gives the composition its height.
    def arch(name: str, location, scale: float, rotation_z: float = 0.0):
        px, py, pz = location
        pillar_h = 3.1 * scale
        gap = 1.35 * scale
        pillar_w = 0.52 * scale
        for sign in (-1, 1):
            parts.append(box(f"{name}_Pillar_{sign}", (pillar_w, 0.62 * scale, pillar_h),
                             (px + sign * gap, py, pz + pillar_h / 2), stone, bevel=0.04))
        band = torus(f"{name}_Band", gap, 0.26 * scale, stone, (px, py, pz + pillar_h), 32, 8)
        # Cut the lower half of the torus so it reads as an arch, not a ring.
        bpy.context.view_layer.objects.active = band
        bpy.ops.object.select_all(action="DESELECT")
        band.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.transform.resize(value=(1.0, 1.0, 1.0))
        bpy.ops.object.mode_set(mode="OBJECT")
        bm = bmesh.new()
        bm.from_mesh(band.data)
        doomed = [v for v in bm.verts if v.co.z < -0.02 * scale]
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
        bm.to_mesh(band.data)
        bm.free()
        parts.append(band)
        parts.append(box(f"{name}_Keystone", (0.5 * scale, 0.7 * scale, 0.42 * scale),
                         (px, py, pz + pillar_h + gap + 0.18 * scale), stone_light, bevel=0.04))

    arch("Arch_NW", (-7.0, 7.5, deck_z), 1.0)
    arch("Arch_NE", (7.0, 7.5, deck_z), 1.0)
    arch("Arch_W", (-9.4, -2.0, deck_z), 0.86)
    arch("Arch_E", (9.4, -2.0, deck_z), 0.86)

    # Pylon sockets: brass ring inlayed into a stone drum, one per beacon.
    for idx, (px, py, pz) in enumerate([(-5.2, -4.4, deck_z), (5.2, -4.4, deck_z), (0.0, 5.4, deck_z + 0.55)]):
        parts.append(lathe(f"PylonSocket_{idx}", [
            (0.0, 0.0), (0.95, 0.0), (0.98, 0.10), (0.92, 0.22), (0.84, 0.24),
        ], stone_light, segments=36))
        parts[-1].location = (px, py, pz)
        ring = torus(f"PylonRing_{idx}", 0.80, 0.045, brass, (px, py, pz + 0.245), 40, 8)
        parts.append(ring)

    # Rubble: irregular shattered blocks, each uniquely rotated and scaled.
    rubble_data = [
        (-8.5, -7.4, 0.34, 13), (-3.0, -8.6, 0.26, 47), (6.2, -7.8, 0.40, 91),
        (10.4, 0.8, 0.30, 22), (-10.8, 3.4, 0.36, 65), (2.6, -2.4, 0.18, 8),
        (-1.2, 8.4, 0.22, 33), (8.2, 6.2, 0.28, 77),
    ]
    for i, (rx, ry, size, seed) in enumerate(rubble_data):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=size)
        bm.verts.ensure_lookup_table()
        for j, v in enumerate(bm.verts):
            wobble = 1.0 + 0.22 * math.sin(seed + j * 2.3)
            v.co *= wobble
        block = new_object(f"Rubble_{i}", bm, stone_dark)
        block.location = (rx, ry, deck_z + size * 0.42)
        block.rotation_euler = (0.15, 0.1, seed * 0.17)
        apply_bevel(block, 0.02, 2, 45)
        parts.append(block)

    for obj in parts:
        shade(obj, 34.0)
    return parts


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reset()

    if args.kind == "lantern":
        parts = build_lantern()
        glb = out_dir / "lantern_hero.glb"
        blend = out_dir / "lantern_hero.blend"
    elif args.kind == "lamplighter":
        parts = build_lamplighter()
        glb = out_dir / "lamplighter.glb"
        blend = out_dir / "lamplighter.blend"
    else:
        parts = build_environment()
        glb = out_dir / "shrine_terrace.glb"
        blend = out_dir / "shrine_terrace.blend"

    info = stats(parts)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    export([o for o in parts if o.type == "MESH"], glb)
    report = {"kind": args.kind, "blender": bpy.app.version_string,
              "glb": str(glb), "blend": str(blend), "geometry": info}
    (out_dir / f"{args.kind}.author.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("STUDIO_AUTHOR_JSON_BEGIN")
    print(json.dumps(report, indent=2))
    print("STUDIO_AUTHOR_JSON_END")
    return 0


if __name__ == "__main__":
    sys.exit(main())
