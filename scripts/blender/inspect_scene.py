"""Blender scene inspector for the Studio's typed `blender.inspect_scene` operation.

Runs headless: `blender --background <blend> --python inspect_scene.py`.
Reads inputs from the environment (Blender has no safe argv channel here):
  STUDIO_BLEND  absolute path of the .blend file to open (required)
  STUDIO_OUT    absolute path of the JSON report to write (required)

Prints exactly one machine-readable line prefixed with STUDIO_INSPECT_JSON.
Never writes to the .blend file and never touches the network.
"""
import json
import os
import sys

try:
    import bpy
except ImportError:
    print("STUDIO_INSPECT_JSON " + json.dumps({"ok": False, "error": "not_running_inside_blender"}))
    raise SystemExit(1)


def main() -> int:
    blend = os.environ.get("STUDIO_BLEND", "")
    out = os.environ.get("STUDIO_OUT", "")
    if not blend or not out:
        print("STUDIO_INSPECT_JSON " + json.dumps({"ok": False, "error": "STUDIO_BLEND and STUDIO_OUT are required"}))
        return 2
    bpy.ops.wm.open_mainfile(filepath=blend)

    objects = []
    for obj in bpy.data.objects:
        mesh_stats = None
        data = obj.data
        if data is not None and hasattr(data, "polygons"):
            mesh_stats = {"vertices": len(data.vertices), "polygons": len(data.polygons),
                          "materials": len(data.materials) if hasattr(data, "materials") else 0}
        objects.append({"name": obj.name, "type": obj.type,
                        "location": [round(v, 4) for v in obj.location],
                        "dimensions": [round(v, 4) for v in obj.dimensions],
                        "mesh": mesh_stats})

    materials = []
    for mat in bpy.data.materials:
        materials.append({"name": mat.name, "use_nodes": bool(mat.use_nodes)})

    images = [{"name": img.name, "size": [img.size[0], img.size[1]],
               "has_data": bool(img.has_data)} for img in bpy.data.images]

    report = {"ok": True, "blend": blend,
              "blender_version": ".".join(str(v) for v in bpy.app.version),
              "object_count": len(objects), "objects": objects,
              "material_count": len(materials), "materials": materials,
              "image_count": len(images), "images": images,
              "scene_names": [s.name for s in bpy.data.scenes]}
    with open(out, "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
    print("STUDIO_INSPECT_JSON " + json.dumps({"ok": True, "report": out,
                                               "objects": len(objects),
                                               "materials": len(materials)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
