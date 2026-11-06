extends SceneTree
## Native scene inspector for the Studio's typed `godot.inspect_scene` operation.
##
## Runs headless without opening the editor:
##   godot --headless --path <project> --script res://tools/inspect_scene.gd
##   -- --scene=res://main.tscn --out=<absolute json path>
##
## Instantiating the scene executes its _ready() path exactly as the game would
## run it, so this is native read-back rather than text parsing. Never writes
## to the project; the JSON report goes to the --out path only.
## Prints exactly one machine-readable line prefixed with STUDIO_INSPECT_JSON.

var _scene_path := "res://main.tscn"
var _out_path := ""


func _init() -> void:
	for arg in OS.get_cmdline_user_args():
		var text := str(arg)
		if text.begins_with("--scene="):
			_scene_path = text.trim_prefix("--scene=")
		elif text.begins_with("--out="):
			_out_path = text.trim_prefix("--out=")
	if _out_path == "":
		print("STUDIO_INSPECT_JSON " + JSON.stringify({"ok": false, "error": "--out is required"}))
		quit(2)
		return
	var packed: PackedScene = load(_scene_path)
	if packed == null:
		print("STUDIO_INSPECT_JSON " + JSON.stringify({"ok": false, "error": "scene_failed_to_load", "scene": _scene_path}))
		quit(3)
		return
	var instance := packed.instantiate()
	root.add_child(instance)
	# One idle frame so _ready() throughout the tree has run before read-back.
	await process_frame
	var report := {"ok": true, "scene": _scene_path,
		"engine": Engine.get_version_info()["string"],
		"node_count": _count(instance), "tree": _describe(instance, 0)}
	var file := FileAccess.open(_out_path, FileAccess.WRITE)
	if file == null:
		print("STUDIO_INSPECT_JSON " + JSON.stringify({"ok": false, "error": "out_not_writable"}))
		quit(4)
		return
	file.store_string(JSON.stringify(report, "  "))
	file.close()
	print("STUDIO_INSPECT_JSON " + JSON.stringify({"ok": true, "report": _out_path, "nodes": report["node_count"]}))
	quit(0)


func _count(node: Node) -> int:
	var total := 1
	for child in node.get_children():
		total += _count(child)
	return total


func _describe(node: Node, depth: int) -> Dictionary:
	var entry := {"name": node.name, "class": node.get_class(), "depth": depth}
	if node is Node3D:
		var t := (node as Node3D).global_transform.origin
		entry["position"] = [snappedf(t.x, 0.001), snappedf(t.y, 0.001), snappedf(t.z, 0.001)]
	if node is MeshInstance3D:
		var mesh := (node as MeshInstance3D).mesh
		entry["has_mesh"] = mesh != null
		if mesh != null:
			entry["surface_count"] = mesh.get_surface_count()
	if node is Light3D:
		entry["light_energy"] = (node as Light3D).light_energy
	var children: Array = []
	if depth < 6:
		for child in node.get_children():
			children.append(_describe(child, depth + 1))
	entry["children"] = children
	entry["child_count_total"] = node.get_child_count()
	return entry
