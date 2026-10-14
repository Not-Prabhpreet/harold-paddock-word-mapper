class_name ScreenFade
extends ColorRect
## A full-screen wipe used between the title, the journal pages and the 3D world, so the episode
## never hard-cuts. Sits on top of every other UI node in the CanvasLayer.

const DEFAULT := 0.45


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	color.a = 1.0
	visible = true


## Fades from black to clear. Awaitable.
func fade_in(duration := DEFAULT) -> void:
	await _to(0.0, duration)
	visible = false


## Fades to black. Awaitable, so callers can swap the scene while it is covered.
func fade_out(duration := DEFAULT) -> void:
	visible = true
	await _to(1.0, duration)


## Fades out, runs `midpoint`, then fades back in.
func wipe(midpoint: Callable, duration := DEFAULT) -> void:
	await fade_out(duration * 0.5)
	midpoint.call()
	await fade_in(duration)


func _to(alpha: float, duration: float) -> void:
	var tween := create_tween()
	tween.tween_property(self, "color:a", alpha, duration).set_trans(Tween.TRANS_SINE)
	await tween.finished
