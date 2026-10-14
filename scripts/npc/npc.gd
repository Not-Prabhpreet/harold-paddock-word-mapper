class_name NPC
extends Node3D
## A character Harold can talk to. Which conversation it plays, its voice and its 3D model are
## all data (the @export fields), so new NPCs are new scene instances, not new code.
##
## GODOT CONCEPTS
## - @export shows a variable in the editor's Inspector so it can be set per instance.
## - Area3D is an invisible trigger volume. Its body_entered / body_exited signals fire
##   when a physics body (the player) walks in or out.

## Shown in the "Press E" prompt.
@export var display_name := "the man in the garden"
## Passage in dialogue/story.json where this conversation starts.
@export var entry_passage := "Carbonear 02"
## Optional: a passage where this NPC's conversation stops early (its choices are disabled).
@export var end_passage := ""
## Talk only once: after the conversation ends the prompt no longer appears.
@export var talk_once := true
## Animation this character loops when nobody is talking to them (the gardener hoes his garden).
@export var idle_animation := "idle"
## Which speaker in voice/lines.json is this character. Their lines play from this NPC.
@export var voice_speaker := "man"
## Folder holding this character's rigged.glb. If it is missing the placeholder shapes show.
@export_dir var asset_dir := "res://assets/characters/garden_man"
## The speaker's social attributes, for the Fieldwork Ledger that is still to come.
@export var speaker_attributes := {"gender": "Male", "age_group": "older", "region": "Carbonear"}

@onready var _area: Area3D = $InteractArea
@onready var _placeholder_head: Node3D = get_node_or_null("Head")

var voice: AudioStreamPlayer3D
var talked := false
var _noticed := false
var _playing_once := false
var _model: CharacterModel
var _talking := false
var _talk_time := 0.0


func _ready() -> void:
	_area.body_entered.connect(_on_body_entered)
	_area.body_exited.connect(_on_body_exited)
	voice = AudioStreamPlayer3D.new()
	voice.name = "Voice"
	voice.position = Vector3(0, 1.65, 0)
	voice.unit_size = 4.0
	add_child(voice)

	_model = CharacterModel.new()
	_model.name = "CharacterModel"
	_model.asset_dir = asset_dir
	add_child(_model)
	if _model.load_model():
		_use_model_instead_of_placeholder()
	if _model.anim != null:
		_model.anim.animation_finished.connect(_on_animation_finished)
	_update_animation()


func can_talk() -> bool:
	return not (talk_once and talked)


func get_prompt() -> String:
	return "Press E to talk to %s" % display_name


func interact(by: Node3D) -> void:
	if not can_talk():
		return
	var ui := get_tree().get_first_node_in_group("dialogue_ui")
	if ui == null:
		push_error("NPC: no node in group 'dialogue_ui'")
		return
	face(by.global_position)
	_playing_once = false
	talked = true
	if talk_once and by is Player:
		(by as Player).clear_interactable(self)
	ui.start(entry_passage, end_passage, self)


## Called by the dialogue UI while one of this character's lines is playing.
func set_talking(talking: bool) -> void:
	_talking = talking
	_update_animation()


func face(target: Vector3) -> void:
	target.y = global_position.y  # turn around the vertical axis only
	if global_position.distance_to(target) > 0.1:
		look_at(target, Vector3.UP)


func _process(delta: float) -> void:
	# Fallback for the placeholder body only: nod the head while talking.
	if _model.anim == null and _placeholder_head != null:
		_talk_time = _talk_time + delta if _talking else 0.0
		_placeholder_head.position.y = 1.68 + (sin(_talk_time * 14.0) * 0.015 if _talking else 0.0)


func _on_animation_finished(_anim_name: String) -> void:
	_playing_once = false
	_update_animation()


## Called when Harold first comes within talking range: the man straightens up and waves.
func _greet() -> void:
	if _noticed or not can_talk():
		return
	_noticed = true
	var player := get_tree().get_first_node_in_group("player")
	if player != null:
		face((player as Node3D).global_position)
	if _model.play_once(["wave"]) != "":
		_playing_once = true


func _update_animation() -> void:
	if _playing_once:
		return
	if _talking:
		_model.play_first(["talking", "idle"])
	else:
		_model.play_first([idle_animation, "idle"])


func _use_model_instead_of_placeholder() -> void:
	for child in get_children():
		if child is CSGShape3D:
			(child as CSGShape3D).visible = false
			(child as CSGShape3D).use_collision = false
	_placeholder_head = null
	var body := StaticBody3D.new()  # keep the player from walking through the character
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.3
	capsule.height = 1.7
	shape.shape = capsule
	shape.position.y = 0.85
	body.add_child(shape)
	add_child(body)


func _on_body_entered(body: Node3D) -> void:
	if body is Player and can_talk():
		(body as Player).set_interactable(self)
		_greet()


func _on_body_exited(body: Node3D) -> void:
	if body is Player:
		(body as Player).clear_interactable(self)
