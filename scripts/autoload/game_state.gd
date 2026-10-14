extends Node
## GameState (autoload): the Twine $variables plus a little runtime state.
##
## Every Twine (set: $x to ...) ends up in set_var(), which emits `var_changed`.
## GODOT CONCEPT - Signals: Godot's observer pattern. Other nodes `connect()` a
## function to a signal and it is called every time the signal is `emit()`ted.

signal var_changed(var_name: String, value: Variant)
signal state_reset

## Twine variables without the `$`, e.g. vars["accent"] == "Local".
var vars: Dictionary = {}

## True while a conversation is on screen. The player reads it to freeze movement.
var in_dialogue := false


func reset(initial: Dictionary) -> void:
	vars.clear()
	for key: String in initial:
		vars[key] = _normalize(initial[key])
	state_reset.emit()


func get_var(var_name: String, default: Variant = null) -> Variant:
	return vars.get(var_name, default)


func set_var(var_name: String, value: Variant) -> void:
	value = _normalize(value)
	vars[var_name] = value
	var_changed.emit(var_name, value)


## JSON has no int type, so Godot parses 0 as 0.0. Turn whole floats back into ints.
static func _normalize(value: Variant) -> Variant:
	if value is float and is_equal_approx(value, roundf(value)):
		return int(value)
	return value
