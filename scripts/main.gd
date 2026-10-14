extends Node3D
## Root of the Carbonear scene: starts the episode, and connects the pieces to each other.
##
## GODOT CONCEPT - Scenes and the scene tree: a scene (.tscn) is a saved tree of nodes.
## main.tscn instances player.tscn, npc.tscn, the props and the UI scenes as children.
## `$Player` is shorthand for get_node("Player"), a path relative to this node.

## The player's name survives "Play again" (the scene reloads, static vars don't).
static var remembered_name := ""
## Show the title screen only on the first run, not after "Play again".
static var title_seen := false

@onready var _player: Player = $Player
@onready var _hud: Control = $UI/HUD
@onready var _dialogue: Control = $UI/DialogueUI
@onready var _dragonfly: Dragonfly = $Dragonfly
@onready var _fade: ScreenFade = $UI/ScreenFade
@onready var _title: Control = $UI/TitleScreen

var _conversation_npc: Node3D = null


func _ready() -> void:
	GameState.reset(Story.initial_variables())
	if remembered_name != "":
		GameState.set_var("name", remembered_name)
	GameState.var_changed.connect(_on_var_changed)

	_player.interactable_changed.connect(_on_interactable_changed)
	_dialogue.conversation_started.connect(_player.enter_conversation)
	_dialogue.conversation_started.connect(func(npc: Node3D) -> void: _conversation_npc = npc)
	_dialogue.dialogue_finished.connect(_player.exit_conversation)
	_dialogue.passage_shown.connect(_on_passage_shown)

	_scatter_ground_cover()
	_fade.fade_in(0.7)

	# Title screen first, then the Twine "Start" page: name prompt and the 1964 introduction.
	if title_seen:
		_title.visible = false
		_open_story()
	else:
		GameState.in_dialogue = true
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		_title.begin.connect(_open_story)


## Grass and rocks are placed at load time, keeping clear of the road, the driveway, the house,
## the garden and the fence line.
func _scatter_ground_cover() -> void:
	var keep_clear: Array[Rect2] = [
		Rect2(-40.0, 14.0, 80.0, 6.0),    # highway
		Rect2(-40.0, 12.6, 80.0, 2.0),    # fence line
		Rect2(-7.8, 2.4, 3.6, 12.4),      # gravel driveway
		Rect2(-4.8, -3.8, 9.6, 8.6),      # house footprint and steps
		Rect2(5.1, 1.1, 4.8, 5.8),        # potato garden
		Rect2(-10.5, 18.9, 2.0, 1.8),     # route sign
	]
	for node in [$Grass, $Rocks]:
		(node as Scatter).build(keep_clear)


func _open_story() -> void:
	title_seen = true
	_dialogue.open_page(Story.data.get("start", "Start"))


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("journal") and not _dialogue.is_open():
		_dialogue.open_page("Field Journal", true)
	elif event.is_action_pressed("toggle_debug"):
		_hud.toggle_debug()


func _on_interactable_changed(target: Node) -> void:
	_hud.show_prompt("" if target == null else target.get_prompt())


func _on_passage_shown(_passage: String, event: String) -> void:
	match event:
		"dragonfly_flyby":
			if _conversation_npc != null:
				_dragonfly.fly_between(_player.global_position, _conversation_npc.global_position)


func _on_var_changed(var_name: String, value: Variant) -> void:
	if var_name == "name":
		remembered_name = str(value)
