extends Node3D
## Fixture: a camera, a wall, and two identical targets.
##
## The target at the origin sits directly behind the wall. The target at x=3.2
## is in the open. A correct visible-segmentation mask contains only the second;
## a cull_mask-based mask would contain both, which is the exact bug this fixture
## exists to catch.

var camera: Camera3D
var lantern_light: OmniLight3D
var capture_plan := ""
var capture_out := ""
var capture_live := false
var capture_token := ""

const TARGET_A := Vector3(0, 0, 0)
const TARGET_B := Vector3(3.2, 0, 0)


func _ready() -> void:
	_parse_args()
	_build()
	if capture_plan != "":
		# A capture that never finishes must fail loudly, not sit in a window forever.
		var watchdog := get_tree().create_timer(120.0)
		watchdog.timeout.connect(func() -> void:
			printerr("STUDIO_CAPTURE_TIMEOUT")
			get_tree().quit(3))
		var script = load("res://scripts/service.gd")
		if script == null:
			printerr("STUDIO_CAPTURE_FAILED service_missing")
			get_tree().quit(2)
			return
		var service = script.new()
		service.name = "CaptureService"
		add_child(service)
		service.run_plan.call_deferred(capture_plan, capture_out)
	elif capture_live:
		var live_script = load("res://scripts/service.gd")
		if live_script == null:
			printerr("STUDIO_CAPTURE_FAILED service_missing")
			get_tree().quit(2)
			return
		var live_service = live_script.new()
		live_service.name = "CaptureService"
		add_child(live_service)
		live_service.run_live.call_deferred(capture_token, capture_out)


func _parse_args() -> void:
	for arg in OS.get_cmdline_args() + OS.get_cmdline_user_args():
		var text := str(arg)
		if text.begins_with("--capture-plan="):
			capture_plan = text.substr("--capture-plan=".length())
		elif text.begins_with("--capture-out="):
			capture_out = text.substr("--capture-out=".length())
		elif text == "--capture-live":
			capture_live = true
		elif text.begins_with("--capture-token-file="):
			capture_token = text.substr("--capture-token-file=".length())


func _build() -> void:
	var world := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.02, 0.024, 0.03)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.4, 0.5, 0.6)
	env.ambient_light_energy = 0.3
	# Glow is on deliberately: the mask passes must switch it off or bright
	# pixels bleed into their neighbours and dilate the measurement.
	env.glow_enabled = true
	env.glow_intensity = 0.8
	world.environment = env
	add_child(world)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -30, 0)
	sun.light_energy = 1.0
	add_child(sun)

	camera = Camera3D.new()
	camera.position = Vector3(0, 0, 6)
	add_child(camera)
	camera.current = true
	camera.look_at(Vector3(0, 0, 0))

	# In front of the wall on purpose: a light placed inside the target's hull
	# lights nothing, and the illumination measurement would then be a vacuous zero.
	lantern_light = OmniLight3D.new()
	lantern_light.position = Vector3(0, 1.0, 3.2)
	lantern_light.light_energy = 5.0
	lantern_light.omni_range = 6.0
	lantern_light.light_color = Color(1.0, 0.75, 0.4)
	add_child(lantern_light)

	_add_box("TargetBehindWall", TARGET_A, Vector3(0.9, 0.9, 0.9), true, Color(0.9, 0.75, 0.4))
	# Nested inside a player-grouped node on purpose: Emberkeep's lantern rig is a
	# child of the player, and a player-first layer check silently classified it as
	# player geometry, leaving the silhouette pass with nothing to render.
	var holder := Node3D.new()
	holder.name = "PlayerRig"
	holder.add_to_group("capture_player")
	add_child(holder)
	_add_box("TargetInOpen", TARGET_B, Vector3(0.9, 0.9, 0.9), true, Color(0.9, 0.75, 0.4), holder)
	# 4 wide, 4 tall, 0.2 deep at z=2: blocks the origin, leaves x=3.2 clear.
	_add_box("Wall", Vector3(0, 0, 2), Vector3(4.0, 4.0, 0.2), false, Color(0.45, 0.45, 0.5))


func _add_box(label: String, position: Vector3, size: Vector3, is_target: bool, colour: Color, parent: Node3D = null) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var instance := MeshInstance3D.new()
	instance.name = label
	instance.mesh = mesh
	instance.position = position
	var material := StandardMaterial3D.new()
	material.albedo_color = colour
	instance.material_override = material
	if is_target:
		instance.add_to_group("capture_target")
	if parent == null:
		add_child(instance)
	else:
		parent.add_child(instance)
	return instance


func capture_apply_state(state: Dictionary) -> void:
	if state.has("lantern_lit"):
		lantern_light.visible = bool(state["lantern_lit"])


func capture_apply_camera(config: Dictionary) -> void:
	if config.has("position"):
		var position: Array = config["position"]
		if position.size() == 3:
			camera.position = Vector3(position[0], position[1], position[2])
			camera.look_at(Vector3(0, 0, 0))
