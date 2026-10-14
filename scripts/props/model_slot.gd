class_name ModelSlot
extends Node3D
## Swaps placeholder shapes for a generated model as soon as the model file exists.
##
## Put simple placeholder CSG shapes as children of this node and set `model_path` to the model
## that tools/blender/ builds. If the file exists the placeholder is hidden and the model appears;
## if not, the placeholder stays, so a missing model never breaks the scene.
##
## GODOT CONCEPT - .glb files are imported as PackedScenes: a saved node tree you can
## instantiate(), exactly like a .tscn.

## e.g. res://assets/buildings/saltbox_house/model.glb
@export_file("*.glb", "*.gltf", "*.tscn") var model_path := ""
## Scale the model so its height matches this many metres. 0 keeps its own size.
@export var fit_height := 0.0
## Extra rotation around the vertical axis, for models that face the wrong way.
@export var yaw_degrees := 0.0
## Build collision from the model's meshes so the player can't walk through it.
@export var add_collision := true

var model: Node3D = null


func _ready() -> void:
	if model_path == "" or not ResourceLoader.exists(model_path):
		return
	var scene := load(model_path) as PackedScene
	if scene == null:
		push_warning("ModelSlot: %s is not a scene" % model_path)
		return
	for child in get_children():
		_disable_placeholder(child)
	model = scene.instantiate() as Node3D
	model.name = "Model"
	model.rotation_degrees.y = yaw_degrees
	add_child(model)
	if fit_height > 0.0:
		var box := _bounds(model)
		if box.size.y > 0.001:
			model.scale *= fit_height / box.size.y
	if add_collision:
		for mesh in model.find_children("*", "MeshInstance3D", true, false):
			(mesh as MeshInstance3D).create_trimesh_collision()


## Hides placeholder shapes. Other children (e.g. the sign's Label3D lettering) stay visible.
func _disable_placeholder(node: Node) -> void:
	if node is CSGShape3D:
		(node as CSGShape3D).use_collision = false
		(node as CSGShape3D).visible = false


static func _bounds(root: Node3D) -> AABB:
	var box := AABB()
	var first := true
	for mesh in root.find_children("*", "MeshInstance3D", true, false):
		var mi := mesh as MeshInstance3D
		var local := root.global_transform.affine_inverse() * mi.global_transform * mi.get_aabb()
		box = local if first else box.merge(local)
		first = false
	return box
