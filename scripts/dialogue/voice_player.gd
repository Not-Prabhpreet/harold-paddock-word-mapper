class_name VoicePlayer
extends Node
## Plays a passage's voice lines one after another from res://voice/audio/<line id>.mp3.
## Lines without an audio file are skipped silently, so the game works before any voices exist.
##
## Each speaker can have its own player: NPCs register an AudioStreamPlayer3D so their voice
## comes from where they stand. Everyone else (Harold, narration) uses a plain 2D player.

signal line_started(line: Dictionary)
signal line_finished(line: Dictionary)

const GAP_SECONDS := 0.25

## Where generated lines live. Tests point this at a fixture folder.
var audio_dir := "res://voice/audio/"

var _speakers: Dictionary = {}  # speaker name -> AudioStreamPlayer or AudioStreamPlayer3D
var _default: AudioStreamPlayer
var _queue: Array = []
var _current: Dictionary = {}
var _current_player: Node = null
var _generation := 0  # bumps on stop() so stale "finished" callbacks are ignored


func _ready() -> void:
	_default = AudioStreamPlayer.new()
	_default.bus = &"Master"
	add_child(_default)
	_default.finished.connect(_on_finished)


func register_speaker(speaker: String, player: Node) -> void:
	if _speakers.get(speaker) == player:
		return
	_speakers[speaker] = player
	if not player.finished.is_connected(_on_finished):
		player.finished.connect(_on_finished)


func has_audio(line_id: String) -> bool:
	var path := audio_dir + line_id + ".mp3"
	return ResourceLoader.exists(path) or FileAccess.file_exists(path)


## Imported resource if Godot has imported it; otherwise read the raw file, so lines generated
## while the editor is open play straight away. (Exported builds always use the imported copy.)
func _load_stream(line_id: String) -> AudioStream:
	var path := audio_dir + line_id + ".mp3"
	if ResourceLoader.exists(path):
		return load(path)
	return AudioStreamMP3.load_from_file(path)


func play_lines(lines: Array) -> void:
	stop()
	for line: Dictionary in lines:
		if has_audio(line["id"]):
			_queue.append(line)
	_play_next()


func stop() -> void:
	_generation += 1
	_queue.clear()
	if _current_player != null:
		_current_player.stop()
	if not _current.is_empty():
		line_finished.emit(_current)
	_current = {}
	_current_player = null


func is_playing() -> bool:
	return not _current.is_empty()


func _play_next() -> void:
	if _queue.is_empty():
		return
	_current = _queue.pop_front()
	_current_player = _speakers.get(_current["speaker"], _default)
	_current_player.stream = _load_stream(_current["id"])
	_current_player.play()
	line_started.emit(_current)


func _on_finished() -> void:
	if _current.is_empty():
		return
	var gen := _generation
	line_finished.emit(_current)
	_current = {}
	_current_player = null
	await get_tree().create_timer(GAP_SECONDS).timeout
	if gen == _generation:
		_play_next()
