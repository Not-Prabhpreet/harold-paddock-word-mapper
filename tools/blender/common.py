"""
Shared helpers for the Blender asset scripts (run inside Blender, not plain Python).

Every asset script:
  1. calls reset() for an empty scene,
  2. builds meshes with box()/cyl()/prism() and materials with mat()/tex_mat(),
  3. calls export(name) -> assets/<category>/<name>/model.glb  (+ preview renders).

Coordinates: Blender is Z-up, metres. The front of every asset faces -Y (Blender's "front"
view), which the glTF exporter turns into +Z: the direction Godot scenes expect.
Textures are cropped straight from the concept art, so models match the painted style.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
TEX_DIR = ASSETS / "textures"


# --------------------------------------------------------------------------- scene
def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.objects):
        for block in list(coll):
            coll.remove(block)


def link(obj: bpy.types.Object) -> bpy.types.Object:
    bpy.context.scene.collection.objects.link(obj)
    return obj


# --------------------------------------------------------------------------- materials
_mats: dict[str, bpy.types.Material] = {}


def mat(name: str, color, rough: float = 0.8, metal: float = 0.0, alpha: float = 1.0) -> bpy.types.Material:
    """Flat-colour material. color: (r, g, b) in 0-1 sRGB."""
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*srgb_to_linear(color), 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    _mats[name] = m
    return m


def tex_mat(name: str, image_path: Path, rough: float = 0.85, alpha_clip: bool = False,
            alpha_blend: bool = False, double_sided: bool = False) -> bpy.types.Material:
    """Material using an image texture (exported to glTF with the model)."""
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = bpy.data.images.load(str(image_path), check_existing=True)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha_clip or alpha_blend:
        nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        if hasattr(m, "blend_method"):
            m.blend_method = "BLEND" if alpha_blend else "CLIP"
        if hasattr(m, "surface_render_method") and alpha_blend:
            m.surface_render_method = "BLENDED"
    if double_sided:
        m.use_backface_culling = False
    bsdf.inputs["Roughness"].default_value = rough
    _mats[name] = m
    return m


def srgb_to_linear(c):
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c[:3])


# --------------------------------------------------------------------------- textures from concept art
def crop_texture(src: Path, box: tuple[int, int, int, int], out_name: str, size: int | None = None,
                 tile_x: bool = True, tile_y: bool = True) -> Path:
    """Crop box=(x, y, w, h) (pixels, top-left origin) from a concept image into a PNG texture.
    With tile_x/tile_y the edges are cross-faded so the texture repeats without hard seams."""
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    img = bpy.data.images.load(str(src), check_existing=True)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]  # top-left origin
    x, y, cw, ch = box
    crop = px[y : y + ch, x : x + cw].copy()
    if tile_x:
        crop = _crossfade(crop, axis=1)
    if tile_y:
        crop = _crossfade(crop, axis=0)
    out = bpy.data.images.new(out_name, crop.shape[1], crop.shape[0], alpha=True)
    out.pixels[:] = crop[::-1].ravel()
    if size:
        out.scale(size, size)
    path = TEX_DIR / f"{out_name}.png"
    out.filepath_raw = str(path)
    out.file_format = "PNG"
    out.save()
    return path


def _crossfade(a: np.ndarray, axis: int, frac: float = 0.18) -> np.ndarray:
    n = a.shape[axis]
    k = max(2, int(n * frac))
    a = np.moveaxis(a, axis, 0)
    head, body, tail = a[:k], a[k : n - k], a[n - k :]
    t = np.linspace(0, 1, k).reshape(-1, *([1] * (a.ndim - 1)))
    blend = tail * (1 - t) + head * t  # tail fades into head, so the end meets the start
    out = np.concatenate([body, blend], axis=0)
    return np.moveaxis(out, 0, axis)


# --------------------------------------------------------------------------- geometry
def _obj_from_bm(name: str, bm: bmesh.types.BMesh, material=None) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = link(bpy.data.objects.new(name, me))
    if material is not None:
        obj.data.materials.append(material)
    return obj


def box(name: str, size, loc, material=None, rot=(0, 0, 0), uv_scale: float | None = None) -> bpy.types.Object:
    """Axis box of size (x, y, z) centred at loc. uv_scale: metres per texture repeat (world UVs)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    obj = _obj_from_bm(name, bm, material)
    obj.location = loc
    obj.rotation_euler = rot
    if uv_scale:
        world_uv(obj, uv_scale)
    return obj


def cyl(name: str, radius: float, depth: float, loc, material=None, rot=(0, 0, 0), verts: int = 12,
        radius2: float | None = None) -> bpy.types.Object:
    """Cylinder (or cone/frustum with radius2) along local Z, centred at loc."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=radius,
                          radius2=radius if radius2 is None else radius2, depth=depth)
    obj = _obj_from_bm(name, bm, material)
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def torus(name: str, major: float, minor: float, loc, material=None, rot=(0, 0, 0), seg=32, ring=8):
    bm = bmesh.new()
    verts = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        for j in range(ring):
            b = 2 * math.pi * j / ring
            r = major + minor * math.cos(b)
            verts.append(bm.verts.new((r * math.cos(a), r * math.sin(a), minor * math.sin(b))))
    for i in range(seg):
        for j in range(ring):
            a = verts[i * ring + j]
            b = verts[((i + 1) % seg) * ring + j]
            c = verts[((i + 1) % seg) * ring + (j + 1) % ring]
            d = verts[i * ring + (j + 1) % ring]
            bm.faces.new((a, b, c, d))
    obj = _obj_from_bm(name, bm, material)
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def prism(name: str, profile_yz, x0: float, x1: float, material=None, uv_scale: float | None = None):
    """Extrude a closed polygon given in the Y-Z plane (list of (y, z)) from x0 to x1."""
    bm = bmesh.new()
    left = [bm.verts.new((x0, y, z)) for y, z in profile_yz]
    right = [bm.verts.new((x1, y, z)) for y, z in profile_yz]
    bm.faces.new(list(reversed(left)))
    bm.faces.new(right)
    n = len(profile_yz)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((left[i], left[j], right[j], right[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = _obj_from_bm(name, bm, material)
    if uv_scale:
        world_uv(obj, uv_scale)
    return obj


def world_uv(obj: bpy.types.Object, metres_per_repeat: float) -> None:
    """Box-project UVs in world units, so textures keep a constant real-world size on any face."""
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    mw = obj.matrix_world
    for poly in me.polygons:
        n = (mw.to_3x3() @ poly.normal).normalized()
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            p = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 0:
                u, v = p.y * (1 if n.x > 0 else -1), p.z
            elif ax == 1:
                u, v = p.x * (-1 if n.y > 0 else 1), p.z
            else:
                u, v = p.x, p.y
            uv[li].uv = (u / metres_per_repeat, v / metres_per_repeat)


def sloped_uv(obj: bpy.types.Object, metres_per_repeat: float) -> None:
    """UVs for roof planes: u along X, v along the slope (so shingle rows run along the eave)."""
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        n = poly.normal
        up = Vector((0, 0, 1))
        slope_dir = (up - n * n.dot(up))
        slope_dir = slope_dir.normalized() if slope_dir.length > 1e-6 else Vector((0, 1, 0))
        for li in poly.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co
            uv[li].uv = (p.x / metres_per_repeat, p.dot(slope_dir) / metres_per_repeat)


def join(name: str, objs) -> bpy.types.Object:
    objs = [o for o in objs if o is not None]
    # Every part needs the same UV layer, or joining drops the UVs of textured parts.
    for o in objs:
        if o.type == "MESH" and not o.data.uv_layers:
            o.data.uv_layers.new(name="UVMap")
        elif o.type == "MESH":
            o.data.uv_layers[0].name = "UVMap"
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return obj


def shade_flat(obj) -> None:
    for p in obj.data.polygons:
        p.use_smooth = False


def shade_smooth(obj) -> None:
    for p in obj.data.polygons:
        p.use_smooth = True


# --------------------------------------------------------------------------- export + preview
def export(category: str, name: str, previews=(("front", 0), ("three_quarter", 35), ("side", 90))) -> Path:
    folder = ASSETS / category / name
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / "model.glb"
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", use_selection=False,
                              export_apply=True, export_yup=True, export_image_format="AUTO")
    tris = sum(len(o.data.polygons) for o in bpy.context.scene.objects if o.type == "MESH")
    print(f"EXPORTED {out.relative_to(ROOT)}  faces={tris}")
    if os.environ.get("NO_PREVIEW") != "1":
        for label, yaw, *pitch in previews:
            render_preview(folder / f"preview_{label}.png", yaw, pitch[0] if pitch else None)
    return out


def render_preview(path: Path, yaw_deg: float, pitch_deg: float | None = None, size: int = 640,
                   focus: Vector | None = None, frame_radius: float | None = None) -> None:
    """Quick EEVEE render from the front (yaw 0 = looking at the -Y face) to check the model."""
    scene = bpy.context.scene
    objs = [o for o in scene.objects if o.type == "MESH"]
    lo = Vector((min(v[i] for o in objs for v in (o.matrix_world @ Vector(c) for c in o.bound_box)) for i in range(3)))
    hi = Vector((max(v[i] for o in objs for v in (o.matrix_world @ Vector(c) for c in o.bound_box)) for i in range(3)))
    centre = Vector(focus) if focus is not None else (lo + hi) / 2
    radius = frame_radius if frame_radius is not None else (hi - lo).length / 2

    cam_data = bpy.data.cameras.get("PreviewCam") or bpy.data.cameras.new("PreviewCam")
    cam = scene.objects.get("PreviewCam") or link(bpy.data.objects.new("PreviewCam", cam_data))
    cam_data.lens = 50
    yaw = math.radians(yaw_deg)
    dist = radius * 3.1
    if pitch_deg is None:
        cam.location = centre + Vector((dist * math.sin(yaw), -dist * math.cos(yaw), radius * 0.55))
    else:
        pt = math.radians(pitch_deg)
        cam.location = centre + dist * Vector((math.sin(yaw) * math.cos(pt), -math.cos(yaw) * math.cos(pt), math.sin(pt)))
    direction = centre - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    if not scene.objects.get("PreviewSun"):
        sun = bpy.data.lights.new("PreviewSun", "SUN")
        sun.energy = 3.0
        s = link(bpy.data.objects.new("PreviewSun", sun))
        s.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
    world = bpy.data.worlds.get("PreviewWorld") or bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.62, 0.68, 0.75, 1)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world

    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.filepath = str(path)
    scene.view_settings.view_transform = "Standard"
    bpy.ops.render.render(write_still=True)
    # The camera and light are only for previews: remove them before any later export.
    for n in ("PreviewCam", "PreviewSun"):
        o = scene.objects.get(n)
        if o:
            bpy.data.objects.remove(o)
    print(f"PREVIEW {path.relative_to(ROOT)}")


def tube(name: str, p0, p1, radius: float, material=None, verts: int = 8, radius2: float | None = None):
    """Cylinder from point p0 to point p1 (for frames, spokes, branches)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    obj = cyl(name, radius, d.length, (p0 + p1) / 2, material, verts=verts, radius2=radius2)
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return obj


def blob(name: str, radius: float, loc, material=None, subdiv: int = 1, scale=(1, 1, 1)):
    """Low-poly icosphere (leaves, flowers, rocks)."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    obj = _obj_from_bm(name, bm, material)
    obj.location = loc
    obj.scale = scale
    return obj


def quad(name: str, w: float, h: float, loc, material=None, rot=(0, 0, 0)):
    """A flat w x h card in the XY plane with 0-1 UVs (for cut-out textures like wings)."""
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0))]
    face = bm.faces.new(vs)
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for loop, uv in zip(face.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv_layer].uv = uv
    obj = _obj_from_bm(name, bm, material)
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def cutout_texture(src: Path, box: tuple[int, int, int, int], out_name: str, bg=None, tolerance: float = 0.12) -> Path:
    """Crop like crop_texture, but make the flat background colour transparent (wings, leaves).
    bg defaults to the colour of the crop's top-left pixel."""
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    img = bpy.data.images.load(str(src), check_existing=True)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    x, y, cw, ch = box
    crop = px[y : y + ch, x : x + cw].copy()
    ref = np.array(bg if bg is not None else crop[0, 0, :3])
    dist = np.linalg.norm(crop[..., :3] - ref, axis=-1)
    crop[..., 3] = np.clip((dist - tolerance * 0.5) / tolerance, 0, 1)
    out = bpy.data.images.new(out_name, cw, ch, alpha=True)
    out.pixels[:] = crop[::-1].ravel()
    path = TEX_DIR / f"{out_name}.png"
    out.filepath_raw = str(path)
    out.file_format = "PNG"
    out.save()
    return path


# --------------------------------------------------------------------------- organic shapes
def sweep(name: str, path, radii, material=None, segments: int = 12, caps=(True, True),
          smooth: bool = True, roll=None):
    """A tube swept along `path` (list of points), with `radii` per point.

    Each radius is a float (round) or an (rx, ry) pair (elliptical: rx across the body, ry
    front-to-back). Ring orientations use parallel transport, so bent limbs don't twist.
    `roll` optionally gives a per-point twist in radians about the tube axis.
    This is the workhorse for arms, legs, torsos and necks.
    """
    pts = [Vector(p) for p in path]
    n = len(pts)
    rr = [(r, r) if isinstance(r, (int, float)) else tuple(r) for r in radii]
    assert len(rr) == n >= 2

    # Tangent per point (averaged at the joints so bends stay smooth)
    seg_dirs = [(pts[i + 1] - pts[i]).normalized() for i in range(n - 1)]
    tangents = [seg_dirs[0]] + [(seg_dirs[i] + seg_dirs[i + 1]).normalized() for i in range(n - 2)] + [seg_dirs[-1]]

    # Parallel-transport frame
    seed = Vector((1, 0, 0))
    if abs(seed.dot(tangents[0])) > 0.9:
        seed = Vector((0, 1, 0))
    u = (seed - tangents[0] * seed.dot(tangents[0])).normalized()
    frames = [(u, tangents[0].cross(u).normalized())]
    for i in range(1, n):
        q = tangents[i - 1].rotation_difference(tangents[i])
        u = (q @ frames[-1][0]).normalized()
        frames.append((u, tangents[i].cross(u).normalized()))

    bm = bmesh.new()
    rings = []
    for i in range(n):
        u, v = frames[i]
        rx, ry = rr[i]
        twist = 0.0 if roll is None else roll[i]
        ring = []
        for s in range(segments):
            a = 2 * math.pi * s / segments + twist
            ring.append(bm.verts.new(pts[i] + u * (math.cos(a) * rx) + v * (math.sin(a) * ry)))
        rings.append(ring)
    for i in range(n - 1):
        for s in range(segments):
            t = (s + 1) % segments
            bm.faces.new((rings[i][s], rings[i][t], rings[i + 1][t], rings[i + 1][s]))
    if caps[0]:
        bm.faces.new(list(reversed(rings[0])))
    if caps[1]:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = _obj_from_bm(name, bm, material)
    if smooth:
        shade_smooth(obj)
    return obj


def uvsphere(name: str, radius: float, loc=(0, 0, 0), material=None, segments: int = 20, rings: int = 12,
             scale=(1, 1, 1), smooth: bool = True):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    obj = _obj_from_bm(name, bm, material)
    obj.location = loc
    obj.scale = scale
    if smooth:
        shade_smooth(obj)
    return obj


def shape_verts(obj, fn, world: bool = True) -> None:
    """Deform in place: fn(point) -> point.

    By default the point is in WORLD space, so a shaping rule can be written with the same
    numbers used to place the part ("flatten everything above z = 1.66"). Pass world=False to
    work in the object's own local space instead.
    """
    if not world:
        for v in obj.data.vertices:
            v.co = Vector(fn(Vector(v.co)))
        return
    bpy.context.view_layer.update()
    m = obj.matrix_world.copy()
    inv = m.inverted()
    for v in obj.data.vertices:
        v.co = inv @ Vector(fn(m @ Vector(v.co)))


def bend_z(obj, fn) -> None:
    """Scale each vertex's X and Y by fn(z) -> (sx, sy, dx, dy). Handy for tapering a shape."""
    for v in obj.data.vertices:
        sx, sy, dx, dy = fn(v.co.z)
        v.co.x = v.co.x * sx + dx
        v.co.y = v.co.y * sy + dy


def subsurf(obj, levels: int = 1, apply: bool = True) -> None:
    m = obj.modifiers.new("Subdivision", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    if apply:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj.data = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
        obj.modifiers.clear()


def mirror_x(obj, name: str | None = None):
    """A mirrored copy across the YZ plane (the other arm, leg, eye...).

    The reflected world transform is baked straight into the mesh, which keeps the copy's
    position, rotation and scale all mirrored. Reflecting also inverts the winding, so the
    normals are flipped back.
    """
    bpy.context.view_layer.update()
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.name = name or (obj.name + "_R")
    link(copy)
    copy.data.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)) @ obj.matrix_world)
    copy.matrix_world = Matrix.Identity(4)
    copy.data.flip_normals()
    return copy


def both(objs):
    """Mirror a list of objects and return originals + mirrors."""
    return list(objs) + [mirror_x(o) for o in objs]
