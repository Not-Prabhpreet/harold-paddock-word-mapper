extends SceneTree
## Headless tests for the dialogue runner against the real dialogue/story.json.
## Run from the project folder:
##   Godot_v4.7.2-stable_win64_console.exe --headless --path . -s res://tests/test_dialogue.gd
##
## GODOT CONCEPT - `-s script` runs a script that extends SceneTree (or MainLoop) instead of
## the main scene: Godot's equivalent of `python some_script.py`.

const Runner := preload("res://scripts/dialogue/dialogue_runner.gd")
const StateScript := preload("res://scripts/autoload/game_state.gd")
const StoryScript := preload("res://scripts/autoload/story.gd")

var _failures := 0
var _story: Dictionary


func _init() -> void:
	_story = StoryScript.load_story("res://dialogue/story.json")
	_check(_story.get("passages", {}).size() == 19, "story.json has 19 passages")

	_test_accent_branch("in the local accent", "Local", "encyclopedias")
	_test_accent_branch("in his Long Branch vernacular", "Long Branch", "young fella from down Long Branch")
	_test_accent_branch("in a St. John's standard accent", "St. John's Standard", "townie")
	_test_full_paths()

	print("\n%s (%d failure%s)" % ["ALL TESTS PASSED" if _failures == 0 else "TESTS FAILED", _failures, "" if _failures == 1 else "s"])
	quit(1 if _failures > 0 else 0)


func _new_state() -> Node:
	var state: Node = StateScript.new()
	state.reset((_story["variables"] as Dictionary).duplicate(true))
	state.set_var("name", "Tester")
	return state


## The opening exchange: greeting, accent choice, reaction, then Carbonear 03.
func _test_accent_branch(choice_text: String, expected_accent: String, expected_phrase: String) -> void:
	var state := _new_state()
	var runner = Runner.new(_story, state)

	var greet: Dictionary = runner.enter("Carbonear 02")
	_check(greet["bbcode"].contains("'ow's she gon', by"), "greeting keeps the NL voice")
	_check(greet["choices"].size() == 3, "three accent choices")

	var target := ""
	for c: Dictionary in greet["choices"]:
		if c["text"] == choice_text:
			target = c["target"]
	_check(target != "", "choice '%s' exists" % choice_text)

	var reply: Dictionary = runner.enter(target)
	_check(reply["passage"] == "Reply", "(go-to:) lands on Reply for %s" % expected_accent)
	_check(state.get_var("accent") == expected_accent, "$accent == %s" % expected_accent)
	_check(reply["bbcode"].contains(expected_phrase), "reaction mentions '%s'" % expected_phrase)
	_check(reply["choices"].size() == 1 and reply["choices"][0]["target"] == "Carbonear 03", "exactly one Next to Carbonear 03")
	var speakers: Array = reply["voice"].map(func(l: Dictionary) -> String: return l["speaker"])
	_check(speakers.size() >= 2 and speakers[0].begins_with("harold") and "man" in speakers, "voice: Harold's reply, then the man (%s)" % ", ".join(speakers))
	if expected_accent == "Local":
		_check(reply["bbcode"].contains("By the way, Tester,"), "{name} is interpolated")
	state.free()

	var fresh := _new_state()
	var after: Dictionary = Runner.new(_story, fresh).enter("Carbonear 03")
	fresh.free()
	_check(after["bbcode"].contains("We loves ya just the same"), "Carbonear 03 text")


## Every route through the episode, checking the end-of-journal feedback (Phase 2 preview).
func _test_full_paths() -> void:
	for ethics_choice in ["Ask a question from Harold's dialect survey", "Talk about the weather a bit"]:
		for record in [true, false]:
			var state := _new_state()
			var runner = Runner.new(_story, state)
			runner.enter("Start")
			runner.enter("Carbonear 02")
			runner.enter("in his Long Branch vernacular")
			runner.enter("Carbonear 03")
			runner.enter(ethics_choice)
			var q: Dictionary = runner.enter("Question")
			if ethics_choice.begins_with("Ask"):
				_check(q["reveals"].has("insect"), "Question passage has the insect reveal")
			runner.enter("DragonflyVariant")
			if not record:
				runner.enter("Carbonear End")
			var journal: Dictionary = runner.enter("Field Journal")
			var text: String = journal["bbcode"]
			var ethics: bool = ethics_choice.begins_with("Ask")
			var label := "ethics=%s lexicon=%s" % [ethics, record]
			_check(state.get_var("ethics") == ethics and state.get_var("lexicon") == record, "%s: variables" % label)
			_check(text.contains("The End"), "%s: end screen shown" % label)
			_check(text.contains("GOOD work") == ethics, "%s: consent feedback" % label)
			_check(text.contains("'orse-stinger") == record, "%s: dragonfly recorded" % label)
			_check(journal["choices"].size() == 1 and journal["choices"][0]["target"] == "Credits", "%s: Credits link" % label)
			state.free()


func _check(ok: bool, what: String) -> void:
	if ok:
		print("  ok    ", what)
	else:
		_failures += 1
		print("  FAIL  ", what)
