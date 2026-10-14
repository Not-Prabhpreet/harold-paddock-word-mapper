extends SceneTree
## Writes test fixtures: a small two-box .glb standing in for a real model.
##   Godot_..._console.exe --headless --path . -s res://tests/make_fixtures.gd
## Then run --import once so Godot imports it.


func _initialize() -> void:
	var root := Node3D.new()
	root.name = "FixtureModel"
	var body := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(1, 2, 1)
	body.mesh = box
	body.position.y = 1.0
	root.add_child(body)
	body.owner = root
	var top := MeshInstance3D.new()
	var cap := BoxMesh.new()
	cap.size = Vector3(1.2, 0.2, 1.2)
	top.mesh = cap
	top.position.y = 2.1
	root.add_child(top)
	top.owner = root

	DirAccess.make_dir_recursive_absolute("res://tests/fixtures/npc")
	for path in ["res://tests/fixtures/model.glb", "res://tests/fixtures/npc/model.glb"]:
		var doc := GLTFDocument.new()
		var state := GLTFState.new()
		var err := doc.append_from_scene(root, state)
		if err == OK:
			err = doc.write_to_filesystem(state, path)
		print("%s: %s" % [path, error_string(err)])
	root.free()
	quit()
