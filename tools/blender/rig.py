"""
Armature and animation helpers for the character scripts.

A character is built as one joined mesh, then:
    skeleton = build_armature(SKELETON, joints)   # bones from named joint positions
    bind(mesh, skeleton)                          # automatic (bone-heat) weights
    clip(skeleton, "idle", 96, {...})             # one glTF animation per call

Animations are authored as per-bone keyframes in degrees, which keeps the character scripts
readable: {"head": [(0, (0, 0, 0)), (48, (6, 0, 0))]} tilts the head forward over two seconds.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Euler, Vector

FPS = 24

# (bone, parent, start joint, end joint). Joint names are looked up in the character's dict.
SKELETON = [
    ("hips", None, "hip", "waist"),
    ("spine", "hips", "waist", "chest"),
    ("chest", "spine", "chest", "neck"),
    ("neck", "chest", "neck", "chin"),
    ("head", "neck", "chin", "skull"),
    ("shoulder.L", "chest", "neck", "shoulder"),
    ("upperarm.L", "shoulder.L", "shoulder", "elbow"),
    ("forearm.L", "upperarm.L", "elbow", "wrist"),
    ("hand.L", "forearm.L", "wrist", "fingers"),
    ("thigh.L", "hips", "hip_joint", "knee"),
    ("shin.L", "thigh.L", "knee", "ankle"),
    ("foot.L", "shin.L", "ankle", "toe"),
]


def mirrored(v: Vector) -> Vector:
    return Vector((-v.x, v.y, v.z))


def build_armature(joints: dict[str, Vector], name: str = "Armature") -> bpy.types.Object:
    """Create the skeleton from named joint positions. Left-side bones are mirrored to .R."""
    data = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")

    def add(bone_name, parent_name, head, tail):
        b = data.edit_bones.new(bone_name)
        b.head = head
        b.tail = tail
        b.use_connect = False
        if parent_name:
            b.parent = data.edit_bones[parent_name]
        return b

    for bone, parent, j0, j1 in SKELETON:
        add(bone, parent, joints[j0], joints[j1])
    for bone, parent, j0, j1 in SKELETON:
        if not bone.endswith(".L"):
            continue
        add(bone[:-2] + ".R", (parent[:-2] + ".R") if parent and parent.endswith(".L") else parent,
            mirrored(joints[j0]), mirrored(joints[j1]))

    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in obj.pose.bones:
        pb.rotation_mode = "XYZ"
    return obj


def bind(mesh: bpy.types.Object, skeleton: bpy.types.Object, smooth_passes: int = 8) -> None:
    """Skin the mesh to the skeleton with distance-based weights.

    Blender's bone-heat weighting needs a clean manifold mesh, which a character assembled from
    many separate parts is not, so weights are computed directly: every vertex is bound to the
    two nearest bone segments, then the weights are relaxed across mesh edges so joints bend
    smoothly instead of creasing.
    """
    bones = [(b.name, Vector(b.head_local), Vector(b.tail_local)) for b in skeleton.data.bones]
    verts = mesh.data.vertices
    weights: list[dict[str, float]] = []

    for v in verts:
        p = mesh.matrix_world @ v.co
        dists = sorted(((_point_segment_distance(p, h, t), name) for name, h, t in bones))
        near = dists[:2]
        if near[1][0] > near[0][0] * 2.5:          # clearly one bone's territory
            near = near[:1]
        raw = {name: 1.0 / (d + 1e-4) ** 3 for d, name in near}
        total = sum(raw.values())
        weights.append({k: w / total for k, w in raw.items()})

    neighbours: list[list[int]] = [[] for _ in verts]
    for e in mesh.data.edges:
        a, b = e.vertices
        neighbours[a].append(b)
        neighbours[b].append(a)
    for _ in range(smooth_passes):
        blended = []
        for i, w in enumerate(weights):
            acc: dict[str, float] = {}
            for src in [w] + [weights[j] for j in neighbours[i]]:
                for k, val in src.items():
                    acc[k] = acc.get(k, 0.0) + val
            total = sum(acc.values())
            blended.append({k: val / total for k, val in acc.items() if val / total > 0.01})
        weights = blended

    for name, _, _ in bones:
        mesh.vertex_groups.new(name=name)
    for i, w in enumerate(weights):
        total = sum(w.values())
        for name, value in w.items():
            mesh.vertex_groups[name].add([i], value / total, "REPLACE")

    mesh.parent = skeleton
    mesh.matrix_parent_inverse = skeleton.matrix_world.inverted()
    mod = mesh.modifiers.new("Armature", "ARMATURE")
    mod.object = skeleton


def _point_segment_distance(p: Vector, a: Vector, b: Vector) -> float:
    ab = b - a
    denom = ab.dot(ab)
    t = 0.0 if denom < 1e-9 else max(0.0, min(1.0, (p - a).dot(ab) / denom))
    return (p - (a + ab * t)).length


# --------------------------------------------------------------------------- animation
def clip(skeleton: bpy.types.Object, name: str, frames: int, tracks: dict, loop: bool = True) -> None:
    """Author one animation.

    tracks maps a bone name to a list of keys. A key is (frame, (rx, ry, rz)) in degrees, or
    (frame, (rx, ry, rz), (dx, dy, dz)) to also move the bone. With `loop`, the first key is
    repeated at the end so the cycle closes seamlessly.
    """
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    if skeleton.animation_data is None:
        skeleton.animation_data_create()
    skeleton.animation_data.action = action

    for bone_name, keys in tracks.items():
        pb = skeleton.pose.bones[bone_name]
        keys = list(keys)
        if loop and keys[0][0] == 0 and keys[-1][0] != frames:
            keys.append((frames, *keys[0][1:]))
        for key in keys:
            frame, rot = key[0], key[1]
            loc = key[2] if len(key) > 2 else None
            pb.rotation_euler = Euler([math.radians(a) for a in rot], "XYZ")
            pb.keyframe_insert("rotation_euler", frame=frame, group=bone_name)
            if loc is not None:
                pb.location = Vector(loc)
                pb.keyframe_insert("location", frame=frame, group=bone_name)

    for fcurve in _fcurves(action):
        for kp in fcurve.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "AUTO"
        fcurve.update()
    # Reset the pose so the next clip starts from rest.
    for pb in skeleton.pose.bones:
        pb.rotation_euler = Euler((0, 0, 0), "XYZ")
        pb.location = Vector((0, 0, 0))


def _fcurves(action):
    """Blender 5 moved an action's curves into layers and slots; 4.x kept them on the action."""
    if hasattr(action, "fcurves") and len(getattr(action, "fcurves", [])):
        return list(action.fcurves)
    curves = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for slot in action.slots:
                bag = strip.channelbag(slot)
                if bag is not None:
                    curves.extend(bag.fcurves)
    return curves


def breathe(bone: str, frames: int, amount: float = 1.2, phase: float = 0.0) -> list:
    """A slow in-out cycle on one axis, for idle breathing and sway."""
    q = frames // 4
    return [(0, (amount * math.sin(phase), 0, 0)),
            (q, (amount * math.sin(phase + math.pi / 2), 0, 0)),
            (2 * q, (amount * math.sin(phase + math.pi), 0, 0)),
            (3 * q, (amount * math.sin(phase + 3 * math.pi / 2), 0, 0))]
