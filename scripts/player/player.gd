class_name Player
extends CharacterBody3D
## Third-person Harold: WASD to walk (Shift to run), mouse to orbit the camera, E to talk.
##
## GODOT CONCEPTS
## - CharacterBody3D: a physics body you move yourself by setting `velocity` and calling
##   move_and_slide(), which handles collisions and sliding along walls.
## - SpringArm3D: holds the camera at a distance and pulls it in when a wall is in the way,
##   so the camera never clips through the house.
## - Tween: animates a property over time (here: the camera easing into a conversation shot).
## - _physics_process(delta) runs at a fixed 60 Hz; _unhandled_input(event) gets input that
##   no UI element consumed first.

signal interactable_changed(target: Node)

@export var walk_speed := 3.2
@export var run_speed := 6.5
@export var turn_speed := 10.0
@export var mouse_sensitivity := 0.0025
@export var camera_distance := 4.0
## Conversation shot: how far back the camera sits and how high it floats, so both faces land in
## the upper half of the screen, clear of the dialogue panel.
@export var conversation_distance := 2.45
@export var conversation_height := 1.48

@onready var _visual: Node3D = $Visual
@onready var _pivot: Node3D = $CameraPivot
@onready var _arm: SpringArm3D = $CameraPivot/SpringArm3D
@onready var _model: CharacterModel = $Visual/CharacterModel

## The NPC currently in range (set by the NPC's Area3D), or null.
var interactable: Node = null
var _saved_camera := {}
var _tween: Tween
var _rest_pivot := Vector3.ZERO


func _ready() -> void:
	_arm.add_excluded_object(get_rid())
	_arm.spring_length = camera_distance
	_rest_pivot = _pivot.position
	if _model.load_model():
		for child in _visual.get_children():
			if child is CSGShape3D:
				(child as CSGShape3D).visible = false


func _unhandled_input(event: InputEvent) -> void:
	if GameState.in_dialogue:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var motion := event as InputEventMouseMotion
		_pivot.rotate_y(-motion.relative.x * mouse_sensitivity)
		_pivot.rotation.x = clampf(_pivot.rotation.x - motion.relative.y * mouse_sensitivity, deg_to_rad(-60), deg_to_rad(25))
	elif event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event.is_action_pressed("interact") and interactable != null:
		interactable.interact(self)


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity += get_gravity() * delta

	var input := Vector2.ZERO
	if not GameState.in_dialogue:
		input = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	# Move relative to where the camera looks, not where Harold faces.
	var direction := (Basis(Vector3.UP, _pivot.rotation.y) * Vector3(input.x, 0.0, input.y)).normalized()
	var speed := run_speed if Input.is_action_pressed("run") else walk_speed
	velocity.x = direction.x * speed
	velocity.z = direction.z * speed
	move_and_slide()

	if direction.length() > 0.01:
		var target_yaw := atan2(-direction.x, -direction.z)  # Godot's forward is -Z
		_visual.rotation.y = lerp_angle(_visual.rotation.y, target_yaw, clampf(turn_speed * delta, 0.0, 1.0))
	_update_animation()


func _update_animation() -> void:
	var horizontal := Vector2(velocity.x, velocity.z).length()
	if horizontal > walk_speed + 0.5:
		_model.play_first(["run", "running", "walk", "walking"])
	elif horizontal > 0.2:
		_model.play_first(["walk", "walking"])
	else:
		_model.play_first(["idle"])


## Turns Harold toward the person he's talking to and eases the camera over his shoulder.
func enter_conversation(npc: Node3D) -> void:
	var to_npc := npc.global_position - global_position
	to_npc.y = 0.0
	if to_npc.length() < 0.01:
		return
	var face_yaw := atan2(-to_npc.x, -to_npc.z)
	_visual.rotation.y = face_yaw
	_saved_camera = {"yaw": _pivot.rotation.y, "pitch": _pivot.rotation.x}
	# Pull the pivot toward the person being spoken to and up to head height, then orbit off to
	# one side: an over-the-shoulder two-shot with both faces above the dialogue panel.
	var mid := to_npc * 0.42
	_ease_camera(face_yaw + deg_to_rad(36.0), deg_to_rad(-9.0), conversation_distance,
			Vector3(mid.x, conversation_height, mid.z))


func exit_conversation() -> void:
	if _saved_camera.is_empty():
		return
	_ease_camera(_saved_camera["yaw"], _saved_camera["pitch"], camera_distance, _rest_pivot)
	_saved_camera = {}


func _ease_camera(yaw: float, pitch: float, distance: float, pivot_pos: Vector3 = Vector3.INF) -> void:
	if _tween != null:
		_tween.kill()
	# Unwrap so the tween turns the short way round.
	var start := _pivot.rotation.y
	yaw = start + wrapf(yaw - start, -PI, PI)
	_tween = create_tween().set_parallel().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_tween.tween_property(_pivot, "rotation:y", yaw, 0.6)
	_tween.tween_property(_pivot, "rotation:x", pitch, 0.6)
	_tween.tween_property(_arm, "spring_length", distance, 0.6)
	if pivot_pos != Vector3.INF:
		_tween.tween_property(_pivot, "position", pivot_pos, 0.6)


func set_interactable(target: Node) -> void:
	interactable = target
	interactable_changed.emit(target)


func clear_interactable(target: Node) -> void:
	if interactable == target:
		set_interactable(null)
