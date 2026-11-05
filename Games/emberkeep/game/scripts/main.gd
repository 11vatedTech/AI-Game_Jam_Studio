extends Node3D
## EMBERKEEP — playable vertical slice.
##
## The world is assembled at runtime from manufactured assets so the production pipeline
## (image -> mesh -> Blender -> engine) stays the single source of truth:
##   res://assets/shrine_terrace.glb   authored architecture kit (Blender)
##   res://assets/lantern_hero.glb     authored hero prop (Blender)
##   res://assets/pylon.glb            image-to-mesh reconstruction (ComfyUI Hunyuan3D -> Blender)
##   res://assets/backdrop.png         generated matte painting used as a distant skyline
##
## Runtime flags (used by the automated smoke test):
##   --smoke --shot-dir=<absolute path>

const INK := Color(0.043, 0.063, 0.086)
const SLATE := Color(0.11, 0.17, 0.20)
const MIST := Color(0.245, 0.355, 0.39)
const BONE := Color(0.847, 0.804, 0.729)
const LANTERN := Color(1.0, 0.757, 0.408)
const EMBER := Color(1.0, 0.478, 0.184)

const PYLON_HEIGHT := 3.6
const WARMTH_DRAIN := 1.55
const WARMTH_MAX := 100.0
const IGNITE_SECONDS := 1.2
const IGNITE_RANGE := 2.6
const MOTE_RESTORE := 16.0

var warmth := WARMTH_MAX
var state := "PLAYING"
var lit := 0
var elapsed := 0.0

var player: CharacterBody3D
var cam_pivot: Node3D
var camera: Camera3D
var lantern_light: OmniLight3D
var lantern_rig: Node3D
var lantern_beam: SpotLight3D
var hud: Control
var hud_layer: CanvasLayer
var pylons: Array = []
var motes: Array = []
var is_smoking := false
var shot_dir := ""
var ignoring_input := false
var message := ""
var message_timer := 0.0
var fx_player: AudioStreamPlayer
var ambience_player: AudioStreamPlayer
var ignite_sfx: AudioStream
var chime_sfx: AudioStream
var win_sfx: AudioStream
var world_env: Environment

func _ready() -> void:
	_parse_args()
	_build_environment()
	_build_deck_and_water()
	_build_player()
	_build_pylons()
	_build_motes()
	_build_ambience()
	_build_hud()
	if is_smoking:
		_run_smoke.call_deferred()

# --------------------------------------------------------------------------- arguments

func _parse_args() -> void:
	var argv: Array = OS.get_cmdline_args() + OS.get_cmdline_user_args()
	for arg in argv:
		var text := str(arg)
		if text == "--smoke":
			is_smoking = true
		elif text.begins_with("--shot-dir="):
			shot_dir = text.substr("--shot-dir=".length())
	if is_smoking:
		# Watchdog: a hung smoke run must fail loudly instead of hanging CI.
		var watchdog := get_tree().create_timer(75.0)
		watchdog.timeout.connect(func() -> void:
			printerr("STUDIO_SMOKE_TIMEOUT")
			get_tree().quit(2))

# --------------------------------------------------------------------------- world

func _build_environment() -> void:
	var world := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = INK
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.30, 0.45, 0.55)
	env.ambient_light_energy = 0.26
	env.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.tonemap_white = 4.0

	env.glow_enabled = true
	env.glow_intensity = 0.55
	env.glow_strength = 1.05
	env.glow_bloom = 0.06
	env.glow_hdr_threshold = 1.05
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE

	env.fog_enabled = true
	env.fog_light_color = MIST
	env.fog_light_energy = 0.55
	env.fog_density = 0.013
	env.fog_light_energy = 0.85
	env.fog_sky_affect = 0.75
	env.fog_aerial_perspective = 0.4

	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.018
	env.volumetric_fog_albedo = MIST
	env.volumetric_fog_emission = Color(0.02, 0.035, 0.045)
	env.volumetric_fog_length = 90.0

	env.ssao_enabled = true
	env.ssao_radius = 1.6
	env.ssao_intensity = 1.4

	world.environment = env
	world_env = env
	add_child(world)

	# Distant matte painting: a wide, unshaded backdrop behind the terrace.
	var backdrop_mesh := QuadMesh.new()
	backdrop_mesh.size = Vector2(120, 50)
	var backdrop := MeshInstance3D.new()
	backdrop.mesh = backdrop_mesh
	backdrop.position = Vector3(0, 13, -44)
	var backdrop_mat := StandardMaterial3D.new()
	backdrop_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	backdrop_mat.albedo_color = Color(1.0, 1.0, 1.0)
	if ResourceLoader.exists("res://assets/backdrop.png"):
		backdrop_mat.albedo_texture = load("res://assets/backdrop.png")
	backdrop_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	backdrop_mat.albedo_color.a = 0.85
	backdrop.material_override = backdrop_mat
	backdrop.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(backdrop)

	# Cold key from the horizon: the only non-warm light in the world.
	var moon := DirectionalLight3D.new()
	moon.light_color = Color(0.55, 0.75, 0.85)
	moon.light_energy = 0.34
	moon.rotation_degrees = Vector3(-38, 152, 0)
	moon.shadow_enabled = true
	moon.directional_shadow_max_distance = 60.0
	add_child(moon)

func _build_deck_and_water() -> void:
	if ResourceLoader.exists("res://assets/shrine_terrace.glb"):
		var kit: PackedScene = load("res://assets/shrine_terrace.glb")
		var inst := kit.instantiate()
		inst.name = "ShrineTerrace"
		# The kit is authored facing +Z; the camera rig looks along -Z, so the terrace turns to face
		# the player's start and the distant skyline sits behind the arches.
		inst.rotation_degrees = Vector3(0, 180, 0)
		_restyle(inst)
		add_child(inst)
		for child in inst.get_children():
			if child is MeshInstance3D:
				child.create_trimesh_collision()
	else:
		push_warning("shrine_terrace.glb missing; the world will be empty.")

	# Standing water plane surrounding the terrace.
	var water := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(260, 260)
	plane.subdivide_width = 40
	plane.subdivide_depth = 40
	water.mesh = plane
	water.position = Vector3(0, -1.25, 0)
	var water_mat := ShaderMaterial.new()
	water_mat.shader = load("res://shaders/water.gdshader")
	water.material_override = water_mat
	water.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(water)

# --------------------------------------------------------------------------- materials

func _restyle(root: Node) -> void:
	for child in root.get_children():
		if child is MeshInstance3D:
			var mesh_instance := child as MeshInstance3D
			var mesh := mesh_instance.mesh
			if mesh == null:
				continue
			for surface in mesh.get_surface_count():
				var source := mesh.surface_get_material(surface)
				var key := ""
				if source != null:
					key = source.resource_name.to_upper()
				mesh_instance.set_surface_override_material(surface, _material_for(key))
		_restyle(child)

func _material_for(key: String) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.resource_name = key
	mat.specular_mode = BaseMaterial3D.SPECULAR_SCHLICK_GGX
	if key.contains("GLASS"):
		mat.albedo_color = Color(0.95, 0.79, 0.58, 0.30)
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.roughness = 0.05
		mat.metallic = 0.0
		mat.emission_enabled = true
		mat.emission = LANTERN
		mat.emission_energy_multiplier = 0.25
		mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	elif key.contains("EMBER") or key.contains("CORE"):
		mat.albedo_color = LANTERN
		mat.emission_enabled = true
		mat.emission = LANTERN
		mat.emission_energy_multiplier = 9.0
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	elif key.contains("BRASS"):
		mat.albedo_color = Color(0.36, 0.26, 0.14)
		mat.metallic = 1.0
		mat.roughness = 0.42
	elif key.contains("DEEP"):
		mat.albedo_color = Color(0.055, 0.085, 0.10)
		mat.roughness = 0.42
	elif key.contains("WORN"):
		mat.albedo_color = Color(0.215, 0.300, 0.325)
		mat.roughness = 0.30
	else:
		mat.albedo_color = Color(0.150, 0.215, 0.245)
		mat.roughness = 0.34
	return mat

# --------------------------------------------------------------------------- player

func _build_player() -> void:
	player = CharacterBody3D.new()
	player.name = "Lamplighter"
	player.position = Vector3(0, 1.0, 9.0)
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.height = 1.7
	capsule.radius = 0.30
	shape.shape = capsule
	shape.position = Vector3(0, 0.85, 0)
	player.add_child(shape)
	add_child(player)

	# Lantern rig: damped pendulum sway is applied in _process.
	lantern_rig = Node3D.new()
	lantern_rig.position = Vector3(0.40, 0.82, -0.18)
	player.add_child(lantern_rig)

	# The lamplighter body: a silhouette, not a character study. Faces stay hidden by the cowl.
	if ResourceLoader.exists("res://assets/lamplighter.glb"):
		var body_scene: PackedScene = load("res://assets/lamplighter.glb")
		var body := body_scene.instantiate()
		body.name = "LamplighterBody"
		_restyle(body)
		body.rotation_degrees = Vector3(0, 0, 0)
		player.add_child(body)

	var lantern: Node3D = null
	if ResourceLoader.exists("res://assets/lantern_hero.glb"):
		var scene: PackedScene = load("res://assets/lantern_hero.glb")
		lantern = scene.instantiate()
		_restyle(lantern)
		lantern_rig.add_child(lantern)

	lantern_light = OmniLight3D.new()
	lantern_light.light_color = LANTERN
	lantern_light.light_energy = 2.4
	lantern_light.omni_range = 8.0
	lantern_light.omni_attenuation = 1.75
	lantern_light.shadow_enabled = true
	lantern_light.position = Vector3(0.40, 1.02, -0.18)
	player.add_child(lantern_light)

	# A soft forward beam so the lantern actually lights the path ahead.
	lantern_beam = SpotLight3D.new()
	lantern_beam.light_color = LANTERN
	lantern_beam.light_energy = 1.1
	lantern_beam.spot_range = 14.0
	lantern_beam.spot_angle = 38.0
	lantern_beam.spot_angle_attenuation = 1.4
	lantern_beam.rotation_degrees = Vector3(-16, 0, 0)
	lantern_beam.position = Vector3(0.32, 1.0, -0.30)
	player.add_child(lantern_beam)

	cam_pivot = Node3D.new()
	cam_pivot.position = player.position + Vector3(0, 1.1, 0)
	add_child(cam_pivot)

	camera = Camera3D.new()
	camera.fov = 38.0
	camera.position = Vector3(0, 4.20, 10.60)
	camera.rotation_degrees = Vector3(-30.0, 0, 0)
	cam_pivot.add_child(camera)

# --------------------------------------------------------------------------- pylons

func _build_pylons() -> void:
	# Sockets follow the terrace's 180-degree turn so the brass inlays stay under each beacon.
	var sockets := [
		{"pos": Vector3(5.2, 0.0, 4.4), "name": "West Beacon"},
		{"pos": Vector3(-5.2, 0.0, 4.4), "name": "East Beacon"},
		{"pos": Vector3(0.0, 0.55, -5.4), "name": "Sanctum Beacon"},
	]
	var template: PackedScene = null
	if ResourceLoader.exists("res://assets/pylon.glb"):
		template = load("res://assets/pylon.glb")

	for entry in sockets:
		var root := Node3D.new()
		root.name = entry["name"].replace(" ", "")
		root.position = entry["pos"]
		add_child(root)

		if template != null:
			var model := template.instantiate()
			_restyle(model)
			# The reconstruction is normalised to metres in Blender; scale defensively to the brief.
			model.scale = Vector3.ONE * _fit_scale(model, PYLON_HEIGHT)
			root.add_child(model)
			for child in model.get_children():
				if child is MeshInstance3D:
					child.create_trimesh_collision()

		var bowl := OmniLight3D.new()
		bowl.light_color = EMBER
		bowl.light_energy = 0.0
		bowl.omni_range = 11.0
		bowl.position = Vector3(0, PYLON_HEIGHT * 0.92, 0)
		bowl.shadow_enabled = false
		root.add_child(bowl)

		var halo := MeshInstance3D.new()
		var sphere := SphereMesh.new()
		sphere.radius = 0.42
		sphere.height = 0.84
		halo.mesh = sphere
		var halo_mat := StandardMaterial3D.new()
		halo_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		halo_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		halo_mat.albedo_color = Color(EMBER.r, EMBER.g, EMBER.b, 0.0)
		halo_mat.emission_enabled = true
		halo_mat.emission = EMBER
		halo_mat.emission_energy_multiplier = 6.0
		halo_mat.albedo_color.a = 0.0
		halo.material_override = halo_mat
		halo.position = Vector3(0, PYLON_HEIGHT * 0.93, 0)
		halo.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(halo)

		pylons.append({
			"root": root,
			"light": bowl,
			"halo": halo,
			"halo_mat": halo_mat,
			"name": entry["name"],
			"position": entry["pos"],
			"lit": false,
			"progress": 0.0,
		})

func _fit_scale(model: Node3D, target_height: float) -> float:
	var box := AABB()
	var first := true
	for child in model.get_children():
		if child is MeshInstance3D:
			var mi := child as MeshInstance3D
			var aabb: AABB = mi.get_aabb()
			if first:
				box = aabb
				first = false
			else:
				box = box.merge(aabb)
	var height: float = maxf(box.size.y, 0.001)
	return target_height / height

# --------------------------------------------------------------------------- motes

func _build_motes() -> void:
	var positions := [
		Vector3(-2.4, 1.1, 6.2), Vector3(2.2, 1.0, 7.4), Vector3(-7.8, 1.2, 1.6),
		Vector3(7.6, 1.1, 2.2), Vector3(0.4, 1.3, 2.0), Vector3(-4.0, 1.2, -2.6),
		Vector3(4.4, 1.1, -3.2), Vector3(0.0, 1.9, -7.6), Vector3(-9.2, 1.4, 6.4),
		Vector3(9.0, 1.3, 6.0), Vector3(-1.8, 1.2, -8.4), Vector3(6.8, 1.2, -7.8),
	]
	for index in positions.size():
		var root := Node3D.new()
		root.position = positions[index]
		add_child(root)

		var mesh := MeshInstance3D.new()
		var sphere := SphereMesh.new()
		sphere.radius = 0.055
		sphere.height = 0.11
		mesh.mesh = sphere
		var mat := StandardMaterial3D.new()
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.albedo_color = LANTERN
		mat.emission_enabled = true
		mat.emission = LANTERN
		mat.emission_energy_multiplier = 7.0
		mesh.material_override = mat
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(mesh)

		var light := OmniLight3D.new()
		light.light_color = LANTERN
		light.light_energy = 0.55
		light.omni_range = 2.6
		root.add_child(light)

		motes.append({
			"root": root,
			"base": positions[index],
			"phase": float(index) * 0.7,
			"frequency": 0.35 + 0.05 * (index % 3),
			"taken": false,
		})

# --------------------------------------------------------------------------- audio

func _build_ambience() -> void:
	ambience_player = AudioStreamPlayer.new()
	ambience_player.bus = "Master"
	add_child(ambience_player)
	if ResourceLoader.exists("res://assets/audio/ambience.ogg"):
		ambience_player.stream = load("res://assets/audio/ambience.ogg")
		ambience_player.volume_db = -13.0
		ambience_player.play()

	fx_player = AudioStreamPlayer.new()
	add_child(fx_player)
	if ResourceLoader.exists("res://assets/audio/ignite.ogg"):
		ignite_sfx = load("res://assets/audio/ignite.ogg")
	if ResourceLoader.exists("res://assets/audio/chime.ogg"):
		chime_sfx = load("res://assets/audio/chime.ogg")
	if ResourceLoader.exists("res://assets/audio/dawn.ogg"):
		win_sfx = load("res://assets/audio/dawn.ogg")

func _play(stream: AudioStream, volume_db := -6.0) -> void:
	if stream == null or fx_player == null:
		return
	fx_player.stream = stream
	fx_player.volume_db = volume_db
	fx_player.play()

# --------------------------------------------------------------------------- hud

func _build_hud() -> void:
	hud_layer = CanvasLayer.new()
	add_child(hud_layer)
	hud = Control.new()
	hud.set_anchors_preset(Control.PRESET_FULL_RECT)
	hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud_layer.add_child(hud)
	hud.draw.connect(_draw_hud)
	hud.set_process(true)

func _draw_hud() -> void:
	var font := ThemeDB.fallback_font
	var size := hud.size
	var warm_ratio: float = clamp(warmth / WARMTH_MAX, 0.0, 1.0)

	# Title block, top-left: letterspaced caps over a hairline rule.
	hud.draw_string(font, Vector2(48, 62), "E M B E R K E E P", HORIZONTAL_ALIGNMENT_LEFT, -1, 22,
		BONE * Color(1, 1, 1, 0.92))
	hud.draw_line(Vector2(48, 76), Vector2(48 + 196.0, 76), BONE * Color(1, 1, 1, 0.22), 1.0)
	hud.draw_string(font, Vector2(48, 100), "The last lamplighter of a drowning shrine-city", HORIZONTAL_ALIGNMENT_LEFT, -1, 13,
		BONE * Color(1, 1, 1, 0.55))

	# Warmth: a hairline meter that shortens as the lantern dies.
	var meter_origin := Vector2(48, size.y - 74)
	hud.draw_string(font, Vector2(meter_origin.x, meter_origin.y - 12), "WARMTH", HORIZONTAL_ALIGNMENT_LEFT, -1, 12,
		BONE * Color(1, 1, 1, 0.62))
	hud.draw_line(meter_origin, meter_origin + Vector2(240, 0), BONE * Color(1, 1, 1, 0.16), 1.0)
	var pulse: float = 1.0 if warm_ratio > 0.35 else 0.55 + 0.45 * sin(elapsed * 7.0)
	var warm_col: Color = LANTERN if warm_ratio > 0.35 else EMBER
	hud.draw_line(meter_origin, meter_origin + Vector2(240.0 * warm_ratio, 0),
		warm_col * Color(1, 1, 1, pulse), 2.0)
	hud.draw_string(font, Vector2(meter_origin.x + 252, meter_origin.y + 4), "%d%%" % roundi(warmth),
		HORIZONTAL_ALIGNMENT_LEFT, -1, 13, BONE * Color(1, 1, 1, 0.7))

	# Beacon counter, top-right.
	var counter := "B E A C O N S   %d / 3" % lit
	hud.draw_string(font, Vector2(size.x - 300, 62), counter, HORIZONTAL_ALIGNMENT_LEFT, -1, 15,
		LANTERN if lit > 0 else BONE * Color(1, 1, 1, 0.62))
	hud.draw_line(Vector2(size.x - 300, 76), Vector2(size.x - 48, 76), BONE * Color(1, 1, 1, 0.16), 1.0)

	# Ignition progress for the nearest beacon.
	for pylon in pylons:
		if pylon["progress"] > 0.01 and not pylon["lit"]:
			var ratio: float = clamp(pylon["progress"] / IGNITE_SECONDS, 0.0, 1.0)
			var w := 180.0
			var origin := Vector2(size.x * 0.5 - w * 0.5, size.y - 96)
			hud.draw_line(origin, origin + Vector2(w, 0), BONE * Color(1, 1, 1, 0.18), 1.0)
			hud.draw_line(origin, origin + Vector2(w * ratio, 0), EMBER, 2.0)

	# Prompt / message line.
	if message != "":
		hud.draw_string(font, Vector2(48, size.y - 116), message, HORIZONTAL_ALIGNMENT_LEFT, -1, 14,
			BONE * Color(1, 1, 1, clamp(message_timer, 0.0, 1.0)))

	if state == "WON":
		hud.draw_string(font, Vector2(0, size.y * 0.46), "D A W N", HORIZONTAL_ALIGNMENT_CENTER, size.x, 46, LANTERN)
		hud.draw_string(font, Vector2(0, size.y * 0.46 + 34), "The keep is lit. The city remembers.",
			HORIZONTAL_ALIGNMENT_CENTER, size.x, 15, BONE * Color(1, 1, 1, 0.75))
	elif state == "LOST":
		hud.draw_string(font, Vector2(0, size.y * 0.46), "T H E   L I G H T   F A I L S",
			HORIZONTAL_ALIGNMENT_CENTER, size.x, 34, EMBER)
		hud.draw_string(font, Vector2(0, size.y * 0.46 + 32), "Press R to relight.",
			HORIZONTAL_ALIGNMENT_CENTER, size.x, 14, BONE * Color(1, 1, 1, 0.7))

# --------------------------------------------------------------------------- loop

func _process(delta: float) -> void:
	elapsed += delta
	message_timer = max(0.0, message_timer - delta * 0.6)
	if message_timer <= 0.0:
		message = ""

	if state == "PLAYING":
		warmth = maxf(0.0, warmth - WARMTH_DRAIN * delta)
		if warmth <= 0.0:
			state = "LOST"
			warmth = 0.0
			lantern_light.light_energy = 0.0
			lantern_beam.light_energy = 0.0
			_play(win_sfx, -8.0)

	_update_player(delta)
	_update_lantern(delta)
	_update_motes(delta)
	_update_pylons(delta)
	hud.queue_redraw()

func _update_player(delta: float) -> void:
	if player == null:
		return
	var input := Vector2.ZERO
	if state == "PLAYING" and not ignoring_input:
		if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP):
			input.y -= 1.0
		if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN):
			input.y += 1.0
		if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
			input.x -= 1.0
		if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
			input.x += 1.0
		if Input.is_physical_key_pressed(KEY_R) and state == "LOST":
			get_tree().reload_current_scene()

	var sprint := Input.is_physical_key_pressed(KEY_SHIFT)
	var speed := 4.2 if sprint else 2.6
	var direction := Vector3.ZERO
	if input.length() > 0.05:
		var yaw := cam_pivot.rotation.y
		var forward := Vector3(-sin(yaw), 0, -cos(yaw))
		var right := Vector3(cos(yaw), 0, -sin(yaw))
		direction = (forward * input.y + right * input.x).normalized()

	var target := direction * speed
	player.velocity.x = move_toward(player.velocity.x, target.x, 12.0 * delta)
	player.velocity.z = move_toward(player.velocity.z, target.z, 12.0 * delta)
	if not player.is_on_floor():
		player.velocity.y -= 18.0 * delta
	else:
		player.velocity.y = -0.1
	player.move_and_slide()

	# Camera follows with damping; yaw eases toward the facing direction.
	var desired := player.global_position + Vector3(0, 1.35, 0)
	cam_pivot.global_position = cam_pivot.global_position.lerp(desired, clamp(delta * 6.0, 0.0, 1.0))
	if direction.length() > 0.1:
		var target_yaw := atan2(-direction.x, -direction.z)
		cam_pivot.rotation.y = lerp_angle(cam_pivot.rotation.y, target_yaw, delta * 2.2)

func _update_lantern(delta: float) -> void:
	if lantern_rig == null:
		return
	var speed := Vector2(player.velocity.x, player.velocity.z).length()
	var sway := sin(elapsed * 4.4) * deg_to_rad(3.5 + speed * 1.2)
	lantern_rig.rotation.z = lerp(lantern_rig.rotation.z, sway, delta * 6.0)
	lantern_rig.rotation.x = lerp(lantern_rig.rotation.x, sin(elapsed * 3.1) * 0.05, delta * 5.0)
	var flicker := 0.92 + 0.08 * sin(elapsed * 11.3) * sin(elapsed * 4.7)
	var health: float = clampf(warmth / WARMTH_MAX, 0.0, 1.0)
	lantern_light.light_energy = 2.4 * flicker * (0.45 + 0.55 * health)
	lantern_light.omni_range = 8.0 * (0.7 + 0.3 * health)
	lantern_beam.light_energy = 1.1 * flicker * (0.4 + 0.6 * health)
	lantern_light.light_color = LANTERN.lerp(EMBER, 1.0 - health)

func _update_motes(delta: float) -> void:
	for mote in motes:
		if mote["taken"]:
			continue
		var node: Node3D = mote["root"]
		var base: Vector3 = mote["base"]
		var phase: float = mote["phase"]
		var freq: float = mote["frequency"]
		node.position = base + Vector3(sin(elapsed * freq * 2.0 + phase) * 0.35,
			sin(elapsed * freq * 2.6 + phase) * 0.16, cos(elapsed * freq * 1.7 + phase) * 0.35)
		if state == "PLAYING" and player.global_position.distance_to(node.global_position) < 1.15:
			mote["taken"] = true
			node.visible = false
			warmth = min(WARMTH_MAX, warmth + MOTE_RESTORE)
			message = "A mote of the old fire."
			message_timer = 1.4
			_play(chime_sfx, -8.0)

func _update_pylons(delta: float) -> void:
	for pylon in pylons:
		if pylon["lit"]:
			continue
		var distance := player.global_position.distance_to(pylon["position"])
		var holding := Input.is_physical_key_pressed(KEY_E) or ignoring_input
		if distance < IGNITE_RANGE and holding and state == "PLAYING":
			pylon["progress"] = pylon["progress"] + delta
			if pylon["progress"] >= IGNITE_SECONDS:
				_light_pylon(pylon)
		else:
			pylon["progress"] = max(0.0, pylon["progress"] - delta * 0.8)

func _light_pylon(pylon: Dictionary) -> void:
	pylon["lit"] = true
	lit += 1
	var light: OmniLight3D = pylon["light"]
	var halo_mat: StandardMaterial3D = pylon["halo_mat"]
	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(light, "light_energy", 7.5, 1.2).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tween.tween_property(halo_mat, "albedo_color:a", 0.55, 1.2).set_trans(Tween.TRANS_CUBIC)
	_play(ignite_sfx, -4.0)
	message = "%s remembers the fire." % pylon["name"]
	message_timer = 2.2
	if lit >= 3:
		_win()

func _win() -> void:
	state = "WON"
	_play(win_sfx, -5.0)
	if world_env == null:
		return
	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(world_env, "ambient_light_energy", 0.55, 4.0)
	tween.tween_property(world_env, "fog_density", 0.010, 4.0)
	tween.tween_property(world_env, "background_color", Color(0.075, 0.115, 0.135), 4.0)

# --------------------------------------------------------------------------- smoke test

func _run_smoke() -> void:
	ignoring_input = true
	var report := {"scene": "res://main.tscn", "engine": Engine.get_version_info()["string"], "steps": []}
	await _settle(0.6)
	await _shot("00_start")
	var start_warmth := warmth

	# Deficit check: warmth must actually drain while playing.
	await _settle(1.4)
	report["steps"].append({"id": "warmth_drains", "from": start_warmth, "to": warmth, "ok": warmth < start_warmth})

	# Deficit check two: a mote must restore warmth that has been spent.
	warmth = 40.0
	var mote: Dictionary = motes[0]
	var before := warmth
	player.global_position = Vector3(0, 0.2, 0.0)
	await _settle(0.2)
	player.global_position = mote["root"].global_position + Vector3(0, -1.0, 0)
	await _settle(0.5)
	report["steps"].append({"id": "mote_restores", "before": before, "after": warmth, "ok": warmth > before})
	warmth = 85.0

	# Each beacon must light and report completion.
	for index in pylons.size():
		var pylon: Dictionary = pylons[index]
		player.global_position = pylon["position"] + Vector3(0.0, 1.0, 0.0)
		await _settle(1.5)
		report["steps"].append({"id": "ignite_%d" % index, "beacon": pylon["name"], "lit": pylon["lit"], "ok": pylon["lit"]})
	await _settle(0.8)
	await _shot("01_dawn")
	report["steps"].append({"id": "win_state", "state": state, "beacons": lit, "ok": state == "WON"})

	# Camera-distance framing check for the art-bible review.
	player.global_position = Vector3(-1.0, 0.2, 6.0)
	await _settle(0.9)
	await _shot("02_gameplay_west")
	player.global_position = Vector3(4.6, 0.2, 6.4)
	await _settle(0.9)
	await _shot("03_beacon_lit")

	var failures: Array = report["steps"].filter(func(s): return not s["ok"])
	report["ok"] = failures.is_empty()
	report["failures"] = failures
	print("STUDIO_SMOKE_JSON " + JSON.stringify(report))
	if shot_dir != "":
		var file := FileAccess.open(shot_dir.path_join("runtime_report.json"), FileAccess.WRITE)
		if file != null:
			file.store_string(JSON.stringify(report, "  "))
			file.close()
	await _settle(0.2)
	get_tree().quit(0 if report["ok"] else 1)

func _settle(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout

func _shot(label: String) -> void:
	if shot_dir == "":
		return
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var path := shot_dir.path_join("shot_%s.png" % label)
	var error := image.save_png(path)
	print("STUDIO_SHOT %s %s" % [path, "ok" if error == OK else "error:%d" % error])
