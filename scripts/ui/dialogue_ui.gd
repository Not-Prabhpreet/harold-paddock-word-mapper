extends Control
## Shows passages from the story in one of two layouts:
## - "conversation": a parchment bar along the bottom while Harold talks to someone in 3D;
## - "page": a full journal page (the opening, the field journal, the poem, the ending, credits).
## Which passages are pages is set in dialogue/presentation.json, not here.
##
## GODOT CONCEPTS
## - Control nodes are Godot's UI widgets. Containers (VBoxContainer, PanelContainer)
##   lay out their children automatically, a bit like CSS flexbox.
## - RichTextLabel renders BBCode ([i], [b], [img], [url=...]). Clicking a [url] fires
##   `meta_clicked`, which we use for Twine's clickable inline footnotes.
## - `%Body` fetches the child marked "unique name in owner" in the scene.

signal conversation_started(npc: Node3D)
signal dialogue_finished
## Fired for every passage shown, with its event name from presentation.json ("" if none).
signal passage_shown(passage: String, event: String)

const LINK_COLOR := "#8b0000"  # crimson ink, from the prototype's stylesheet
const LINK_HOVER_COLOR := Color("#ff4500")
const REVEAL_COLOR := "#5c4033"
const CONVERSATION_ANCHORS := [0.08, 0.5, 0.92, 0.97]  # left, top, right, bottom
const PAGE_ANCHORS := [0.2, 0.05, 0.8, 0.95]

@onready var _panel: PanelContainer = $Panel
@onready var _dim: ColorRect = $Dim
@onready var _backdrop: TextureRect = $Backdrop
@onready var _portrait: TextureRect = %Portrait
@onready var _portrait_box: VBoxContainer = %PortraitBox
@onready var _caption: Label = %Caption
@onready var _fade: ScreenFade = get_tree().get_first_node_in_group("screen_fade")
@onready var _body: RichTextLabel = %Body
@onready var _choices: VBoxContainer = %Choices

var _runner: DialogueRunner
var _end_passage := ""
var _current: Dictionary = {}
var _revealed: Dictionary = {}  # reveal id -> true once clicked
var _buttons: Array[Button] = []
var _history: Array[String] = []
var _voice: VoicePlayer
var _npc: Node3D = null
var _closable := false  # page opened from the world (journal key): offer "Close"
var _parchment_style: StyleBox
var _page_style: StyleBox
var _reveal_tween: Tween
var _fresh_passage := false


func _ready() -> void:
	visible = false
	_parchment_style = _panel.get_theme_stylebox("panel")
	_page_style = _make_page_style()
	_body.meta_clicked.connect(_on_meta_clicked)
	_voice = VoicePlayer.new()
	_voice.name = "VoicePlayer"
	add_child(_voice)
	_voice.line_started.connect(_on_line_started)
	_voice.line_finished.connect(_on_line_finished)


## Conversation with `npc` starting at `entry`. Reaching `end_passage` (optional) stops early.
func start(entry: String, end_passage := "", npc: Node3D = null) -> void:
	_end_passage = end_passage
	_npc = npc
	_closable = false
	if npc != null:
		_voice.register_speaker(npc.voice_speaker, npc.voice)
		conversation_started.emit(npc)
	_open(entry)


## A page outside any conversation: the opening screen, or the journal opened with J.
func open_page(passage: String, closable := false) -> void:
	_end_passage = ""
	_npc = null
	_closable = closable
	_open(passage)


func is_open() -> bool:
	return visible


func close_dialogue() -> void:
	_voice.stop()
	visible = false
	_backdrop.visible = false
	GameState.in_dialogue = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	dialogue_finished.emit()


func _open(passage: String) -> void:
	_runner = DialogueRunner.new(Story.data, GameState)
	_runner.images = Story.presentation.get("images", {})
	_history.clear()
	GameState.in_dialogue = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	visible = true
	_go(passage)


func _go(passage_name: String) -> void:
	# Leaving a page for the 3D world (e.g. "Continue down the highway"): wipe to black, drop the
	# player into Carbonear, wipe back.
	if _npc == null and Story.is_world(passage_name):
		if _fade != null:
			await _fade.fade_out(0.3)
			close_dialogue()
			await _fade.fade_in(0.45)
		else:
			close_dialogue()
		return
	if not _current.is_empty() and _current.get("passage", "") != passage_name:
		_history.append(_current["passage"])
	_current = _runner.enter(passage_name)
	_revealed.clear()
	_set_layout(Story.is_page(_current["passage"]))
	_update_backdrop()
	if _needs_prompt():
		_portrait_box.visible = false
		_show_prompt()
		return
	_fresh_passage = true
	_render()
	_body.scroll_to_line(0)
	_show_portrait(_first_speaker())
	_voice.play_lines(_current["voice"])
	var event: String = Story.presentation.get("events", {}).get(_current["passage"], "")
	passage_shown.emit(_current["passage"], event)


func _set_layout(page: bool) -> void:
	var a: Array = PAGE_ANCHORS if page else CONVERSATION_ANCHORS
	_panel.anchor_left = a[0]
	_panel.anchor_top = a[1]
	_panel.anchor_right = a[2]
	_panel.anchor_bottom = a[3]
	for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		_panel.set_offset(side, 0.0)
	_dim.visible = page
	_panel.add_theme_stylebox_override("panel", _page_style if page and _page_style != null else _parchment_style)


## The journal-page image as the paper behind page passages (falls back to plain parchment).
func _make_page_style() -> StyleBox:
	var path: String = Story.presentation.get("page_texture", "")
	if path == "" or not ResourceLoader.exists(path):
		return null
	var style := StyleBoxTexture.new()
	style.texture = load(path)
	style.content_margin_left = 64.0  # clear of the stitched binding on the left edge
	style.content_margin_right = 40.0
	style.content_margin_top = 34.0
	style.content_margin_bottom = 26.0
	return style


# --------------------------------------------------------------------------- art
## Full-screen picture behind a page, chosen by the first rule in presentation.json whose
## "if" variables all match (e.g. the sunset journal-writing art only if $lexicon is true).
func _update_backdrop() -> void:
	var rules: Array = Story.presentation.get("backdrops", {}).get(_current["passage"], [])
	for rule: Dictionary in rules:
		var ok := true
		for key: String in rule.get("if", {}):
			if not DialogueRunner._same(GameState.get_var(key), rule["if"][key]):
				ok = false
		if ok and ResourceLoader.exists(rule["image"]):
			_backdrop.texture = load(rule["image"])
			_backdrop.visible = true
			_dim.color.a = 0.25
			return
	_backdrop.visible = false
	_dim.color.a = 0.55


## Whose portrait to show before any voice line plays: the character presentation.json gives an
## expression for this passage (e.g. the laughing gardener), otherwise whoever speaks first.
func _first_speaker() -> String:
	var moods: Dictionary = Story.presentation.get("expressions", {}).get(_current.get("passage", ""), {})
	if not moods.is_empty():
		return moods.keys()[0]
	var lines: Array = _current.get("voice", [])
	return lines[0]["speaker"] if not lines.is_empty() else ""


## Shows `speaker`'s portrait with the expression set for this passage ("harold_local" -> harold).
func _show_portrait(speaker: String) -> void:
	var who := speaker.get_slice("_", 0)
	var faces: Dictionary = Story.presentation.get("portraits", {}).get(who, {})
	if faces.is_empty():
		_portrait_box.visible = false
		return
	var mood: String = Story.presentation.get("expressions", {}).get(_current.get("passage", ""), {}).get(who, "neutral")
	var path: String = faces.get(mood, faces.get("neutral", ""))
	_portrait_box.visible = path != "" and ResourceLoader.exists(path)
	if _portrait_box.visible:
		_portrait.texture = load(path)
		var names: Dictionary = Story.presentation.get("speaker_names", {})
		_caption.text = names.get(who, "")


# --------------------------------------------------------------------------- name prompt
func _needs_prompt() -> bool:
	for p: Dictionary in _current["prompts"]:
		if str(GameState.get_var(p["var"], "")) == "":
			return true
	return false


func _show_prompt() -> void:
	var prompt: Dictionary = _current["prompts"][0]
	_body.text = "\n\n[center][font_size=26]%s[/font_size][/center]" % prompt["text"]
	_clear_choices()
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var field := LineEdit.new()
	field.placeholder_text = "Your name"
	field.custom_minimum_size = Vector2(320, 44)
	field.add_theme_font_override("font", _body.get_theme_font("normal_font"))
	field.add_theme_font_size_override("font_size", 20)
	field.max_length = 40
	row.add_child(field)
	var begin := _style_button(Button.new())
	begin.text = "Begin"
	row.add_child(begin)
	_choices.add_child(row)
	var submit := func() -> void:
		var name_text := field.text.strip_edges()
		GameState.set_var(prompt["var"], name_text if name_text != "" else "friend")
		_current = {}
		_go(Story.data.get("start", "Start"))
	field.text_submitted.connect(func(_text: String) -> void: submit.call())
	begin.pressed.connect(submit)
	field.grab_focus.call_deferred()


# --------------------------------------------------------------------------- rendering
func _render() -> void:
	var text: String = _current["bbcode"]
	var notes: Dictionary = Story.presentation.get("reveal_notes", {})
	for id: String in _current["reveals"]:
		var reveal: Dictionary = _current["reveals"][id]
		var shown: String
		if _revealed.has(id):
			var note := ""
			if notes.has(id):
				note = "\n[center][font_size=15][i]%s[/i][/font_size][/center]\n" % notes[id]
			shown = "[u]%s[/u][color=%s]%s[/color]%s" % [reveal["label"], REVEAL_COLOR, reveal["bbcode"], note]
		else:
			shown = "[url=reveal:%s][color=%s][b]%s[/b][/color][/url]" % [id, LINK_COLOR, reveal["label"]]
		text = text.replace("{{reveal:%s}}" % id, shown)
	_body.text = text
	if _fresh_passage:
		_fresh_passage = false
		_start_reveal()
	else:
		_body.visible_ratio = 1.0
	_build_choices()


## Types the passage on like field notes being written. Any key or click finishes it at once.
func _start_reveal() -> void:
	if _reveal_tween != null:
		_reveal_tween.kill()
	var characters := _body.get_total_character_count()
	if characters <= 0:
		_body.visible_ratio = 1.0
		return
	_body.visible_ratio = 0.0
	_reveal_tween = create_tween()
	_reveal_tween.tween_property(_body, "visible_ratio", 1.0,
			clampf(float(characters) / 150.0, 0.2, 1.8))


func _revealing() -> bool:
	return _reveal_tween != null and _reveal_tween.is_running()


func _finish_reveal() -> void:
	if _reveal_tween != null:
		_reveal_tween.kill()
	_body.visible_ratio = 1.0


func _clear_choices() -> void:
	for child in _choices.get_children():
		child.queue_free()
	_buttons.clear()


func _build_choices() -> void:
	_clear_choices()
	var passage: String = _current["passage"]
	var stop_here := passage == _end_passage

	for choice: Dictionary in _current["choices"]:
		var button := _add_button(choice["text"])
		if stop_here:
			button.disabled = true
		else:
			button.pressed.connect(_go.bind(choice["target"]))

	if Story.is_final(passage):
		_add_button("Play again").pressed.connect(_play_again)
		_add_button("Quit").pressed.connect(func() -> void: get_tree().quit())
	elif stop_here:
		_add_button("Close").pressed.connect(close_dialogue)
	elif _current["choices"].is_empty() and not _history.is_empty():
		_add_button("Back").pressed.connect(_go_back)
	elif _current["choices"].is_empty():
		_add_button("Close").pressed.connect(close_dialogue)

	if _closable and not Story.is_final(passage):
		_add_button("Close journal").pressed.connect(close_dialogue)


func _play_again() -> void:
	if _fade != null:
		await _fade.fade_out(0.4)
	get_tree().reload_current_scene()


func _go_back() -> void:
	var previous: String = _history.pop_back()
	_current = {}
	_go(previous)


func _add_button(text: String) -> Button:
	var button := _style_button(Button.new())
	button.text = "%d. %s" % [_buttons.size() + 1, text]
	button.alignment = HORIZONTAL_ALIGNMENT_LEFT
	_choices.add_child(button)
	_buttons.append(button)
	return button


func _style_button(button: Button) -> Button:
	button.flat = true
	button.focus_mode = Control.FOCUS_NONE
	button.add_theme_font_override("font", _body.get_theme_font("bold_font"))
	button.add_theme_font_size_override("font_size", 19)
	button.add_theme_color_override("font_color", Color(LINK_COLOR))
	button.add_theme_color_override("font_hover_color", LINK_HOVER_COLOR)
	button.add_theme_color_override("font_pressed_color", LINK_HOVER_COLOR)
	button.add_theme_color_override("font_disabled_color", Color(0.45, 0.4, 0.35, 0.7))
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	return button


## Number keys 1-9 pick the matching choice.
func _unhandled_input(event: InputEvent) -> void:
	if not visible:
		return
	# While the text is still typing on, any press completes it instead of choosing.
	if _revealing() and ((event is InputEventKey and event.pressed and not event.echo)
			or (event is InputEventMouseButton and event.pressed)):
		get_viewport().set_input_as_handled()
		_finish_reveal()
		return
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	var index: int = (event as InputEventKey).keycode - KEY_1
	if index >= 0 and index < _buttons.size() and not _buttons[index].disabled:
		get_viewport().set_input_as_handled()
		_buttons[index].pressed.emit()


func _on_meta_clicked(meta: Variant) -> void:
	var key := str(meta)
	if key.begins_with("reveal:"):
		_revealed[key.trim_prefix("reveal:")] = true
		_render()


func _on_line_started(line: Dictionary) -> void:
	_show_portrait(line["speaker"])
	if _npc != null and line["speaker"] == _npc.voice_speaker:
		_npc.set_talking(true)


func _on_line_finished(line: Dictionary) -> void:
	if _npc != null and line["speaker"] == _npc.voice_speaker:
		_npc.set_talking(false)
