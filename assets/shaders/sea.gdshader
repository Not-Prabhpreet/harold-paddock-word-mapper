shader_type spatial;
render_mode cull_back, specular_schlick_ggx;

// Conception Bay. The plane stays flat; the swell comes from an animated normal, which reads
// correctly at the distance the player ever sees it and costs almost nothing on a laptop.

uniform vec3 deep_color : source_color = vec3(0.035, 0.125, 0.225);
uniform vec3 shallow_color : source_color = vec3(0.11, 0.30, 0.42);
uniform vec3 sky_tint : source_color = vec3(0.52, 0.67, 0.80);
uniform float wave_scale = 0.09;
uniform float wave_strength : hint_range(0.0, 1.0) = 0.22;
uniform float speed = 0.25;

void fragment() {
	vec2 p = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xz * wave_scale;
	float t = TIME * speed;

	// Three crossing swells; their gradient becomes the surface normal.
	float h = sin(p.x * 1.0 + t) * 0.5
	        + sin(p.y * 1.31 - t * 0.83) * 0.32
	        + sin((p.x + p.y) * 0.67 + t * 1.27) * 0.21;
	float dx = cos(p.x * 1.0 + t) * 0.5 + cos((p.x + p.y) * 0.67 + t * 1.27) * 0.14;
	float dy = cos(p.y * 1.31 - t * 0.83) * 0.42 + cos((p.x + p.y) * 0.67 + t * 1.27) * 0.14;
	NORMAL = normalize(NORMAL + vec3(-dx, 0.0, -dy) * wave_strength);

	float facing = clamp(dot(normalize(VIEW), NORMAL), 0.0, 1.0);
	vec3 col = mix(deep_color, shallow_color, smoothstep(0.0, 0.55, facing));
	col = mix(sky_tint, col, smoothstep(0.03, 0.35, facing));   // grazing angles pick up the sky
	col += vec3(0.05) * smoothstep(0.55, 1.0, h);               // glints on the wave crests

	ALBEDO = col;
	ROUGHNESS = 0.08;
	METALLIC = 0.0;
	SPECULAR = 0.65;
}
