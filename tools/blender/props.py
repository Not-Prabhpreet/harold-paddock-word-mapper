"""
Props for episode 1, modelled from the concept art.
Run one or more:  blender -b -P tools/blender/props.py -- bicycle dragonfly picket_fence ...
Each asset is exported to assets/props/<name>/model.glb with preview renders.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib

import common

importlib.reload(common)
from common import *  # noqa: E402,F401,F403

SHEET = ASSETS / "props" / "props_sheet.png"


def uv2(obj, su, sv):
    """World-space UVs with different metres-per-repeat horizontally (su) and vertically (sv)."""
    world_uv(obj, su)
    for d in obj.data.uv_layers.active.data:
        d.uv = (d.uv[0], d.uv[1] * su / sv)
    return obj


# ============================================================================ bicycle
def bicycle():
    """1960s 10-speed, from assets/props/bicycle/concept_1.png. Front wheel toward -Y."""
    red = mat("Frame", (0.66, 0.13, 0.11), rough=0.35, metal=0.3)
    chrome = mat("Chrome", (0.8, 0.8, 0.82), rough=0.25, metal=1.0)
    tyre = mat("Tyre", (0.12, 0.12, 0.13), rough=0.9)
    gum = mat("Gumwall", (0.78, 0.62, 0.38), rough=0.8)
    tape = mat("BarTape", (0.93, 0.91, 0.86), rough=0.8)
    leather = mat("Leather", (0.48, 0.28, 0.15), rough=0.6)
    canvas = mat("Canvas", (0.42, 0.42, 0.28), rough=0.95)
    dark = mat("Dark", (0.18, 0.18, 0.2), rough=0.6, metal=0.5)

    R = 0.34                       # wheel radius (700c with tyre)
    rear = Vector((0, 0.5, R))
    front = Vector((0, -0.5, R))
    bb = Vector((0, 0.08, 0.27))   # bottom bracket
    seat_top = Vector((0, 0.24, 0.84))
    head_top = Vector((0, -0.36, 0.82))
    head_bot = Vector((0, -0.4, 0.66))
    p = []

    for c, nm in ((rear, "Rear"), (front, "Front")):
        p.append(torus(f"Tyre{nm}", R - 0.015, 0.016, c, tyre, rot=(0, math.pi / 2, 0), seg=40, ring=6))
        p.append(torus(f"Gum{nm}", R - 0.032, 0.008, c, gum, rot=(0, math.pi / 2, 0), seg=40, ring=5))
        p.append(torus(f"Rim{nm}", R - 0.045, 0.008, c, chrome, rot=(0, math.pi / 2, 0), seg=40, ring=5))
        p.append(cyl(f"Hub{nm}", 0.025, 0.1, c, chrome, rot=(0, math.pi / 2, 0), verts=10))
        for i in range(18):
            a = 2 * math.pi * i / 18
            side = 0.03 if i % 2 else -0.03
            rim_pt = c + Vector((0, math.cos(a) * (R - 0.05), math.sin(a) * (R - 0.05)))
            p.append(tube("Spoke", c + Vector((side, 0, 0)), rim_pt, 0.0025, chrome, verts=4))

    tr = 0.016
    p += [tube("TopTube", seat_top + Vector((0, 0, -0.03)), head_top + Vector((0, 0, -0.04)), tr, red),
          tube("DownTube", head_bot, bb, tr * 1.15, red),
          tube("SeatTube", bb, seat_top, tr, red),
          tube("ChainStayL", bb, rear + Vector((0.035, 0, 0)), 0.01, red),
          tube("ChainStayR", bb, rear + Vector((-0.035, 0, 0)), 0.01, red),
          tube("SeatStayL", seat_top + Vector((0, 0, -0.05)), rear + Vector((0.035, 0, 0)), 0.009, red),
          tube("SeatStayR", seat_top + Vector((0, 0, -0.05)), rear + Vector((-0.035, 0, 0)), 0.009, red),
          tube("HeadTube", head_bot, head_top, 0.02, red),
          tube("ForkL", head_bot, front + Vector((0.035, -0.04, 0)), 0.011, red),
          tube("ForkR", head_bot, front + Vector((-0.035, -0.04, 0)), 0.011, red)]

    # Seat post, saddle, saddle bag
    post_top = seat_top + Vector((0, 0.03, 0.12))
    p.append(tube("SeatPost", seat_top, post_top, 0.012, chrome))
    p.append(box("Saddle", (0.13, 0.27, 0.05), post_top + Vector((0, 0.01, 0.03)), leather))
    p.append(box("SaddleNose", (0.06, 0.08, 0.04), post_top + Vector((0, -0.14, 0.025)), leather))
    p.append(box("Bag", (0.16, 0.12, 0.11), post_top + Vector((0, 0.16, -0.06)), canvas))
    p.append(box("BagStrap", (0.17, 0.02, 0.115), post_top + Vector((0, 0.17, -0.06)), leather))

    # Stem and drop handlebars (white tape)
    stem_end = head_top + Vector((0, -0.08, 0.06))
    p.append(tube("Stem", head_top, stem_end, 0.012, chrome))
    p.append(tube("BarCentre", stem_end + Vector((-0.2, 0, 0)), stem_end + Vector((0.2, 0, 0)), 0.013, tape))
    for sx in (-0.2, 0.2):
        a = stem_end + Vector((sx, 0, 0))
        b = a + Vector((0, -0.09, -0.02))
        c = b + Vector((0, -0.02, -0.12))
        d = c + Vector((0, 0.08, -0.03))
        p += [tube("Drop", a, b, 0.012, tape), tube("Drop", b, c, 0.012, tape), tube("Drop", c, d, 0.012, tape)]
        p.append(box("Hood", (0.03, 0.04, 0.06), b + Vector((0, 0.0, 0.03)), leather))

    # Drivetrain
    p.append(torus("Chainring", 0.1, 0.008, bb + Vector((-0.05, 0, 0)), chrome, rot=(0, math.pi / 2, 0), seg=28, ring=4))
    p.append(cyl("Cassette", 0.045, 0.03, rear + Vector((-0.05, 0, 0)), chrome, rot=(0, math.pi / 2, 0), verts=14))
    p.append(tube("ChainTop", bb + Vector((-0.05, 0, 0.1)), rear + Vector((-0.05, 0, 0.045)), 0.004, dark, verts=4))
    p.append(tube("ChainBot", bb + Vector((-0.05, 0, -0.1)), rear + Vector((-0.05, 0, -0.045)), 0.004, dark, verts=4))
    crank_end = bb + Vector((-0.07, 0.06, -0.15))
    p.append(tube("Crank", bb + Vector((-0.06, 0, 0)), crank_end, 0.01, chrome))
    p.append(box("Pedal", (0.09, 0.06, 0.02), crank_end + Vector((-0.05, 0, 0)), leather))
    crank2 = bb + Vector((0.07, -0.06, 0.15))
    p.append(tube("Crank2", bb + Vector((0.06, 0, 0)), crank2, 0.01, chrome))
    p.append(box("Pedal2", (0.09, 0.06, 0.02), crank2 + Vector((0.05, 0, 0)), leather))
    p.append(box("Derailleur", (0.02, 0.05, 0.07), rear + Vector((-0.06, 0.02, -0.07)), chrome))

    bike = join("Bicycle", p)
    shade_flat(bike)
    export("props", "bicycle", previews=(("side", 90), ("three_quarter", 35)))


# ============================================================================ dragonfly
def dragonfly():
    """Dragonfly ('orse-stinger) with wings cut straight out of the concept art. Head toward -Y."""
    src = ASSETS / "props" / "dragonfly" / "concept_1.png"
    fore = cutout_texture(src, (34, 262, 336, 150), "dragonfly_forewing", tolerance=0.06)
    hind = cutout_texture(src, (84, 440, 300, 130), "dragonfly_hindwing", tolerance=0.06)
    m_fore = tex_mat("Forewing", fore, rough=0.3, alpha_blend=True, double_sided=True)
    m_hind = tex_mat("Hindwing", hind, rough=0.3, alpha_blend=True, double_sided=True)
    teal = mat("Teal", (0.16, 0.5, 0.55), rough=0.35, metal=0.2)
    green = mat("Thorax", (0.36, 0.6, 0.34), rough=0.4)
    eye = mat("Eye", (0.14, 0.45, 0.5), rough=0.15, metal=0.3)
    leg = mat("Leg", (0.2, 0.18, 0.16), rough=0.7)
    yellow = mat("Spots", (0.78, 0.82, 0.3), rough=0.5)

    s = 0.1  # 10 cm wingspan-ish scale unit
    p = []
    p.append(blob("EyeL", 0.012, (0.009, -0.06, 0.004), eye, subdiv=2))
    p.append(blob("EyeR", 0.012, (-0.009, -0.06, 0.004), eye, subdiv=2))
    p.append(blob("Thorax", 0.016, (0, -0.035, 0), green, subdiv=2, scale=(1, 1.3, 1)))
    for i in range(9):
        y = -0.012 + i * 0.011
        r = 0.0065 - i * 0.0002
        p.append(cyl("Segment", r, 0.0105, (0, y, 0), teal, rot=(math.pi / 2, 0, 0), verts=8))
        p.append(blob("Spot", r * 0.55, (0, y, r * 0.75), yellow, subdiv=1, scale=(1, 1.4, 0.4)))
    p.append(tube("Tail", (0, 0.087, 0), (0, 0.095, 0), 0.003, leg, verts=6))
    for side in (-1, 1):
        for k, y in enumerate((-0.042, -0.035, -0.028)):
            hip = Vector((side * 0.008, y, -0.01))
            knee = hip + Vector((side * 0.01, -0.006 + k * 0.004, -0.008))
            foot = knee + Vector((side * 0.004, -0.004, -0.012))
            p += [tube("Leg", hip, knee, 0.0012, leg, verts=4), tube("Leg", knee, foot, 0.001, leg, verts=4)]
    # Wings: cards with the painted wing textures; right side mirrored
    fw, fh = 0.08, 0.08 * 150 / 336
    hw, hh = 0.07, 0.07 * 130 / 300
    for side in (-1, 1):
        f = quad("Forewing", fw, fh, (side * (fw / 2 + 0.008), -0.04, 0.012), m_fore, rot=(0, 0, 0))
        h = quad("Hindwing", hw, hh, (side * (hw / 2 + 0.008), -0.02, 0.011), m_hind, rot=(0, 0, 0))
        f.rotation_euler = (0, 0, math.radians(-6 * side))
        h.rotation_euler = (0, 0, math.radians(8 * side))
        if side > 0:
            f.scale.x = -1
            h.scale.x = -1
        p += [f, h]
    body = join("Dragonfly", p)
    export("props", "dragonfly", previews=(("top", 0, 80), ("three_quarter", 30, 35)))


# ============================================================================ picket fence
def picket_fence():
    """One 2.4 m section: two square posts with caps, two rails, eight pointed pickets."""
    wood_png = crop_texture(SHEET, (182, 170, 28, 205), "fence_wood", tile_x=False)
    wood = tex_mat("FenceWood", wood_png, rough=0.9)
    p = []
    L = 2.4
    for x in (-L / 2, L / 2):
        p.append(uv2(box("Post", (0.12, 0.12, 1.15), (x, 0, 0.575), wood), 0.12, 1.2))
        p.append(cyl("PostCap", 0.1, 0.1, (x, 0, 1.2), wood, verts=4, radius2=0.0, rot=(0, 0, math.pi / 4)))
    for z in (0.3, 0.8):
        p.append(uv2(box("Rail", (L, 0.05, 0.09), (0, 0.06, z), wood), 0.6, 0.12))
    n = 8
    for i in range(n):
        x = -L / 2 + 0.2 + i * (L - 0.4) / (n - 1)
        p.append(uv2(box("Picket", (0.09, 0.025, 0.9), (x, -0.0, 0.53), wood), 0.12, 1.0))
        p.append(prism("PicketTip", [(-0.0125, 0.98), (-0.0125, 0.98), (0.0125, 0.98)], 0, 0, wood) if False else
                 cyl("PicketTip", 0.064, 0.09, (x, 0.0, 1.02), wood, verts=4, radius2=0.0, rot=(0, 0, math.pi / 4)))
    fence = join("PicketFence", p)
    shade_flat(fence)
    export("props", "picket_fence", previews=(("front", 0), ("three_quarter", 35)))


# ============================================================================ potato patch
def potato_patch():
    """4 m x 5 m garden: three soil mounds (along Y) with leafy, flowering potato plants."""
    soil_png = crop_texture(SHEET, (70, 640, 110, 50), "soil")
    soil = tex_mat("Soil", soil_png, rough=1.0)
    leaf = mat("PotatoLeaf", (0.28, 0.5, 0.2), rough=0.8)
    leaf2 = mat("PotatoLeafLight", (0.42, 0.62, 0.26), rough=0.8)
    flower = mat("PotatoFlower", (0.97, 0.95, 0.88), rough=0.6)
    centre = mat("FlowerCentre", (0.95, 0.75, 0.15), rough=0.6)
    random.seed(7)
    p = [uv2(box("Bed", (4.0, 5.0, 0.08), (0, 0, 0.04), soil), 1.0, 1.0)]
    for rx in (-1.2, 0.0, 1.2):
        prof = []
        for k in range(9):
            a = math.pi * k / 8
            prof.append((rx + 0.48 * math.cos(a), 0.06 + 0.3 * math.sin(a)))
        # profile is in X-Z here, so build along Y by swapping axes via rotation
        mound = prism("Mound", [(x, z) for x, z in prof], -2.3, 2.3, soil)
        mound.rotation_euler = (0, 0, math.pi / 2)
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action="DESELECT")
        mound.select_set(True)
        bpy.context.view_layer.objects.active = mound
        bpy.ops.object.transform_apply(rotation=True)
        uv2(mound, 1.0, 1.0)
        # prism builds the profile in the Y-Z plane; after the turn the mound runs along Y at x = -rx
        mound.location.x = 0
        p.append(mound)
        for j in range(7):
            y = -2.0 + j * 0.66 + random.uniform(-0.08, 0.08)
            base = Vector((-rx + random.uniform(-0.05, 0.05), y, 0.33))
            for _ in range(7):
                off = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.18, 0.18), random.uniform(0.0, 0.25)))
                m = leaf if random.random() < 0.6 else leaf2
                p.append(blob("Leaf", random.uniform(0.09, 0.14), base + off, m, scale=(1, 1, 0.7)))
            for _ in range(random.randint(1, 3)):
                fpos = base + Vector((random.uniform(-0.15, 0.15), random.uniform(-0.12, 0.12), random.uniform(0.3, 0.42)))
                p.append(blob("Flower", 0.035, fpos, flower))
                p.append(blob("Centre", 0.015, fpos + Vector((0, 0, 0.025)), centre))
    patch = join("PotatoPatch", p)
    shade_flat(patch)
    export("props", "potato_patch", previews=(("three_quarter", 35),))


# ============================================================================ spruce tree
def spruce_tree():
    """A scraggly, windswept black spruce (about 5.5 m), branches longer on the downwind side."""
    bark = mat("Bark", (0.4, 0.34, 0.28), rough=0.95)
    needles = mat("Needles", (0.33, 0.4, 0.17), rough=0.9)
    needles2 = mat("NeedlesDark", (0.24, 0.32, 0.14), rough=0.9)
    rock = mat("Rock", (0.5, 0.48, 0.45), rough=0.95)
    grass = mat("DryGrass", (0.62, 0.58, 0.28), rough=0.9)
    random.seed(70)
    H = 5.5
    lean = Vector((0.25, 0, 0))  # top leans slightly downwind (+X)
    p = [tube("Trunk", (0, 0, 0), lean + Vector((0, 0, H)), 0.13, bark, verts=7, radius2=0.03)]
    tiers = 13
    for t in range(tiers):
        f = t / (tiers - 1)
        z = 1.2 + f * (H - 1.4)
        centre = lean * (z / H) + Vector((0, 0, z))
        reach = (1.0 - f) * 1.15 + 0.25
        for k in range(5):
            a = 2 * math.pi * k / 5 + random.uniform(-0.3, 0.3) + t
            downwind = 0.55 + 0.6 * max(0.0, math.cos(a))  # longer toward +X (wind)
            length = reach * downwind * random.uniform(0.75, 1.1)
            tip = centre + Vector((math.cos(a) * length, math.sin(a) * length, -0.15 * length))
            if t < 3 and random.random() < 0.5:
                p.append(tube("DeadBranch", centre, tip, 0.02, bark, verts=4, radius2=0.004))
                continue
            p.append(tube("Branch", centre, tip, 0.025, bark, verts=4, radius2=0.006))
            for s in range(3):
                q = centre.lerp(tip, 0.35 + 0.3 * s)
                m = needles if (s + k) % 2 else needles2
                p.append(blob("Needles", 0.16 + 0.06 * (1 - f), q + Vector((0, 0, 0.04)), m,
                              scale=(1.5, 1.5, 0.55)))
    p.append(blob("TopTuft", 0.18, lean + Vector((0, 0, H)), needles, scale=(0.8, 0.8, 1.6)))
    for i in range(6):
        a = i * 1.1
        p.append(blob("Rock", random.uniform(0.18, 0.3), (math.cos(a) * 0.45, math.sin(a) * 0.4, 0.05), rock,
                      scale=(1.2, 1, 0.55)))
    for i in range(10):
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(0.2, 0.6)
        base = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        p.append(cyl("Grass", 0.07, 0.35, base + Vector((0, 0, 0.17)), grass, verts=4, radius2=0.0))
    tree = join("Spruce", p)
    shade_flat(tree)
    export("props", "spruce_tree", previews=(("front", 0), ("side", 90)))


# ============================================================================ route sign
def route_sign():
    """Weathered sign on a post. Board 1.6 x 1.1 m centred 2.3 m up with its face at y = -0.03,
    matching the game's 'ROUTE 70 / CARBONEAR' Label3D, which is drawn just in front of it."""
    board_png = crop_texture(SHEET, (700, 578, 180, 108), "sign_board", tile_x=False, tile_y=False)
    post_png = crop_texture(SHEET, (776, 700, 30, 220), "sign_post", tile_x=False)
    board_m = tex_mat("Board", board_png, rough=0.85)
    post_m = tex_mat("Post", post_png, rough=0.95)
    rust = mat("Bolt", (0.55, 0.25, 0.15), rough=0.6, metal=0.6)
    p = []
    post = uv2(box("Post", (0.14, 0.12, 3.0), (0, 0.09, 1.5), post_m), 0.14, 3.0)
    p.append(post)
    p.append(cyl("PostTip", 0.1, 0.14, (0, 0.09, 3.07), post_m, verts=4, radius2=0.0, rot=(0, 0, math.pi / 4)))
    board = box("Board", (1.6, 0.06, 1.1), (0, 0, 2.3), board_m)
    # stretch the board texture once across the face
    me = board.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uvd = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uvd[li].uv = (v.x / 1.6 + 0.5, v.z / 1.1 + 0.5)
    p.append(board)
    for z in (2.62, 1.98):
        p.append(blob("Bolt", 0.035, (0, -0.035, z), rust))
    sign = join("RouteSign", p)
    shade_flat(sign)
    export("props", "route_sign", previews=(("front", 0), ("three_quarter", 35)))


BUILDERS = {f.__name__: f for f in (bicycle, dragonfly, picket_fence, potato_patch, spruce_tree, route_sign)}


# ============================================================================ ground cover
def grass_tuft():
    """A small clump of meadow grass, scattered across the fields by the Scatter node."""
    blade = mat("GrassBlade", (0.38, 0.52, 0.24), rough=0.9)
    blade2 = mat("GrassBladeDry", (0.55, 0.57, 0.27), rough=0.9)
    random.seed(12)
    p = []
    for i in range(11):
        a = random.uniform(0, 2 * math.pi)
        lean = random.uniform(0.04, 0.13)
        h = random.uniform(0.14, 0.26)
        base = Vector((math.cos(a) * random.uniform(0, 0.05), math.sin(a) * random.uniform(0, 0.05), 0))
        mid = base + Vector((math.cos(a) * lean * 0.5, math.sin(a) * lean * 0.5, h * 0.6))
        tip = base + Vector((math.cos(a) * lean, math.sin(a) * lean, h))
        m = blade if random.random() < 0.75 else blade2
        p.append(sweep(f"Blade{i}", [base, mid, tip], [0.011, 0.007, 0.0015], m, segments=4,
                       caps=(True, True), smooth=False))
    tuft = join("GrassTuft", p)
    export("props", "grass_tuft", previews=(("three_quarter", 30),))


def beach_rock():
    """A weathered granite boulder, for the rocky edges of the property."""
    stone = mat("Granite", (0.52, 0.50, 0.47), rough=0.95)
    lichen = mat("Lichen", (0.55, 0.57, 0.40), rough=0.95)
    random.seed(31)
    rock = blob("Rock", 0.42, (0, 0, 0.18), stone, subdiv=2, scale=(1.25, 1.0, 0.62))
    shape_verts(rock, lambda v: Vector((
        v.x * (1 + 0.16 * math.sin(v.y * 7.0)), v.y * (1 + 0.14 * math.cos(v.x * 6.0)),
        max(0.0, v.z * (1 + 0.18 * math.sin(v.x * 5.0 + v.y * 4.0))))))
    shade_flat(rock)
    p = [rock]
    for i in range(5):
        a = i * 1.26
        p.append(blob(f"Lichen{i}", random.uniform(0.07, 0.12),
                      (math.cos(a) * 0.3, math.sin(a) * 0.22, 0.30), lichen, subdiv=1, scale=(1, 1, 0.22)))
    out = join("BeachRock", p)
    export("props", "beach_rock", previews=(("three_quarter", 30),))


BUILDERS.update({f.__name__: f for f in (grass_tuft, beach_rock)})


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else list(BUILDERS)
    reset()
    BUILDERS[args[0]]()
