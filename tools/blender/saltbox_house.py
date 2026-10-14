"""
Saltbox house for Carbonear, modelled from assets/buildings/saltbox_house/concept_1.png.
Run:  blender -b -P tools/blender/saltbox_house.py

Matches the graybox footprint so it drops into the scene unscaled: 8 m wide (X), 7 m deep (Y),
front wall at y = -3 (facing -Y = the road), two storeys at the front, long rear roof down to a
one-storey back wall at y = +4.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib

import common

importlib.reload(common)
from common import *  # noqa: E402,F401,F403

CONCEPT = ASSETS / "buildings" / "saltbox_house" / "concept_1.png"

# ----------------------------------------------------------------------------- dimensions
W = 8.0                 # width along X
Y_FRONT, Y_BACK = -3.0, 4.0
FOUND_H = 0.6           # stone foundation
EAVE_FRONT = 6.0        # top of front wall
RIDGE_Y, RIDGE_Z = -1.0, 8.0
EAVE_BACK = 3.2         # top of back wall
ROOF_T = 0.16           # roof thickness
OVERHANG = 0.35
GABLE_OVER = 0.22

reset()

# ----------------------------------------------------------------------------- textures from the concept art
roof_png = crop_texture(CONCEPT, (1100, 312, 290, 236), "house_roof_shingles")
siding_png = crop_texture(CONCEPT, (1138, 598, 124, 132), "house_siding")
stone_png = crop_texture(CONCEPT, (996, 745, 200, 28), "house_stone", tile_y=False)
brick_png = crop_texture(CONCEPT, (388, 222, 34, 70), "house_chimney_brick")

M_SIDING = tex_mat("Siding", siding_png, rough=0.9)
M_ROOF = tex_mat("Shingles", roof_png, rough=0.95)
M_STONE = tex_mat("Stone", stone_png, rough=0.95)
M_BRICK = tex_mat("ChimneyBrick", brick_png, rough=0.9)
M_TRIM = mat("Trim", (0.93, 0.91, 0.85), rough=0.7)
M_GLASS = mat("Glass", (0.20, 0.25, 0.30), rough=0.15, metal=0.2)
M_DOOR = mat("Door", (0.33, 0.47, 0.31), rough=0.6)
M_DOOR_DARK = mat("DoorPanel", (0.27, 0.40, 0.26), rough=0.6)
M_BRASS = mat("Brass", (0.78, 0.62, 0.3), rough=0.35, metal=0.9)
M_STEP = mat("Steps", (0.58, 0.57, 0.55), rough=0.95)
M_WOOD = mat("BoxWood", (0.62, 0.5, 0.36), rough=0.9)
M_POT = mat("ChimneyPot", (0.66, 0.34, 0.22), rough=0.85)
M_LEAF = mat("Leaves", (0.27, 0.5, 0.22), rough=0.8)
M_RED = mat("FlowerRed", (0.84, 0.15, 0.13), rough=0.6)
M_YELLOW = mat("FlowerYellow", (0.96, 0.78, 0.15), rough=0.6)
M_RIDGE = mat("RidgeCap", (0.24, 0.24, 0.25), rough=0.9)

parts = []


def uv(obj, su, sv=None):
    world_uv(obj, su)
    if sv:
        # rescale V separately (world_uv uses one scale)
        layer = obj.data.uv_layers.active.data
        for d in layer:
            d.uv = (d.uv[0], d.uv[1] * su / sv)
    return obj


# ----------------------------------------------------------------------------- body
found = box("Foundation", (W + 0.1, Y_BACK - Y_FRONT + 0.1, FOUND_H), (0, (Y_FRONT + Y_BACK) / 2, FOUND_H / 2), M_STONE)
parts.append(uv(found, 3.0, 0.6))

profile = [(Y_FRONT, FOUND_H), (Y_FRONT, EAVE_FRONT), (RIDGE_Y, RIDGE_Z), (Y_BACK, EAVE_BACK), (Y_BACK, FOUND_H)]
shell = prism("Walls", profile, -W / 2, W / 2, M_SIDING)
parts.append(uv(shell, 1.85, 2.0))


# ----------------------------------------------------------------------------- roof
def slope_frame(top, bottom):
    ty, tz = top
    by, bz = bottom
    L = math.hypot(by - ty, bz - tz)
    u = ((by - ty) / L, (bz - tz) / L)                      # down the slope
    n = (-u[1], u[0]) if -u[1] * 0 + u[0] * 1 > 0 else (u[1], -u[0])
    if n[1] < 0 and False:
        pass
    # pick the perpendicular that points up
    c1, c2 = (-u[1], u[0]), (u[1], -u[0])
    n = c1 if c1[1] > 0 else c2
    return u, n


def roof_slab(name, top, bottom, overhang):
    u, n = slope_frame(top, bottom)
    ty, tz = top
    by, bz = bottom[0] + u[0] * overhang, bottom[1] + u[1] * overhang
    t = ROOF_T
    prof = [(ty, tz), (by, bz), (by + n[0] * t, bz + n[1] * t), (ty + n[0] * t, tz + n[1] * t)]
    slab = prism(name, prof, -W / 2 - GABLE_OVER, W / 2 + GABLE_OVER, M_ROOF)
    sloped_uv(slab, 3.0)
    return slab, u, n


front_roof, uf, nf = roof_slab("RoofFront", (RIDGE_Y, RIDGE_Z), (Y_FRONT, EAVE_FRONT), OVERHANG)
back_roof, ub, nb = roof_slab("RoofBack", (RIDGE_Y, RIDGE_Z), (Y_BACK, EAVE_BACK), OVERHANG)
parts += [front_roof, back_roof]
ridge = box("RidgeCap", (W + 2 * GABLE_OVER + 0.04, 0.28, 0.14), (0, RIDGE_Y, RIDGE_Z + ROOF_T + 0.02), M_RIDGE)
parts.append(ridge)


# Fascia boards under the eaves and rake boards up the gable edges (white trim)
def rake(side_x, top, bottom, overhang):
    u, n = slope_frame(top, bottom)
    ty, tz = top
    by, bz = bottom[0] + u[0] * overhang, bottom[1] + u[1] * overhang
    d = 0.2  # board depth below the roof
    prof = [(ty, tz + 0.02), (by, bz + 0.02), (by - n[0] * d, bz - n[1] * d), (ty - n[0] * d, tz - n[1] * d)]
    x0 = side_x - 0.03 if side_x > 0 else side_x - 0.05
    return prism("Rake", prof, side_x + (0.0 if side_x > 0 else -0.06), side_x + (0.06 if side_x > 0 else 0.0), M_TRIM)


for sx in (-W / 2 - GABLE_OVER + 0.02, W / 2 + GABLE_OVER - 0.08):
    parts.append(rake(sx, (RIDGE_Y, RIDGE_Z), (Y_FRONT, EAVE_FRONT), OVERHANG))
    parts.append(rake(sx, (RIDGE_Y, RIDGE_Z), (Y_BACK, EAVE_BACK), OVERHANG))

parts.append(box("FasciaFront", (W + 2 * GABLE_OVER, 0.08, 0.22),
                 (0, Y_FRONT + uf[0] * OVERHANG - 0.02, EAVE_FRONT + uf[1] * OVERHANG - 0.06), M_TRIM))
parts.append(box("FasciaBack", (W + 2 * GABLE_OVER, 0.08, 0.22),
                 (0, Y_BACK + ub[0] * OVERHANG + 0.02, EAVE_BACK + ub[1] * OVERHANG - 0.06), M_TRIM))
parts.append(box("FriezeFront", (W + 0.1, 0.06, 0.22), (0, Y_FRONT - 0.03, EAVE_FRONT - 0.12), M_TRIM))

# Corner boards
for x in (-W / 2, W / 2):
    parts.append(box("CornerF", (0.2, 0.2, EAVE_FRONT - FOUND_H), (x, Y_FRONT, (EAVE_FRONT + FOUND_H) / 2), M_TRIM))
    parts.append(box("CornerB", (0.2, 0.2, EAVE_BACK - FOUND_H), (x, Y_BACK, (EAVE_BACK + FOUND_H) / 2), M_TRIM))
    # vertical trim where the two-storey part meets the lean-to (seen in the side view)
    z_top = RIDGE_Z + (0.6 - RIDGE_Y) * (EAVE_BACK - RIDGE_Z) / (Y_BACK - RIDGE_Y)
    parts.append(box("SideTrim", (0.05 if x > 0 else 0.05, 0.16, z_top - FOUND_H), (x + (0.02 if x > 0 else -0.02), 0.6, (z_top + FOUND_H) / 2), M_TRIM))


# ----------------------------------------------------------------------------- windows
def window(cx, cz, w, h, facing, cols=3, rows=3, plane=None):
    """A sash window with white frame, sill and muntins. facing: '-y', '+y', '-x', '+x'."""
    objs = []
    sgn = -1 if facing[0] == "-" else 1
    axis = facing[1]
    p = plane if plane is not None else ((Y_FRONT if sgn < 0 else Y_BACK) if axis == "y" else sgn * W / 2)

    def at(a, depth_off, b):
        # a = horizontal coordinate along the wall, b = height, depth_off = outward offset
        if axis == "y":
            return (a, p + sgn * depth_off, b)
        return (p + sgn * depth_off, a, b)

    def sz(sa, sd, sh):
        return (sa, sd, sh) if axis == "y" else (sd, sa, sh)

    objs.append(box("WinFrame", sz(w + 0.26, 0.08, h + 0.26), at(cx, 0.04, cz), M_TRIM))
    objs.append(box("WinGlass", sz(w, 0.04, h), at(cx, 0.085, cz), M_GLASS))
    for i in range(1, cols):
        a = cx - w / 2 + w * i / cols
        objs.append(box("Muntin", sz(0.04, 0.03, h), at(a, 0.11, cz), M_TRIM))
    for j in range(1, rows):
        b = cz - h / 2 + h * j / rows
        objs.append(box("Muntin", sz(w, 0.03, 0.04 if j != rows // 2 + (rows % 2 == 0) - 1 else 0.07), at(cx, 0.11, b), M_TRIM))
    objs.append(box("Sill", sz(w + 0.42, 0.18, 0.07), at(cx, 0.1, cz - h / 2 - 0.15), M_TRIM))
    objs.append(box("Head", sz(w + 0.4, 0.12, 0.1), at(cx, 0.08, cz + h / 2 + 0.17), M_TRIM))
    return objs


# Front: two downstairs, three upstairs
for x in (-2.55, 2.55):
    parts += window(x, 2.25, 0.95, 1.25, "-y")
for x in (-2.6, 0.0, 2.6):
    parts += window(x, 4.55, 0.9, 1.15, "-y")
# Back: two small windows in the one-storey wall
for x in (-2.0, 2.0):
    parts += window(x, 2.0, 0.7, 0.85, "+y", cols=3, rows=3)
# Sides: upstairs window in the tall front part, a smaller one in the lean-to
for side in ("-x", "+x"):
    parts += window(-2.0, 4.4, 0.85, 1.1, side)
    parts += window(2.3, 1.95, 0.7, 0.85, side)

# ----------------------------------------------------------------------------- door, transom, steps
DZ0 = FOUND_H
parts.append(box("DoorSurround", (1.5, 0.1, 2.75), (0, Y_FRONT - 0.05, DZ0 + 1.37), M_TRIM))
parts.append(box("DoorHeader", (1.75, 0.18, 0.16), (0, Y_FRONT - 0.09, DZ0 + 2.8), M_TRIM))
parts.append(box("Door", (1.0, 0.08, 2.05), (0, Y_FRONT - 0.12, DZ0 + 1.03), M_DOOR))
for (px, pz, ph) in ((-0.22, 0.55, 0.65), (0.22, 0.55, 0.65), (-0.22, 1.45, 0.75), (0.22, 1.45, 0.75)):
    parts.append(box("DoorPanel", (0.34, 0.03, ph), (px, Y_FRONT - 0.17, DZ0 + pz), M_DOOR_DARK))
parts.append(box("Transom", (1.0, 0.04, 0.32), (0, Y_FRONT - 0.12, DZ0 + 2.38), M_GLASS))
for i in (-0.25, 0.0, 0.25):
    parts.append(box("TransomBar", (0.03, 0.03, 0.32), (i, Y_FRONT - 0.15, DZ0 + 2.38), M_TRIM))
knob = cyl("Knob", 0.045, 0.06, (0.36, Y_FRONT - 0.18, DZ0 + 1.0), M_BRASS, rot=(math.pi / 2, 0, 0), verts=10)
parts.append(knob)
parts.append(box("StepLow", (1.7, 0.75, 0.3), (0, Y_FRONT - 0.42, 0.15), M_STEP))
parts.append(box("StepHigh", (1.7, 0.4, 0.3), (0, Y_FRONT - 0.25, 0.45), M_STEP))

# ----------------------------------------------------------------------------- flower boxes
import bmesh as _bm


def blob(name, r, loc, material, subdiv=1):
    bm = _bm.new()
    _bm.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = link(bpy.data.objects.new(name, me))
    o.data.materials.append(material)
    o.location = loc
    return o


import random

random.seed(1964)
for x in (-2.55, 2.55):
    zb = 2.25 - 1.25 / 2 - 0.42
    parts.append(box("FlowerBox", (1.3, 0.34, 0.3), (x, Y_FRONT - 0.22, zb), M_WOOD))
    for bx in (-0.45, 0.45):
        parts.append(box("Bracket", (0.06, 0.2, 0.22), (x + bx, Y_FRONT - 0.12, zb - 0.22), M_WOOD))
    for i in range(9):
        fx = x - 0.55 + i * 0.1375
        parts.append(blob("Leaf", 0.11, (fx, Y_FRONT - 0.22 + random.uniform(-0.06, 0.06), zb + 0.2), M_LEAF))
        if i % 2 == 0 or random.random() < 0.4:
            m = M_RED if random.random() < 0.55 else M_YELLOW
            parts.append(blob("Flower", 0.07, (fx + random.uniform(-0.04, 0.04), Y_FRONT - 0.3 + random.uniform(-0.05, 0.03), zb + 0.3 + random.uniform(0, 0.05)), m))

# ----------------------------------------------------------------------------- chimney
CX, CY = 1.7, RIDGE_Y + 0.15
chim = box("Chimney", (0.72, 0.72, 2.2), (CX, CY, RIDGE_Z + 0.25), M_BRICK)
parts.append(uv(chim, 0.6, 1.2))
parts.append(box("ChimneyCap", (0.84, 0.84, 0.1), (CX, CY, RIDGE_Z + 1.4), M_TRIM))
parts.append(cyl("ChimneyPot", 0.14, 0.38, (CX, CY, RIDGE_Z + 1.62), M_POT, verts=12, radius2=0.12))

house = join("SaltboxHouse", parts)
shade_flat(house)
export("buildings", "saltbox_house")
