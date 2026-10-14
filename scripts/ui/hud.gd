extends Control
## On-screen overlay: the "Press E" prompt, a controls hint, and (F3) a debug readout of the
## Twine variables so you can watch $accent, $ethics and $lexicon change.

@onready var _prompt: Label = %InteractPrompt
@onready var _state_label: Label = %StateLabel
@onready var _hint: Label = $ControlsHint

var _prompt_text := ""


func _ready() -> void:
	_state_label.visible = false
	GameState.var_changed.connect(func(_name: String, _value: Variant) -> void: _refresh_state())
	GameState.state_reset.connect(_refresh_state)
	_refresh_state()


func _process(_delta: float) -> void:
	_prompt.visible = _prompt_text != "" and not GameState.in_dialogue
	_hint.visible = not GameState.in_dialogue


func show_prompt(text: String) -> void:
	_prompt_text = text
	_prompt.text = text


func toggle_debug() -> void:
	_state_label.visible = not _state_label.visible


func _refresh_state() -> void:
	var lines := PackedStringArray(["FIELD STATE (F3 to hide)"])
	for key in ["name", "accent", "ethics", "question", "lexicon", "fieldworkScore"]:
		lines.append("$%s = %s" % [key, str(GameState.get_var(key, "-"))])
	_state_label.text = "\n".join(lines)
