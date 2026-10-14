class_name CharacterModel
extends Node3D
## Loads a character built by tools/blender/characters.py and plays its animations by name.
##
## Looks in `asset_dir` for rigged.glb (or a static model.glb). The rigged file carries every clip
## ("idle", "walk", "talking"...). If no file is there, load_model() returns false and the owner
## keeps showing its simple placeholder shapes, so the game still runs.

@export_dir var asset_dir := ""
## Blender exports characters facing +Z; Godot's forward is -Z, hence the default half turn.
@export var yaw_degrees := 180.0

const LOOPING := ["idle", "talking", "walk", "walking", "run", "running", "hoeing", "writing"]

var anim: AnimationPlayer = null


func load_model() -> bool:
	var path := ""
	for file in ["rigged.glb", "model.glb"]:
		if asset_dir != "" and ResourceLoader.exists(asset_dir.path_join(file)):
			path = asset_dir.path_join(file)
			break
	if path == "":
		return false
	var model := (load(path) as PackedScene).instantiate() as Node3D
	model.name = "Model"
	model.rotation_degrees.y = yaw_degrees
	add_child(model)
	var players := model.find_children("*", "AnimationPlayer", true, false)
	if not players.is_empty():
		anim = players[0]
		_set_loops()
	return true


## glTF carries no loop flag, so cycles that must repeat are marked here by name.
func _set_loops() -> void:
	for anim_name in anim.get_animation_list():
		if anim_name in LOOPING:
			anim.get_animation(anim_name).loop_mode = Animation.LOOP_LINEAR


func has_animation(anim_name: String) -> bool:
	return anim != null and anim.has_animation(anim_name)


## Plays the first of `names` that exists once, without looping. Returns the one played.
func play_once(names: Array, blend := 0.18) -> String:
	if anim == null:
		return ""
	for n: String in names:
		if anim.has_animation(n):
			anim.get_animation(n).loop_mode = Animation.LOOP_NONE
			anim.play(n, blend)
			return n
	return ""


## Plays the first of `names` that exists, blending over `blend` seconds. Returns the one played.
func play_first(names: Array, blend := 0.25) -> String:
	if anim == null:
		return ""
	for n: String in names:
		if anim.has_animation(n):
			if anim.current_animation != n:
				anim.play(n, blend)
			return n
	return ""
