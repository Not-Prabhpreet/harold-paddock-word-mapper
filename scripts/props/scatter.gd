class_name Scatter
extends MultiMeshInstance3D
## Sprinkles one mesh across the ground many times in a single draw call.
##
## GODOT CONCEPT - MultiMeshInstance3D draws thousands of copies of the same mesh in one go, so a
## field of grass costs about as much as a single tuft. Each copy gets its own position, rotation
## and size, but they all share the mesh and material.
##
## `build()` is called from main.gd with the rectangles to keep clear (the road, the driveway,
## the house, the garden), so nothing sprouts through the geometry.

## Model to scatter, e.g. res://assets/props/grass_tuft/model.glb
@export_file("*.glb") var source_model := ""
@export var count := 600
## Half-extents of the scatter area on the ground plane, around this node's position.
@export var area := Vector2(34.0, 34.0)
@export var scale_range := Vector2(0.75, 1.35)
## Keep instances at least this far from the centre (used to ring rocks around the edges).
@export var inner_radius := 0.0
@export var random_seed := 1
@export var tilt_degrees := 7.0


func build(exclusions: Array = []) -> void:
	if source_model == "" or not ResourceLoader.exists(source_model):
		return
	var source := (load(source_model) as PackedScene).instantiate()
	var meshes := source.find_children("*", "MeshInstance3D", true, false)
	if meshes.is_empty():
		source.free()
		return

	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = (meshes[0] as MeshInstance3D).mesh
	mm.instance_count = count

	var rng := RandomNumberGenerator.new()
	rng.seed = random_seed
	var placed := 0
	var attempts := 0
	while placed < count and attempts < count * 24:
		attempts += 1
		var x := rng.randf_range(-area.x, area.x)
		var z := rng.randf_range(-area.y, area.y)
		var here := Vector2(x, z)
		if inner_radius > 0.0 and here.length() < inner_radius:
			continue
		var world := Vector2(global_position.x + x, global_position.z + z)
		var blocked := false
		for rect: Rect2 in exclusions:
			if rect.has_point(world):
				blocked = true
				break
		if blocked:
			continue
		var basis := Basis(Vector3.UP, rng.randf_range(0.0, TAU))
		basis = basis.rotated(Vector3.RIGHT, deg_to_rad(rng.randf_range(-tilt_degrees, tilt_degrees)))
		basis = basis.scaled(Vector3.ONE * rng.randf_range(scale_range.x, scale_range.y))
		mm.set_instance_transform(placed, Transform3D(basis, Vector3(x, 0.0, z)))
		placed += 1

	mm.instance_count = placed   # trim the tail if the area was crowded
	multimesh = mm
	source.free()
