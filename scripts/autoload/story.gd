extends Node
## Story (autoload): loads the converted Twine dialogue graph once at startup.
##
## GODOT CONCEPT - Autoload: a script listed under [autoload] in project.godot is
## instantiated before any scene and reachable everywhere by name (here: `Story`).
## Think of it as a module-level singleton in Python.

const STORY_PATH := "res://dialogue/story.json"
const PRESENTATION_PATH := "res://dialogue/presentation.json"

var data: Dictionary = {}
## How passages are staged in 3D (pages vs conversation, events, bundled images).
var presentation: Dictionary = {}


func _ready() -> void:
	data = load_story(STORY_PATH)
	presentation = load_story(PRESENTATION_PATH)


func is_page(passage: String) -> bool:
	return passage in presentation.get("page_passages", [])


func is_world(passage: String) -> bool:
	return passage in presentation.get("world_passages", [])


func is_final(passage: String) -> bool:
	return passage in presentation.get("final_passages", [])


static func load_story(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("Story: cannot open %s (%s)" % [path, error_string(FileAccess.get_open_error())])
		return {}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if parsed is Dictionary:
		return parsed
	push_error("Story: %s is not a JSON object" % path)
	return {}


## Starting values for $variables (from the Twine StoryInit passage), deep-copied.
func initial_variables() -> Dictionary:
	return (data.get("variables", {}) as Dictionary).duplicate(true)
