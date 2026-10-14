class_name Dragonfly
extends ModelSlot
## The 'orse-stinger. Hidden until a passage's "dragonfly_flyby" event, then it darts in,
## passes right between Harold and the man ("flies right between Harold and the man"),
## circles once and leaves. Uses assets/props/dragonfly/model.glb, built in Blender.

@export var flight_seconds := 4.5

var _wings: Array[Node3D] = []
var _flap := 0.0
var _tween: Tween


func _ready() -> void:
	super._ready()
	visible = false
	for child in get_children():
		if child.name.begins_with("Wing"):
			_wings.append(child)


func fly_between(a: Vector3, b: Vector3) -> void:
	var mid := (a + b) * 0.5
	mid.y = 1.6
	var across := (b - a)
	across.y = 0.0
	across = across.normalized()
	var side := across.cross(Vector3.UP).normalized()  # perpendicular to the line between them
	var points: Array[Vector3] = [
		mid + side * 5.0 + Vector3(0, 1.2, 0),
		mid + side * 1.2 + Vector3(0, 0.2, 0),
		mid,
		mid - side * 0.9 + across * 0.6 + Vector3(0, 0.15, 0),
		mid - side * 0.4 - across * 0.7,
		mid + side * 0.3,
		mid - side * 6.0 + Vector3(0, 1.8, 0),
	]
	global_position = points[0]
	visible = true
	if _tween != null:
		_tween.kill()
	_tween = create_tween()
	var leg := flight_seconds / float(points.size() - 1)
	for i in range(1, points.size()):
		_tween.tween_callback(_face.bind(points[i]))
		_tween.tween_property(self, "global_position", points[i], leg).set_trans(Tween.TRANS_SINE)
	_tween.tween_callback(func() -> void: visible = false)


func _face(target: Vector3) -> void:
	if global_position.distance_to(target) > 0.01:
		look_at(target, Vector3.UP)


func _process(delta: float) -> void:
	if not visible:
		return
	_flap += delta * 60.0
	if model != null:
		# The modelled wings are static: a quick wobble and bob reads as hovering flight.
		model.rotation.z = sin(_flap * 0.35) * 0.12
		model.position.y = sin(_flap * 0.2) * 0.01
		return
	for i in _wings.size():
		_wings[i].rotation.z = sin(_flap + i) * 0.5 * (1.0 if i % 2 == 0 else -1.0)
