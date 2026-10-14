class_name DialogueRunner
extends RefCounted
## Plays passages from dialogue/story.json. Pure logic with no UI, so it can be unit tested.
##
## GODOT CONCEPT - RefCounted: a plain object freed automatically when nothing references
## it (like a normal Python object). Nodes, by contrast, live in the scene tree.
## `class_name` registers the script as a global type, so other scripts can write
## `DialogueRunner.new(...)`.
##
## How each Harlowe macro maps onto a block in story.json:
##   (set: $x to v)            "set"     -> state.set_var(x, v), applied in reading order
##   (if:)[...] (else:)[...]   "if"      -> evaluate "cond", run "then" or "else"
##   (go-to: "P")              "goto"    -> abandon this passage and run P instead
##   [[Text|Target]]           "choice"  -> a button the player can press
##   [x]<id| + (click-append:) "reveal"  -> clickable inline footnote
##   (align:)+(box:)[...]      "style"   -> centred block (the poem)
##   (prompt: ...)             "prompt"  -> returned to the UI to ask the player (Phase 2)
##   $var / (current-date:)    {var} / {current_date} placeholders in "text"
##   (spoken lines)            "voice"   -> added by tools/voice_lines.py; queued for audio playback

const MAX_GOTO_HOPS := 32

var _story: Dictionary
## Anything with get_var(name, default) and set_var(name, value), normally the GameState autoload.
var _state: Object
## Optional map of Twine image URL -> {"path": res://..., "width": px} for bundled copies.
var images: Dictionary = {}
var _var_re := RegEx.create_from_string("\\{(\\w+)\\}")


func _init(story: Dictionary, state: Object) -> void:
	_story = story
	_state = state


func has_passage(passage_name: String) -> bool:
	return (_story.get("passages", {}) as Dictionary).has(passage_name)


## Runs a passage: applies its (set:)s, follows any (go-to:), and returns what to show:
## {
##   "passage": String,          # name of the passage actually displayed (after go-tos)
##   "bbcode":  String,          # body text for a RichTextLabel; reveals appear as {{reveal:id}}
##   "reveals": {id: {"label": String, "bbcode": String}},
##   "choices": [{"text": String, "target": String}],
##   "prompts": [{"var": String, "text": String, "default": String}],
##   "voice":   [{"id": String, "speaker": String, "text": String}],  # in speaking order
## }
## Voice lines from passages left by (go-to:) are kept, so a router passage can speak first.
func enter(passage_name: String) -> Dictionary:
	var current := passage_name
	var carried_voice: Array = []
	for _hop in MAX_GOTO_HOPS:
		if not has_passage(current):
			push_error("DialogueRunner: no passage named '%s'" % current)
			return _new_output(current, "[i]Missing passage: %s[/i]" % current)
		var out := _new_output(current)
		var finished := _exec(_story["passages"][current]["blocks"], out)
		if finished:
			out["bbcode"] = (out["bbcode"] as String).strip_edges()
			out["voice"] = carried_voice + out["voice"]
			out.erase("goto")
			return out
		carried_voice.append_array(out["voice"])
		current = out["goto"]  # (go-to:) fired: like Harlowe, discard this passage's output
	push_error("DialogueRunner: more than %d go-to hops, probably a loop" % MAX_GOTO_HOPS)
	return _new_output(current, "[i]Story loop detected.[/i]")


func _new_output(passage_name: String, bbcode := "") -> Dictionary:
	return {"passage": passage_name, "bbcode": bbcode, "reveals": {}, "choices": [], "prompts": [], "voice": [], "goto": ""}


## Executes blocks in order. Returns false if a (go-to:) aborted the passage.
func _exec(blocks: Array, out: Dictionary) -> bool:
	for block: Dictionary in blocks:
		match block["type"]:
			"text":
				out["bbcode"] += interpolate(block["text"])
			"set":
				_state.set_var(block["var"], _resolve(block["value"]))
			"if":
				var branch: Array = block["then"] if eval_condition(block["cond"]) else block.get("else", [])
				if not _exec(branch, out):
					return false
			"goto":
				out["goto"] = block["target"]
				return false
			"choice":
				out["choices"].append({"text": interpolate(block["text"]), "target": block["target"]})
			"reveal":
				# Rendered up front and hidden by the UI until clicked. Fine while reveals only hold
				# text and images; a reveal containing (set:) would need deferred execution.
				var inner := _new_output(out["passage"])
				_exec(block["content"], inner)
				out["reveals"][block["id"]] = {"label": interpolate(block.get("label", "")), "bbcode": inner["bbcode"]}
				out["bbcode"] += "{{reveal:%s}}" % block["id"]
			"style":
				var inner := _new_output(out["passage"])
				_exec(block["content"], inner)
				out["bbcode"] += "[center]%s[/center]" % (inner["bbcode"] as String).strip_edges()
			"image":
				var local: Dictionary = images.get(block["src"], {})
				if not local.is_empty() and ResourceLoader.exists(local["path"]):
					out["bbcode"] += "
[center][img=%d]%s[/img][/center]
" % [int(local.get("width", 320)), local["path"]]
				else:
					out["bbcode"] += "[color=#7a6a55][i](picture: %s)[/i][/color]" % (block["src"] as String).get_file()
			"prompt":
				out["prompts"].append(block)
			"voice":
				for line: Dictionary in block["lines"]:
					if not line.get("skip", false):
						out["voice"].append(line)
			_:
				push_warning("DialogueRunner: unsupported block type '%s'" % block["type"])
	return true


func eval_condition(cond: Dictionary) -> bool:
	if cond.has("not"):
		return not eval_condition(cond["not"])
	for clause: Dictionary in cond.get("all", []):
		if not _eval_clause(clause):
			return false
	return true


func _eval_clause(clause: Dictionary) -> bool:
	if not clause.has("var"):
		push_warning("DialogueRunner: unparsed condition %s" % clause)
		return false
	var left: Variant = _state.get_var(clause["var"], 0)  # Harlowe treats unset variables as 0
	var right: Variant = _resolve(clause["value"])
	match clause["op"]:
		"is":
			return _same(left, right)
		"is_not":
			return not _same(left, right)
		"contains":
			if left is String:
				return (left as String).contains(str(right))
			if left is Array:
				return right in left
			return false
	push_warning("DialogueRunner: unknown operator '%s'" % clause["op"])
	return false


## Equality that never errors on mismatched types (GDScript's == does for e.g. String vs bool).
static func _same(a: Variant, b: Variant) -> bool:
	var numeric := [TYPE_INT, TYPE_FLOAT]
	if typeof(a) in numeric and typeof(b) in numeric:
		return is_equal_approx(float(a), float(b))
	return typeof(a) == typeof(b) and a == b


## A value may be a literal or a reference like {"var": "accent"}.
func _resolve(value: Variant) -> Variant:
	if value is Dictionary and (value as Dictionary).has("var"):
		return _state.get_var(value["var"], 0)
	return value


## Replaces {name} with the variable's current value and {current_date} with today's date.
func interpolate(text: String) -> String:
	var result := text.replace("{current_date}", Time.get_date_string_from_system())
	var matches := _var_re.search_all(result)
	matches.reverse()  # replace right-to-left so earlier offsets stay valid
	for m in matches:
		var value: Variant = _state.get_var(m.get_string(1))
		if value != null:
			result = result.substr(0, m.get_start()) + str(value) + result.substr(m.get_end())
	return result
