shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

// Meadow grass for the Carbonear fields: three tones broken up by layered value noise, so the
// ground reads as patchy summer grass instead of one flat green. Everything is driven by world
// position, so the pattern never repeats visibly and needs no texture file.

uniform vec3 grass_shade : source_color = vec3(0.20, 0.31, 0.14);
uniform vec3 grass_mid : source_color = vec3(0.39, 0.51, 0.22);
uniform vec3 grass_dry : source_color = vec3(0.63, 0.60, 0.33);
uniform float patch_scale = 0.030;   // wide drifts, tens of metres across
uniform float meso_scale = 0.16;     // clumps a few metres across
uniform float detail_scale = 0.85;   // fine mottling underfoot
uniform float dry_amount : hint_range(0.0, 1.0) = 0.5;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

float value_noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
	           mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
	float total = 0.0;
	float amp = 0.5;
	for (int i = 0; i < 4; i++) {
		total += amp * value_noise(p);
		p *= 2.07;
		amp *= 0.5;
	}
	return total;
}

void fragment() {
	vec2 p = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xz;
	float patches = fbm(p * patch_scale);
	float meso = fbm(p * meso_scale + vec2(31.7, 11.3));
	float detail = fbm(p * detail_scale);

	vec3 col = mix(grass_shade, grass_mid, smoothstep(0.26, 0.74, patches * 0.55 + meso * 0.45));
	col = mix(col, grass_dry, smoothstep(0.48, 0.86, meso * 0.5 + detail * 0.5) * dry_amount);
	col *= 0.86 + 0.30 * detail;

	ALBEDO = col;
	ROUGHNESS = 0.94;
	SPECULAR = 0.08;
}
