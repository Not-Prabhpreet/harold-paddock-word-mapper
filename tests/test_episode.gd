extends SceneTree
## End-to-end test: plays all of episode 1 in the real 3D scene, the way a student would.
##   Godot_v4.7.2-stable_win64_console.exe --headless --path . -s res://tests/test_episode.gd
## Without --headless it also saves screenshots to user://screenshots/ (paths are printed).

var _failures := 0
var _ui: Control
var _body: RichTextLabel


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var main: Node = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	await _frames(5)
	var game_state: Node = root.get_node("GameState")
	var player: CharacterBody3D = main.get_node("Player")
	_ui = main.get_node("UI/DialogueUI")
	_body = _ui.get_node("%Body")
	_ui._voice.audio_dir = "res://tests/fixtures/voice/"  # silent stand-in for the greeting

	# --- Title screen, then the opening page with the name prompt
	var title: Control = main.get_node("UI/TitleScreen")
	_check(title.visible and game_state.in_dialogue and not _ui.visible, "title screen first, player frozen")
	await _shot("00_title")
	title.get_node("%BeginButton").pressed.emit()
	await _frames(3)
	_check(not title.visible and _ui.visible, "Begin opens the story")
	var fields := _ui.find_children("*", "LineEdit", true, false)
	_check(not fields.is_empty() and _body.text.contains("What is your name"), "name prompt shown")
	await _shot("01_name_prompt")
	var field: LineEdit = fields[0]
	field.text = "Professor"
	field.text_submitted.emit(field.text)
	await _frames(3)
	_check(game_state.get_var("name") == "Professor", "$name stored")
	_check(_body.text.contains("Welcome Professor") and _body.text.contains("summer of 1964"), "Start page with the name")
	_ui._on_meta_clicked("reveal:sign")
	await _frames(2)
	_check(_body.text.contains("res://assets/images/route70.svg"), "road-sign footnote shows the bundled image")
	_check(_ui._backdrop.visible, "title art behind the opening page")
	await _shot("02_start_page")

	# --- Side trips: linguistics (dead end in Twine, Back here), journal, poem
	await _press("What the heck is linguistics")
	_check(_body.text.contains("natural languages are structured"), "What is linguistics page")
	await _press("Back")
	_check(_body.text.contains("summer of 1964"), "Back returns to Start")
	await _press("Open field journal")
	_check(_body.text.contains("no data to record"), "empty field journal")
	await _press("Read scribbles")
	_check(_body.text.contains("And I John"), "Harold's poem")
	await _shot("03_poem")
	await _press("Continue")
	await create_timer(1.1).timeout   # wipe to black and back
	_check(not _ui.visible and not game_state.in_dialogue, "Continue drops the player into Carbonear")

	# --- Third-person world
	await _physics(5)
	_check(player.is_on_floor(), "player standing on the road")
	var cam: Camera3D = player.get_node("CameraPivot/SpringArm3D/Camera3D")
	_check(cam.global_position.distance_to(player.global_position) > 2.5, "camera sits behind Harold (third person)")
	await _shot("04_third_person")
	player.global_position = Vector3(6.2, 0.1, 10.1)
	await _physics(10)
	var npc: Node = player.interactable
	_check(npc != null, "gardener in range")
	await _shot("04b_approach")

	# --- The conversation
	npc.interact(player)
	await _frames(3)
	_check(_ui._voice.is_playing() and npc._talking, "greeting voice plays from the gardener")
	_check(_body.text.contains("'ow's she gon', by"), "greeting")
	_check(_ui._portrait.visible and _ui._portrait.texture.resource_path.ends_with("man_neutral.png"), "gardener's portrait in the conversation bar")
	_check(player.interactable == null, "talk prompt cleared once the conversation starts")
	await create_timer(0.8).timeout
	_check(player.get_node("CameraPivot/SpringArm3D").spring_length < 3.6, "camera eases into an over-the-shoulder shot")
	await _shot("05_greeting")
	await _press("Long Branch")
	_check(game_state.get_var("accent") == "Long Branch", "$accent = Long Branch")
	_check(_body.text.contains("young fella from down Long Branch"), "accent reaction")
	await _press("Next")
	_check(_body.text.contains("We loves ya"), "Carbonear 03")
	await _press("Ask a question")
	_check(game_state.get_var("ethics") == true, "$ethics = true (consent route)")
	_check(_body.text.contains("By da jeezuz"), "survey explanation")
	_check(_ui._portrait.texture.resource_path.ends_with("man_laughing.png"), "he laughs at 'By da jeezuz'")
	await _press("Next")
	_check(_body.text.contains("informed consent"), "consent obtained before the question")
	var dragonfly: Node3D = main.get_node("Dragonfly")
	await _frames(10)
	_check(dragonfly.visible, "dragonfly flies between Harold and the man")
	await create_timer(1.2).timeout
	await _shot("06_dragonfly")
	_ui._on_meta_clicked("reveal:insect")
	await _frames(2)
	_check(_body.text.contains("dragonfly.jpg"), "insect footnote shows the dragonfly photo")
	await _press("Next")
	_check(_body.text.contains("'ORSE-STINGER"), "the elicited variant")
	await _press("Look at field journal")

	# --- Ending
	_check(_body.text.contains("The End") and _body.text.contains("Long Branch accent"), "end screen names the accent")
	_check(_body.text.contains("GOOD work") and _body.text.contains("'orse-stinger"), "feedback: consent + recorded variant")
	_check(_ui._backdrop.visible and _ui._backdrop.texture.resource_path.ends_with("ending.png"), "sunset journal-writing art behind the end screen")
	await _shot("07_end_screen")
	await _press("Credits")
	_check(_body.text.contains("Paddock, H. J. (1966)"), "credits with the Paddock citation")
	_check(_ui._buttons.any(func(b: Button) -> bool: return b.text.contains("Play again")), "Play again offered")
	await _shot("08_credits")

	print("\n%s (%d failures)" % ["EPISODE TEST PASSED" if _failures == 0 else "EPISODE TEST FAILED", _failures])
	main.queue_free()
	await _frames(2)
	quit(1 if _failures > 0 else 0)


## Presses the first enabled choice whose text contains `fragment`.
func _press(fragment: String) -> void:
	for b: Button in _ui._buttons:
		if b.text.contains(fragment) and not b.disabled:
			b.pressed.emit()
			await _frames(3)
			return
	_check(false, "button '%s' exists (have: %s)" % [fragment, ", ".join(_ui._buttons.map(func(x: Button) -> String: return x.text))])


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _physics(n: int) -> void:
	for i in n:
		await physics_frame


func _shot(shot_name: String) -> void:
	if DisplayServer.get_name() == "headless":
		return
	if _ui != null and _ui.visible:
		_ui._finish_reveal()   # capture the finished page, not the typewriter mid-stroke
	await _frames(6)
	DirAccess.make_dir_recursive_absolute("user://screenshots")
	var path := "user://screenshots/%s.png" % shot_name
	root.get_viewport().get_texture().get_image().save_png(path)
	print("  saved ", ProjectSettings.globalize_path(path))


func _check(ok: bool, what: String) -> void:
	print("  ", "ok   " if ok else "FAIL ", " ", what)
	if not ok:
		_failures += 1
