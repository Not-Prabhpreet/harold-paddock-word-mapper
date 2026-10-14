extends Control
## Title screen: the key art, the game's name and a Begin button. Emits `begin` when the
## player is ready; main.gd then opens the Twine "Start" page.

signal begin

@onready var _button: Button = %BeginButton


func _ready() -> void:
	_button.pressed.connect(_on_begin)
	_button.grab_focus.call_deferred()


func _unhandled_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_accept"):
		get_viewport().set_input_as_handled()
		_on_begin()


func _on_begin() -> void:
	if not visible:
		return
	visible = false
	begin.emit()
