shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

// EMBERKEEP water: near-black standing water with slow broad ripples and a cold grazing sheen.
uniform vec4 deep_color : source_color = vec4(0.200, 0.280, 0.320, 1.0);
uniform vec4 sheen_color : source_color = vec4(0.340, 0.460, 0.490, 1.0);
uniform float ripple_scale = 0.35;
uniform float ripple_speed = 0.06;
uniform float sheen_power = 4.0;

varying vec3 world_pos;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
			mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = world_pos.xz * ripple_scale;
	float t = TIME * ripple_speed;
	float n = noise(p + vec2(t, t * 0.7)) * 0.6 + noise(p * 2.3 - vec2(t * 1.4, t)) * 0.4;
	float dx = noise(p + vec2(0.15, 0.0) + vec2(t, t * 0.7)) - n;
	float dz = noise(p + vec2(0.0, 0.15) + vec2(t, t * 0.7)) - n;

	vec3 normal_map = normalize(vec3(dx * 4.5, dz * 4.5, 1.0));
	NORMAL = normal_map;

	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float sheen = pow(1.0 - facing, sheen_power);
	ALBEDO = mix(deep_color.rgb, sheen_color.rgb, sheen * 0.85);
	ROUGHNESS = mix(0.04, 0.22, sheen);
	METALLIC = 0.0;
	SPECULAR = 0.85;
	EMISSION = sheen_color.rgb * sheen * 0.05;
}
