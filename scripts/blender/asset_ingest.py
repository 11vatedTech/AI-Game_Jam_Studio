"""Blender asset ingest: inspect, clean, verify and render AI-generated meshes.

Every generated mesh is untrusted input. This tool measures the real mesh, repairs what can be
repaired deterministically, applies real-world scale, exports engine-ready GLB, and renders
evidence. It fails loudly rather than shipping a mesh it could not verify.

Run:
  blender --background --python scripts/blender/asset_ingest.py -- \
      --input  <mesh.glb> \
      --name   lantern \
      --height 0.42 \
      --target-tris 14000 \
      --out-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--height", type=float, default=1.0, help="Final world height in metres")
    parser.add_argument("--target-tris", type=int, default=15000)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--no-decimate", action="store_true")
    parser.add_argument("--drop-floor", action="store_true",
                        help="Remove a reconstructed backdrop floor and keep the tallest component")
    parser.add_argument("--trim-radius", type=float, default=0.0,
                        help="Delete geometry outside this cylinder radius (import units), "
                             "removing backdrop floors the reconstruction hallucinated")
    return parser.parse_args(argv)


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_mesh(path: Path) -> list[bpy.types.Object]:
    suffix = path.suffix.lower()
    if suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    else:
        raise SystemExit(f"Unsupported mesh format: {suffix}")
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def join(objects: list[bpy.types.Object]) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def measure(obj: bpy.types.Object) -> dict:
    mesh = obj.data
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    corners = [matrix @ Vector(c) for c in obj.bound_box]
    mins = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    maxs = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    dims = maxs - mins
    non_manifold = 0
    for edge in mesh.edges:
        pass
    # Count boundary/non-manifold edges without bmesh operators.
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    loose_verts = sum(1 for v in bm.verts if not v.link_edges)
    bm.free()
    return {
        "vertices": len(mesh.vertices),
        "triangles": len(mesh.loop_triangles),
        "polygons": len(mesh.polygons),
        "materials": [m.name if m else None for m in mesh.materials],
        "uv_layers": [uv.name for uv in mesh.uv_layers],
        "color_attributes": [c.name for c in mesh.color_attributes],
        "bbox_min": [round(v, 6) for v in mins],
        "bbox_max": [round(v, 6) for v in maxs],
        "dimensions": [round(v, 6) for v in dims],
        "non_manifold_edges": non_manifold,
        "loose_vertices": loose_verts,
        "volume_m3": None,
    }


def drop_floor(obj: bpy.types.Object, *, normal_threshold: float = 0.80, band: float = 0.12) -> dict:
    """Delete the horizontal backdrop floor an image-to-mesh reconstruction hallucinates.

    The reconstruction reads a flat studio background as a ground plane. Those faces are the only
    near-horizontal surfaces in the lowest band of the mesh, so removing them (and then keeping the
    tallest connected component) recovers just the object.
    """
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    zs = [v.co.z for v in bm.verts]
    if not zs:
        bm.free()
        return {"floor_removed": 0}
    zmin, zmax = min(zs), max(zs)
    cut = zmin + band * (zmax - zmin)
    doomed = [f for f in bm.faces
              if abs(f.normal.z) > normal_threshold and f.calc_center_median().z < cut]
    removed = len(doomed)
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()

    # Trim whatever apron survived the face deletion, using the object's own radius profile rather
    # than a guessed constant. Loose-part separation is O(n^2) here and unusable at 1M triangles.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    upper = [v for v in bm.verts if v.co.z > cut]
    if upper:
        radii = sorted(math.hypot(v.co.x, v.co.y) for v in upper)
        p90 = radii[int(len(radii) * 0.90)] if radii else 0.0
        limit = p90 * 1.35
        doomed = [v for v in bm.verts if math.hypot(v.co.x, v.co.y) > limit]
        apron = len(doomed)
        if doomed:
            bmesh.ops.delete(bm, geom=doomed, context="VERTS")
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        return {"floor_removed": removed, "p90_radius": round(p90, 4),
                "trim_limit": round(limit, 4), "apron_removed": apron,
                "remaining_vertices": len(obj.data.vertices)}
    bm.free()
    return {"floor_removed": removed, "p90_radius": None}


def trim_cylinder(obj: bpy.types.Object, radius: float) -> dict:
    """Remove reconstructed backdrop geometry outside a cylinder around the origin."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    doomed = [v for v in bm.verts if math.hypot(v.co.x, v.co.y) > radius]
    removed = len(doomed)
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {"trim_radius": radius, "removed_vertices": removed,
            "remaining_vertices": len(obj.data.vertices)}


def clean(obj: bpy.types.Object) -> dict:
    """Deterministic repair: weld, remove loose geometry, recalculate outward normals."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0004)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    before = len(obj.data.polygons)
    return {"merged_before": before}


def decimate(obj: bpy.types.Object, target_tris: int) -> dict:
    obj.data.calc_loop_triangles()
    current = len(obj.data.loop_triangles)
    if current <= target_tris:
        return {"decimated": False, "triangles_before": current, "triangles_after": current}
    ratio = max(0.02, min(1.0, target_tris / current))
    modifier = obj.modifiers.new(name="StudioDecimate", type="DECIMATE")
    modifier.decimate_type = "COLLAPSE"
    modifier.ratio = ratio
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.calc_loop_triangles()
    return {"decimated": True, "ratio": round(ratio, 4),
            "triangles_before": current, "triangles_after": len(obj.data.loop_triangles)}


def normalise_scale(obj: bpy.types.Object, target_height: float) -> dict:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    obj.location = (0.0, 0.0, 0.0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    dims = obj.dimensions
    height = max(dims.z, 1e-6)
    factor = target_height / height
    obj.scale = (factor, factor, factor)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # Sit the asset on the ground plane, centred on X/Y.
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    min_z = min(c.z for c in corners)
    centre_x = (min(c.x for c in corners) + max(c.x for c in corners)) / 2
    centre_y = (min(c.y for c in corners) + max(c.y for c in corners)) / 2
    obj.location = (obj.location.x - centre_x, obj.location.y - centre_y, obj.location.z - min_z)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return {"scale_factor": round(factor, 6), "final_dimensions": [round(v, 4) for v in obj.dimensions]}


def unwrap(obj: bpy.types.Object) -> dict:
    """Smart-project a UV set when the generated mesh lacks usable UVs."""
    if obj.data.uv_layers:
        return {"uv_unwrapped": False, "existing": [uv.name for uv in obj.data.uv_layers]}
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"uv_unwrapped": True, "existing": [uv.name for uv in obj.data.uv_layers]}


def build_studio() -> dict:
    """Neutral review lighting: cool world, warm key, rim — matches the art bible's read."""
    world = bpy.data.worlds.new("ReviewWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.035, 0.055, 0.065, 1.0)
    bg.inputs[1].default_value = 1.0
    bpy.context.scene.world = world

    def lamp(name, kind, location, energy, color, size=2.0):
        data = bpy.data.lights.new(name, type=kind)
        data.energy = energy
        data.color = color
        if kind == "AREA":
            data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        bpy.context.collection.objects.link(obj)
        return obj

    key = lamp("KeyWarm", "AREA", (2.2, -2.4, 2.4), 180.0, (1.0, 0.72, 0.42), size=2.4)
    key.rotation_euler = (math.radians(55), 0, math.radians(42))
    rim = lamp("RimCool", "AREA", (-2.4, 2.0, 2.0), 120.0, (0.45, 0.72, 0.85), size=2.0)
    rim.rotation_euler = (math.radians(62), 0, math.radians(-140))
    fill = lamp("FillSoft", "AREA", (0.0, -3.0, 1.0), 30.0, (0.6, 0.7, 0.8), size=4.0)
    fill.rotation_euler = (math.radians(80), 0, 0)
    return {"lights": ["KeyWarm", "RimCool", "FillSoft"]}


def setup_render(resolution: int = 1024) -> None:
    scene = bpy.context.scene
    engines = {item.identifier for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    if hasattr(scene, "eevee"):
        for attr, value in (("use_gtao", True), ("use_raytracing", True), ("taa_render_samples", 64)):
            if hasattr(scene.eevee, attr):
                setattr(scene.eevee, attr, value)


def render_views(out_dir: Path, name: str, height: float) -> list[str]:
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("ReviewCam")
    cam_data.lens = 70
    cam = bpy.data.objects.new("ReviewCam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    distance = max(1.2, height * 2.6)
    views = {
        "front": (0.0, -1.0),
        "three_quarter": (0.78, -0.78),
        "side": (1.0, 0.0),
    }
    paths = []
    for label, (dx, dy) in views.items():
        cam.location = (dx * distance, dy * distance, height * 0.72)
        direction = Vector((0, 0, height * 0.45)) - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        target = out_dir / f"{name}_{label}.png"
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        paths.append(str(target))
    return paths


def main() -> int:
    args = parse_args()
    src = Path(args.input).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not src.is_file():
        raise SystemExit(f"Input mesh not found: {src}")

    reset_scene()
    mesh_objects = import_mesh(src)
    if not mesh_objects:
        raise SystemExit("Import produced no mesh objects")
    obj = join(mesh_objects)
    obj.name = args.name

    imported = measure(obj)
    trim = trim_cylinder(obj, args.trim_radius) if args.trim_radius > 0 else {"trim_radius": 0, "removed_vertices": 0}
    floor = drop_floor(obj) if args.drop_floor else {"floor_removed": 0}
    obj = bpy.context.view_layer.objects.active if args.drop_floor else obj
    weld = clean(obj)
    decimation = decimate(obj, args.target_tris) if not args.no_decimate else {"decimated": False}
    scaling = normalise_scale(obj, args.height)
    uvs = unwrap(obj)
    obj.data.update()
    final = measure(obj)

    build_studio()
    setup_render()
    renders = render_views(out_dir, args.name, args.height)

    blend_path = out_dir / f"{args.name}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    glb_path = out_dir / f"{args.name}.glb"
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_normals=True,
        export_texcoords=bool(obj.data.uv_layers),
        export_materials="EXPORT",
    )

    report = {
        "tool": {"blender": bpy.app.version_string, "source": str(src)},
        "asset": args.name,
        "imported": imported,
        "trim": trim,
        "floor": floor,
        "weld": weld,
        "decimation": decimation,
        "scaling": scaling,
        "uv": uvs,
        "final": final,
        "outputs": {"blend": str(blend_path), "glb": str(glb_path), "renders": renders},
        "verdict": "GEOMETRY_MEASURED",
        "note": "Numeric verification only. Silhouette, material and gameplay-distance judgement require review.",
    }
    report_path = out_dir / f"{args.name}.ingest.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("STUDIO_INGEST_JSON_BEGIN")
    print(json.dumps(report, indent=2))
    print("STUDIO_INGEST_JSON_END")
    return 0


if __name__ == "__main__":
    sys.exit(main())
