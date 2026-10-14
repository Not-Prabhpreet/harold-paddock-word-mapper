extends SceneTree
## Tests that generated assets replace placeholders, using small fixture files.
##   Godot_..._console.exe --headless --path . -s res://tests/test_assets.gd

const ModelSlotScript := preload("res://scripts/props/model_slot.gd")

var _failures := 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	# ModelSlot: placeholder hidden, model added, scaled, given collision
	var slot: Node3D = ModelSlotScript.new()
	var placeholder := CSGBox3D.new()
	placeholder.use_collision = true
	slot.add_child(placeholder)
	slot.model_path = "res://tests/fixtures/model.glb"
	slot.fit_height = 4.4
	root.add_child(slot)
	await process_frame
	_check(slot.model != null, "ModelSlot loaded the .glb")
	_check(not placeholder.visible and not placeholder.use_collision, "placeholder hidden, no collision")
	var height: float = ModelSlotScript._bounds(slot.model).size.y * slot.model.scale.y
	_check(absf(height - 4.4) < 0.05, "model scaled to fit_height (%.2f m)" % height)
	_check(not slot.model.find_children("*", "StaticBody3D", true, false).is_empty(), "collision generated")

	# ModelSlot with no file yet keeps the placeholder
	var empty: Node3D = ModelSlotScript.new()
	var keep := CSGBox3D.new()
	empty.add_child(keep)
	empty.model_path = "res://assets/props/does_not_exist/model.glb"
	root.add_child(empty)
	await process_frame
	_check(empty.model == null and keep.visible, "missing model keeps the placeholder")

	# NPC: model from asset_dir replaces the CSG body
	var npc: Node3D = (load("res://scenes/npc.tscn") as PackedScene).instantiate()
	npc.asset_dir = "res://tests/fixtures/npc"
	root.add_child(npc)
	await process_frame
	_check(npc.has_node("CharacterModel/Model"), "NPC loaded model.glb from asset_dir")
	_check(not (npc.get_node("Body") as CSGShape3D).visible, "NPC placeholder hidden")
	_check(npc.voice is AudioStreamPlayer3D, "NPC has a positional voice player")

	print("\n%s (%d failures)" % ["ASSET TEST PASSED" if _failures == 0 else "ASSET TEST FAILED", _failures])
	for n in [slot, empty, npc]:
		n.queue_free()
	await process_frame
	quit(1 if _failures > 0 else 0)


func _check(ok: bool, what: String) -> void:
	print("  ", "ok   " if ok else "FAIL ", " ", what)
	if not ok:
		_failures += 1
