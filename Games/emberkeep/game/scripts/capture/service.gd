extends Node
## Deterministic, plan-driven capture with occlusion-respecting masks.
##
## Loaded only when a capture flag is present, so an ordinary session pays
## nothing and opens no socket.
##
## Mask construction is deliberately not `cull_mask`-based for the *visible*
## measurement: culled geometry writes no depth, so a lantern-only camera shows
## the lantern through walls. Here the occluders stay in the pass as opaque
## black depth writers and the target is drawn white with depth testing on, so
## occlusion comes from the depth buffer. `cull_mask` is used only for the
## silhouette, which is explicitly labelled as ignoring occlusion.

const GROUP_TARGET := "capture_target"
const GROUP_PLAYER := "capture_player"
const LAYER_WORLD := 1 << 0
const LAYER_TARGET := 1 << 2
const LAYER_PLAYER := 1 << 3
const ALL_LAYERS := 0xFFFFF
const ADAPTER_VERSION := "1.0.0"

var _plan: Dictionary = {}
var _context: Dictionary = {}
var _out_dir := ""
var _saved_layers: Dictionary = {}
var _saved_overrides: Dictionary = {}
var _saved_glow: bool = true
var _world_env: WorldEnvironment = null
# Masks must match the frame's *pixels*, not the stretched 2D viewport size.
var _mask_size := Vector2i.ZERO

# Live session state. No session exists until a connection authenticates.
var _live := false
var _server: TCPServer = null
var _connection: StreamPeerTCP = null
var _buffer := ""
var _authed := false
var _token := ""
var _last_activity_ms := 0
var _capture_times_ms: Array = []
var _session_file := ""
var _capture_in_flight := false

const MAX_LINE_BYTES := 65536
const MAX_CAPTURES_PER_MINUTE := 20
const IDLE_TIMEOUT_MS := 300000
const MAX_AUTH_FAILURES := 3


func _ready() -> void:
	# The tree is paused while capturing so a frame cannot change underneath us.
	process_mode = Node.PROCESS_MODE_ALWAYS


func run_plan(plan_path: String, out_dir: String) -> void:
	_out_dir = out_dir
	_plan = _read_json(plan_path)
	if _plan.is_empty():
		printerr("STUDIO_CAPTURE_FAILED plan_unreadable")
		get_tree().quit(2)
		return
	_context = _read_json(out_dir.path_join("capture-context.json"))

	var report := {"ok": true, "captures": [], "failures": []}
	_assign_layers()
	_world_env = _find_world_environment()
	if _world_env != null and _world_env.environment != null:
		_saved_glow = _world_env.environment.glow_enabled

	var entries: Array = _plan.get("entries", [])
	if entries.is_empty():
		report["ok"] = false
		report["failures"].append("plan has no entries")

	for entry in entries:
		var outcome: Dictionary = await _capture_entry(entry)
		report["captures"].append(outcome)
		if not bool(outcome.get("ok", false)):
			report["ok"] = false
			report["failures"].append(outcome.get("error", "capture_failed"))

	_restore_layers()
	if _world_env != null and _world_env.environment != null:
		_world_env.environment.glow_enabled = _saved_glow
	get_tree().paused = false
	print("STUDIO_CAPTURE_JSON " + JSON.stringify(report))
	get_tree().quit(0 if bool(report["ok"]) else 1)


# --------------------------------------------------------------------------- capture

func _capture_entry(entry: Dictionary, capture_mode: String = "deterministic") -> Dictionary:
	var parent := get_parent()
	get_tree().paused = false
	_apply_state(entry.get("state", {}))
	_apply_camera(entry.get("camera", {}))

	var target_tick := int(entry.get("physics_tick", 0))
	var guard := 0
	while Engine.get_physics_frames() < target_tick and guard < 100000:
		await get_tree().physics_frame
		guard += 1
	if guard >= 100000:
		return {"ok": false, "error": "physics_tick_never_reached", "target": target_tick}

	# Freeze the simulation, then let two frames present so temporal effects settle.
	get_tree().paused = true
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw

	var roles: Array = entry.get("roles", _plan.get("default_roles", ["frame"]))
	var capture_id := _uuid4()
	var artifacts: Array = []
	var white_pixels: Dictionary = {}

	if roles.has("frame"):
		var frame := await _render_viewport_image()
		if frame == null:
			return {"ok": false, "error": "frame_capture_returned_null"}
		_mask_size = frame.get_size()
		artifacts.append(_write_artifact("frame", "render", frame, capture_id))
	elif _mask_size == Vector2i.ZERO:
		var probe := await _render_viewport_image()
		if probe != null:
			_mask_size = probe.get_size()

	_set_glow(false)
	if roles.has("mask_world_visible"):
		var world_mask := await _mask_world()
		white_pixels["mask_world_visible"] = _white_count(world_mask)
		artifacts.append(_write_artifact("mask_world_visible", "visible_segmentation", world_mask, capture_id))
	if roles.has("mask_world_occupancy"):
		var occupancy := await _mask_occupancy()
		white_pixels["mask_world_occupancy"] = _white_count(occupancy)
		artifacts.append(_write_artifact("mask_world_occupancy", "scene_coverage", occupancy, capture_id))
	if roles.has("mask_player_visible"):
		var player_mask := await _mask(LAYER_PLAYER)
		white_pixels["mask_player_visible"] = _white_count(player_mask)
		artifacts.append(_write_artifact("mask_player_visible", "visible_segmentation", player_mask, capture_id))
	if roles.has("mask_lantern_visible"):
		var lantern_mask := await _mask(LAYER_TARGET)
		white_pixels["mask_lantern_visible"] = _white_count(lantern_mask)
		artifacts.append(_write_artifact("mask_lantern_visible", "visible_segmentation", lantern_mask, capture_id))
	if roles.has("mask_lantern_silhouette"):
		var silhouette := await _silhouette()
		white_pixels["mask_lantern_silhouette"] = _white_count(silhouette)
		artifacts.append(_write_artifact("mask_lantern_silhouette", "unoccluded_silhouette", silhouette, capture_id))
	if roles.has("mask_lantern_illumination"):
		var illumination := await _illumination()
		white_pixels["mask_lantern_illumination"] = _white_count(illumination)
		artifacts.append(_write_artifact("mask_lantern_illumination", "illumination_delta", illumination, capture_id))
	_set_glow(true)

	if artifacts.is_empty():
		return {"ok": false, "error": "no_artifacts_written", "roles": roles}

	var bundle_path := _write_bundle(capture_id, entry, roles, artifacts, capture_mode)
	return {
		"ok": FileAccess.file_exists(bundle_path),
		"capture_id": capture_id,
		"bundle": bundle_path,
		"artifacts": artifacts.size(),
		"physics_tick": Engine.get_physics_frames(),
		"render_frame": Engine.get_frames_drawn(),
		"white_pixels": white_pixels,
		"layer_counts": _layer_counts(),
	}


func _render_viewport_image() -> Image:
	await RenderingServer.frame_post_draw
	var texture := get_viewport().get_texture()
	if texture == null:
		return null
	return texture.get_image()


# --------------------------------------------------------------------------- masks

## Visible segmentation: occluders are kept as opaque black depth writers and the
## target layer is drawn white, so the depth buffer — not culling — removes the
## parts of the target that are behind geometry.
func _mask(target_layer: int) -> Image:
	return await _render_mask(target_layer, true, true, false)


func _silhouette() -> Image:
	return await _render_mask(LAYER_TARGET, true, false, false)


func _mask_world() -> Image:
	return await _render_mask(LAYER_WORLD | LAYER_PLAYER, false, false, true)


## Coverage: which pixels have surfaces in them at all.
##
## The visible-segmentation pass cannot answer this — the environment sky is drawn
## into that viewport, so it reports coverage for pixels where nothing exists. Here
## the sky is replaced by a background colour the palette cannot produce
## (cyan, red channel 0) and every surface is forced white, so the red channel
## separates "a surface is here" from "the camera is looking at nothing"
## regardless of how dark the surface happens to be lit.
func _mask_occupancy() -> Image:
	var environment: Environment = null
	var saved_mode := Environment.BG_SKY
	var saved_color := Color(0, 0, 0)
	if _world_env != null and _world_env.environment != null:
		environment = _world_env.environment
		saved_mode = environment.background_mode
		saved_color = environment.background_color
		environment.background_mode = Environment.BG_COLOR
		environment.background_color = Color(0.0, 1.0, 1.0, 1.0)
	var image := await _render_mask(ALL_LAYERS, true, false, true)
	if environment != null:
		environment.background_mode = saved_mode
		environment.background_color = saved_color
	return image


func _illumination() -> Image:
	var lit := await _render_viewport_image()
	_toggle_light(false)
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var unlit := await _render_viewport_image()
	_toggle_light(true)
	if lit == null or unlit == null:
		return _blank_image()
	return _difference(lit, unlit)


func _render_mask(target_layer: int, white_targets: bool, black_occluders: bool, white_others: bool) -> Image:
	var source := _camera()
	var size := Vector2i(frame_size().x, frame_size().y)

	var viewport := SubViewport.new()
	viewport.size = size
	viewport.transparent_bg = true
	viewport.msaa_3d = Viewport.MSAA_DISABLED   # MSAA blends ID colours at silhouette edges
	viewport.own_world_3d = false                # share the scene so depth is comparable
	viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
	add_child(viewport)

	var camera := Camera3D.new()
	camera.cull_mask = target_layer if not black_occluders else ALL_LAYERS
	if source != null:
		camera.projection = source.projection
		camera.fov = source.fov
		camera.near = source.near
		camera.far = source.far
		camera.size = source.size
		camera.global_transform = source.global_transform
	viewport.add_child(camera)
	camera.current = true

	var white := _flat_material(Color(1, 1, 1, 1))
	var black := _flat_material(Color(0, 0, 0, 1))
	for instance in _visual_instances():
		var target := _is_target(instance)
		if target and white_targets:
			_saved_overrides[instance] = instance.material_override
			instance.material_override = white
		elif white_others and not target:
			_saved_overrides[instance] = instance.material_override
			instance.material_override = white
		elif black_occluders and not target:
			_saved_overrides[instance] = instance.material_override
			instance.material_override = black

	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var raw: Image = viewport.get_texture().get_image() if viewport.get_texture() != null else null

	_restore_overrides()
	viewport.queue_free()
	if raw == null:
		return _blank_image()
	return _binarise(raw)


func _binarise(raw: Image) -> Image:
	var width := raw.get_width()
	var height := raw.get_height()
	var source := raw.get_data()
	var out := PackedByteArray()
	out.resize(width * height)
	for index in range(width * height):
		# Threshold on the red channel: white target, black occluder, transparent bg.
		out[index] = 255 if source[index * 4] > 127 else 0
	return Image.create_from_data(width, height, false, Image.FORMAT_L8, out)


func _difference(before: Image, after: Image) -> Image:
	var a: Image = before.duplicate()
	var b: Image = after.duplicate()
	a.convert(Image.FORMAT_RGB8)
	b.convert(Image.FORMAT_RGB8)
	var width := a.get_width()
	var height := a.get_height()
	if width != b.get_width() or height != b.get_height():
		return _blank_image()
	var left := a.get_data()
	var right := b.get_data()
	var out := PackedByteArray()
	out.resize(width * height)
	for index in range(width * height):
		var delta := 0
		for channel in range(3):
			delta = max(delta, abs(int(left[index * 3 + channel]) - int(right[index * 3 + channel])))
		out[index] = 255 if delta > 8 else 0
	return Image.create_from_data(width, height, false, Image.FORMAT_L8, out)


func _white_count(image: Image) -> int:
	var data := image.get_data()
	var total := 0
	for value in data:
		if value == 255:
			total += 1
	return total


func _layer_counts() -> Dictionary:
	var counts := {"world": 0, "target": 0, "player": 0}
	for instance in _visual_instances():
		match instance.layers:
			LAYER_TARGET:
				counts["target"] += 1
			LAYER_PLAYER:
				counts["player"] += 1
			_:
				counts["world"] += 1
	return counts


func _blank_image() -> Image:
	var size := frame_size()
	var out := PackedByteArray()
	out.resize(size.x * size.y)
	return Image.create_from_data(size.x, size.y, false, Image.FORMAT_L8, out)


# --------------------------------------------------------------------------- scene helpers

func frame_size() -> Vector2i:
	if _mask_size.x > 0 and _mask_size.y > 0:
		return _mask_size
	return get_viewport().get_visible_rect().size


func _visual_instances() -> Array:
	var found: Array = []
	for node in get_tree().root.find_children("*", "VisualInstance3D", true, false):
		var instance := node as GeometryInstance3D
		if instance != null:
			found.append(instance)
	return found


func _assign_layers() -> void:
	for instance in _visual_instances():
		_saved_layers[instance] = instance.layers
		# Target is checked first: the lantern rig is a child of the player, so a
		# player-first check would classify every lantern mesh as player geometry
		# and the silhouette pass would then render nothing at all.
		if _in_group(instance, GROUP_TARGET):
			instance.layers = LAYER_TARGET
		elif _in_group(instance, GROUP_PLAYER):
			instance.layers = LAYER_PLAYER
		else:
			instance.layers = LAYER_WORLD


func _restore_layers() -> void:
	for instance in _saved_layers:
		if is_instance_valid(instance):
			instance.layers = _saved_layers[instance]
	_saved_layers.clear()


func _is_target(instance: Node) -> bool:
	return _in_group(instance, GROUP_TARGET)


func _in_group(node: Node, group: String) -> bool:
	var current := node
	while current != null:
		if current.is_in_group(group):
			return true
		current = current.get_parent()
	return false


func _restore_overrides() -> void:
	for instance in _saved_overrides:
		if is_instance_valid(instance):
			instance.material_override = _saved_overrides[instance]
	_saved_overrides.clear()


func _flat_material(colour: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = colour
	return material


func _camera() -> Camera3D:
	var parent := get_parent()
	if parent != null and parent.get("camera") != null:
		return parent.get("camera")
	return get_viewport().get_camera_3d()


func _find_world_environment() -> WorldEnvironment:
	for node in get_tree().root.find_children("*", "WorldEnvironment", true, false):
		return node as WorldEnvironment
	return null


func _set_glow(enabled: bool) -> void:
	# Glow bleeds bright mask pixels into their neighbours, which would dilate a
	# measurement. The environment is restored after the mask passes.
	if _world_env != null and _world_env.environment != null:
		_world_env.environment.glow_enabled = enabled


func _toggle_light(enabled: bool) -> void:
	var parent := get_parent()
	if parent == null:
		return
	var light = parent.get("lantern_light")
	if light != null:
		light.visible = enabled


func _apply_state(state: Dictionary) -> void:
	var parent := get_parent()
	if parent == null or state.is_empty():
		return
	if parent.has_method("capture_apply_state"):
		parent.capture_apply_state(state)
		return
	var light = parent.get("lantern_light")
	if light != null and state.has("lantern_lit"):
		light.visible = bool(state["lantern_lit"])


func _apply_camera(config: Dictionary) -> void:
	var parent := get_parent()
	if parent != null and parent.has_method("capture_apply_camera"):
		parent.capture_apply_camera(config)
		return
	var camera := _camera()
	if camera == null:
		return
	if config.has("position"):
		var position: Array = config["position"]
		if position.size() == 3:
			camera.global_position = Vector3(position[0], position[1], position[2])
	if parent != null and parent.get("player") != null:
		camera.look_at(parent.get("player").global_position + Vector3(0, 1.1, 0))


# --------------------------------------------------------------------------- bundle

func _write_artifact(role: String, semantics: String, image: Image, capture_id: String) -> Dictionary:
	var directory := _out_dir.path_join(capture_id)
	DirAccess.make_dir_recursive_absolute(directory)
	var path := directory.path_join(role + ".png")
	var error := image.save_png(path)
	if error != OK:
		push_error("mask/frame write failed for %s: %d" % [role, error])
	var size := image.get_size()
	return {
		"role": role,
		"semantics": semantics,
		"path": role + ".png",
		"sha256": FileAccess.get_sha256(path),
		"width": size.x,
		"height": size.y,
		"mime": "image/png",
		"bytes": FileAccess.get_file_as_bytes(path).size(),
		"derived_from": null,
	}


func _write_bundle(capture_id: String, entry: Dictionary, roles: Array, artifacts: Array, capture_mode: String = "deterministic") -> String:
	var frame := _find_artifact(artifacts, "frame")
	var resolution: Array = [0, 0]
	if not frame.is_empty():
		resolution = [frame["width"], frame["height"]]
	var requested: Array = resolution
	var requested_context = _context.get("requested_resolution")
	if requested_context is Array and requested_context.size() == 2:
		requested = requested_context
	var now := Time.get_datetime_string_from_system(true) + "Z"
	var git: Dictionary = _context.get("git", {"commit": "", "dirty": false})
	var document := {
		"schema_version": "2.0",
		"capture_id": capture_id,
		"mode": capture_mode,
		# Authority is not the game's to grant: repeatability qualification happens
		# in the Studio. The game asserts no more than "supervisory, not yet run".
		"evidence_grade": "supervisory",
		"application": {
			"name": str(_context.get("name", "emberkeep")),
			"adapter_version": ADAPTER_VERSION,
			"engine_version": str(Engine.get_version_info().get("string", "unknown")),
			"project_path": str(_context.get("project_path", "")),
			"rendering_method": str(ProjectSettings.get_setting("rendering/renderer/rendering_method", "forward_plus")),
			"requested_resolution": requested,
			"resolution": resolution,
			"msaa_3d": int(ProjectSettings.get_setting("rendering/anti_aliasing/quality/msaa_3d", 0)),
			"screen_space_aa": int(ProjectSettings.get_setting("rendering/anti_aliasing/quality/screen_space_aa", 0)),
			"stretch_mode": str(ProjectSettings.get_setting("display/window/stretch/mode", "disabled")),
		},
		"request": {
			"roles": roles,
			"physics_tick": Engine.get_physics_frames(),
			"render_frame": Engine.get_frames_drawn(),
			"camera": entry.get("camera", {}),
			"state": entry.get("state", {}),
			"seed": int(_context.get("seed", 0)),
			"rng_instance_seeds": _context.get("rng_instance_seeds", {}),
		},
		"qualification": {
			"repeatability": {
				"status": "not_run",
				"runs": 0,
				"state_digest": null,
				"render_contract": null,
				"tolerance": null,
				"measured_max_delta": null,
			}
		},
		"artifacts": artifacts,
		"provenance": {
			"contract_sha256": str(_context.get("contract_sha256", "0".repeat(64))),
			"plan_sha256": str(_context.get("plan_sha256", "0".repeat(64))),
			"git": {
				"commit": str(git.get("commit", "")),
				"dirty": bool(git.get("dirty", false)),
				"tree_sha256": git.get("tree_sha256", null),
				"untracked_or_patch_sha256": git.get("untracked_or_patch_sha256", null),
			},
			"engine": {
				"version": str(Engine.get_version_info().get("string", "unknown")),
				"executable_sha256": _context.get("engine_executable_sha256", null),
			},
			"gpu": _context.get("gpu", null),
			"settings": {
				"fixed_fps": int(Engine.get_physics_ticks_per_second()),
				"physics_ticks_per_second": int(Engine.get_physics_ticks_per_second()),
				"warmup_frames": int(_plan.get("warmup_frames", 0)),
				"paused_for_capture": true,
				"physics_interpolation_disabled": true,
			},
			"host": OS.get_name().to_lower(),
			"started_at": str(_context.get("started_at", now)),
			"finished_at": now,
			"duration_ms": max(1, Time.get_ticks_msec() - int(_context.get("started_ms", Time.get_ticks_msec()))),
		},
		"verification": {"status": "unverified", "checks": []},
	}

	if capture_mode == "live":
		# Live observation has no repeatability qualification; claiming one would be
		# a category error, not a shortcut.
		document.erase("qualification")

	var path := _out_dir.path_join(capture_id).path_join("bundle.json")
	# Bundle last, atomically: a bundle must never describe half-written evidence.
	var temporary := path + ".tmp"
	var file := FileAccess.open(temporary, FileAccess.WRITE)
	if file == null:
		push_error("cannot write bundle: %s" % temporary)
		return ""
	file.store_string(JSON.stringify(document, "  "))
	file.close()
	DirAccess.rename_absolute(temporary, path)
	return path


func _find_artifact(artifacts: Array, role: String) -> Dictionary:
	for artifact in artifacts:
		if artifact["role"] == role:
			return artifact
	return {}


# --------------------------------------------------------------------------- live session

func run_live(token_path: String, out_dir: String) -> void:
	_out_dir = out_dir
	_context = _read_json(out_dir.path_join("capture-context.json"))
	_token = FileAccess.get_file_as_string(token_path).strip_edges()
	if _token.length() < 16:
		printerr("STUDIO_CAPTURE_FAILED token_missing")
		get_tree().quit(2)
		return
	_server = TCPServer.new()
	var error := _server.listen(0, "127.0.0.1")  # loopback only, ephemeral port
	if error != OK:
		printerr("STUDIO_CAPTURE_FAILED listen_%d" % error)
		get_tree().quit(2)
		return
	_world_env = _find_world_environment()
	if _world_env != null and _world_env.environment != null:
		_saved_glow = _world_env.environment.glow_enabled
	_assign_layers()
	_session_file = _out_dir.path_join("session.json")
	DirAccess.make_dir_recursive_absolute(_out_dir)
	var session := {
		"port": _server.get_local_port(),
		"pid": OS.get_process_id(),
		"started_at": Time.get_datetime_string_from_system(true) + "Z",
		"project": str(_context.get("project_path", ProjectSettings.get_setting("application/config/name", ""))),
	}
	var file := FileAccess.open(_session_file, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(session))
		file.close()
	_last_activity_ms = Time.get_ticks_msec()
	_live = true
	set_process(true)
	print("STUDIO_CAPTURE_LIVE_READY " + JSON.stringify(session))


func _process(_delta: float) -> void:
	if not _live:
		return
	_poll_accept()
	_poll_connection()
	if Time.get_ticks_msec() - _last_activity_ms > IDLE_TIMEOUT_MS:
		_stop_live("idle_timeout")


func _poll_accept() -> void:
	if _server == null:
		return
	# Always drain the accept queue. Returning early while a session is held left
	# extra connections waiting in the OS queue instead of being refused, so a
	# client saw a hang rather than a closed socket.
	while _server.is_connection_available():
		var candidate := _server.take_connection()
		if _connection != null:
			# poll() updates the status from the socket; a peer whose client closed
			# otherwise stays CONNECTED and holds the only session slot forever.
			_connection.poll()
		var held_is_live := _connection != null and _connection.get_status() == StreamPeerTCP.STATUS_CONNECTED
		if not held_is_live:
			# A peer that is already gone must not block the next connection.
			if _connection != null:
				_close_peer(_connection)
			_connection = candidate
			_authed = false
			_buffer = ""
			_last_activity_ms = Time.get_ticks_msec()
			_setup_connection()
		else:
			# One session at a time: extra connections are refused, never queued.
			_close_peer(candidate)


func _setup_connection() -> void:
	if _connection == null:
		return
	_connection.set_no_delay(true)


func _poll_connection() -> void:
	if _connection == null:
		return
	_connection.poll()
	var status := _connection.get_status()
	if status != StreamPeerTCP.STATUS_CONNECTED:
		_drop_connection()
		return
	var available := _connection.get_available_bytes()
	if available > 0:
		var chunk := _connection.get_partial_data(available)
		if chunk[0] != OK:
			_drop_connection()
			return
		_buffer += (chunk[1] as PackedByteArray).get_string_from_utf8()
		_last_activity_ms = Time.get_ticks_msec()
	if _buffer.length() > MAX_LINE_BYTES and _buffer.find("\n") == -1:
		_deny("line_too_long")
		_drop_connection()
		return
	while _buffer.find("\n") != -1:
		var index := _buffer.find("\n")
		var line := _buffer.substr(0, index).strip_edges()
		_buffer = _buffer.substr(index + 1)
		if line.length() == 0:
			continue
		if line.length() > MAX_LINE_BYTES:
			_deny("line_too_long")
			_drop_connection()
			return
		_handle_line(line)


func _handle_line(line: String) -> void:
	var parsed = JSON.parse_string(line)
	if not (parsed is Dictionary):
		_send({"ok": false, "error": "invalid_json"})
		return
	var message: Dictionary = parsed
	var op := str(message.get("op", ""))
	if not _authed:
		if op != "hello":
			_deny("auth_required")
			_drop_connection()
			return
		if _constant_time_equal(str(message.get("token", "")), _token):
			_authed = true
			_send({"ok": true, "mode": "live", "protocol": 1})
		else:
			_deny("bad_token")
			_drop_connection()
		return
	match op:
		"state":
			_send({
				"ok": true,
				"physics_tick": Engine.get_physics_frames(),
				"render_frame": Engine.get_frames_drawn(),
				"fps": Engine.get_frames_per_second(),
				"mode": "live",
			})
		"capture":
			if not _allow_capture():
				_send({"ok": false, "error": "rate_limited"})
				return
			if _capture_in_flight:
				_send({"ok": false, "error": "capture_in_flight"})
				return
			var roles: Array = message.get("roles", ["frame"])
			_live_capture(roles)
		"quit":
			_send({"ok": true, "closing": true})
			_stop_live("requested")
		_:
			# No arbitrary evaluation, no shell, no client-supplied paths.
			_deny("unknown_op")
			_send({"ok": false, "error": "unknown_op"})


func _live_capture(roles: Array) -> void:
	_capture_in_flight = true
	var entry := {
		"physics_tick": Engine.get_physics_frames() + 2,
		"roles": roles,
		"camera": {},
		"state": {},
	}
	var outcome: Dictionary = await _capture_entry(entry, "live")
	get_tree().paused = false
	if _world_env != null and _world_env.environment != null:
		_world_env.environment.glow_enabled = _saved_glow
	_capture_in_flight = false
	_send({
		"ok": bool(outcome.get("ok", false)),
		"mode": "live",
		"evidence_grade": "supervisory",
		"capture_id": outcome.get("capture_id", ""),
		"bundle": outcome.get("bundle", ""),
		"error": outcome.get("error", ""),
	})


func _allow_capture() -> bool:
	var now := Time.get_ticks_msec()
	var kept: Array = []
	for stamp in _capture_times_ms:
		if now - int(stamp) < 60000:
			kept.append(stamp)
	_capture_times_ms = kept
	if _capture_times_ms.size() >= MAX_CAPTURES_PER_MINUTE:
		_deny("rate_limited")
		return false
	_capture_times_ms.append(now)
	return true


func _constant_time_equal(left: String, right: String) -> bool:
	if left.length() != right.length() or left.length() == 0:
		return false
	var difference := 0
	for index in range(left.length()):
		difference |= left.unicode_at(index) ^ right.unicode_at(index)
	return difference == 0


func _send(payload: Dictionary) -> void:
	if _connection == null:
		return
	_connection.put_data((JSON.stringify(payload) + "\n").to_utf8_buffer())


func _deny(reason: String) -> void:
	var path := _out_dir.path_join("live-denials.jsonl")
	DirAccess.make_dir_recursive_absolute(_out_dir)
	var file := FileAccess.open(path, FileAccess.READ_WRITE) if FileAccess.file_exists(path) else FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.seek_end()
		file.store_line(JSON.stringify({"at": Time.get_datetime_string_from_system(true) + "Z", "reason": reason}))
		file.close()


func _drop_connection() -> void:
	if _connection != null:
		_close_peer(_connection)
	_connection = null
	_authed = false
	_buffer = ""


func _close_peer(peer: StreamPeerTCP) -> void:
	if peer == null:
		return
	# Closing with unread bytes makes the OS send RST, which a client sees as a
	# reset rather than a clean refusal. Drain first so the shutdown is orderly.
	var available := peer.get_available_bytes()
	if available > 0:
		peer.get_partial_data(available)
	peer.disconnect_from_host()


func _stop_live(reason: String) -> void:
	_live = false
	set_process(false)
	_drop_connection()
	if _server != null:
		_server.stop()
		_server = null
	if _session_file != "" and FileAccess.file_exists(_session_file):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(_session_file))
	print("STUDIO_CAPTURE_LIVE_STOP " + reason)
	get_tree().quit(0)


func _read_json(path: String) -> Dictionary:
	if path == "" or not FileAccess.file_exists(path):
		return {}
	var text := FileAccess.get_file_as_string(path)
	var parsed = JSON.parse_string(text)
	return parsed if parsed is Dictionary else {}


func _uuid4() -> String:
	var bytes := Crypto.new().generate_random_bytes(16)
	var hex := ""
	for index in range(16):
		hex += "%02x" % bytes[index]
	return hex.substr(0, 8) + "-" + hex.substr(8, 4) + "-" + hex.substr(12, 4) + "-" + hex.substr(16, 4) + "-" + hex.substr(20, 12)
