"""
The two characters of episode 1, modelled from their concept sheets:
  assets/characters/garden_man/concept_1.png   the older man in his potato garden
  assets/characters/harold/concept_1.png       Harold Paddock, the young fieldworker

Run:  blender -b -P tools/blender/characters.py -- garden_man
      blender -b -P tools/blender/characters.py -- harold

Each build makes the body from swept tubes and shaped spheres, joins it into one mesh, skins it
to a skeleton and authors the animations the game asks for by name (idle, talking, walk...).
Exports to assets/characters/<name>/rigged.glb plus preview renders.

Both stand in the A-pose of the concept sheets and face -Y, which the glTF exporter turns into
+Z, the direction the game's CharacterModel expects (it applies a 180 degree yaw).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib

import common
import rig

importlib.reload(common)
importlib.reload(rig)
from common import *  # noqa: E402,F403
from rig import FPS, bind, build_armature, clip  # noqa: E402


def arc_path(centre, radius, a0, a1, steps=9, plane="xz", squash=1.0):
    """Points along a circular arc, for mouths, brims and straps."""
    pts = []
    for i in range(steps):
        a = math.radians(a0 + (a1 - a0) * i / (steps - 1))
        c, s = math.cos(a) * radius, math.sin(a) * radius * squash
        if plane == "xz":
            pts.append(Vector(centre) + Vector((c, 0, s)))
        elif plane == "xy":
            pts.append(Vector(centre) + Vector((c, s, 0)))
        else:
            pts.append(Vector(centre) + Vector((0, c, s)))
    return pts


def eye(name, centre, radius, white, iris_m, pupil_m, look=(0, -1, 0), iris_scale=0.52):
    """Eyeball with an iris and pupil set into the front, looking along `look`."""
    d = Vector(look).normalized()
    parts = [uvsphere(f"{name}Ball", radius, centre, white, segments=16, rings=10)]
    parts.append(uvsphere(f"{name}Iris", radius * iris_scale, Vector(centre) + d * (radius * 0.80),
                          iris_m, segments=14, rings=8, scale=(1, 1, 1)))
    parts.append(uvsphere(f"{name}Pupil", radius * iris_scale * 0.5, Vector(centre) + d * (radius * 0.94),
                          pupil_m, segments=12, rings=7))
    return parts


def brow(name, centre, half_width, thickness, material, tilt=0.0, arch=0.30):
    """An eyebrow: a flattened bar with a slight arch, sitting on the brow ridge."""
    b = uvsphere(name, 1.0, centre, material, segments=14, rings=8,
                 scale=(half_width, thickness * 0.9, thickness))
    c = Vector(centre)
    shape_verts(b, lambda v, c=c, w=half_width, a=arch: Vector((
        v.x, v.y, v.z - ((v.x - c.x) / w) ** 2 * w * a)))
    b.rotation_euler = (0, math.radians(tilt), 0)
    return b


# ============================================================================= the gardener
def garden_man():
    """Stocky man in his late sixties: flat cap, braces, rolled sleeves, rubber boots. 1.72 m."""
    J = {
        "toe": Vector((0.095, -0.145, 0.03)),
        "ankle": Vector((0.095, 0.015, 0.105)),
        "knee": Vector((0.105, 0.0, 0.455)),
        "hip_joint": Vector((0.105, 0.0, 0.905)),
        "hip": Vector((0.0, 0.0, 0.93)),
        "waist": Vector((0.0, 0.0, 1.09)),
        "chest": Vector((0.0, 0.0, 1.26)),
        "neck": Vector((0.0, 0.0, 1.425)),
        "chin": Vector((0.0, 0.0, 1.495)),
        "skull": Vector((0.0, 0.0, 1.70)),
        "shoulder": Vector((0.205, 0.0, 1.405)),
        "elbow": Vector((0.345, 0.01, 1.145)),
        "wrist": Vector((0.465, 0.025, 0.895)),
        "fingers": Vector((0.515, 0.03, 0.785)),
    }

    SKIN = mat("Skin", (0.84, 0.63, 0.50), rough=0.72)
    SHIRT = mat("Shirt", (0.44, 0.54, 0.66), rough=0.92)
    CUFF = mat("ShirtCuff", (0.53, 0.62, 0.72), rough=0.92)
    UNDER = mat("Undershirt", (0.87, 0.85, 0.79), rough=0.95)
    BRACE = mat("Brace", (0.29, 0.20, 0.13), rough=0.6)
    BRASS = mat("Buckle", (0.72, 0.57, 0.26), rough=0.35, metal=0.9)
    TROUSER = mat("Trousers", (0.36, 0.28, 0.19), rough=0.95)
    BOOT = mat("Boot", (0.15, 0.15, 0.16), rough=0.55)
    SOLE = mat("BootSole", (0.09, 0.09, 0.10), rough=0.9)
    CAP = mat("Cap", (0.40, 0.40, 0.41), rough=0.9)
    HAIR = mat("Hair", (0.74, 0.73, 0.70), rough=0.9)
    WHITE = mat("EyeWhite", (0.93, 0.93, 0.90), rough=0.25)
    IRIS = mat("Iris", (0.33, 0.43, 0.46), rough=0.2)
    PUPIL = mat("Pupil", (0.06, 0.06, 0.07), rough=0.2)
    MOUTH = mat("Mouth", (0.45, 0.25, 0.23), rough=0.5)
    BUTTON = mat("Button", (0.30, 0.37, 0.46), rough=0.5)

    P = []  # parts

    # ---- torso: a barrel chest over a slight belly, shirt tucked under the waistband
    P.append(sweep("Shirt",
                   [(0, 0.005, 0.92), (0, 0.005, 1.02), (0, 0.004, 1.12), (0, 0.0, 1.24),
                    (0, -0.004, 1.34), (0, -0.004, 1.41), (0, 0, 1.445)],
                   [(0.185, 0.135), (0.197, 0.152), (0.206, 0.157), (0.218, 0.150),
                    (0.226, 0.138), (0.216, 0.124), (0.124, 0.100)],
                   SHIRT, segments=18, caps=(True, False)))
    # collar and the cream undershirt showing at the neck
    P.append(sweep("Neck", [(0, 0, 1.40), (0, 0, 1.50)], [(0.068, 0.062), (0.064, 0.058)], SKIN, segments=14))
    P.append(sweep("Undershirt", [(0, -0.012, 1.40), (0, -0.016, 1.455)],
                   [(0.085, 0.075), (0.078, 0.070)], UNDER, segments=14))
    P.append(sweep("Collar", [(0, 0, 1.432), (0, -0.004, 1.478)],
                   [(0.098, 0.090), (0.090, 0.082)], SHIRT, segments=16, caps=(False, False)))
    for z in (1.33, 1.24, 1.15, 1.06):
        P.append(uvsphere("Button", 0.011, (0, -0.152 - (0.004 if z > 1.2 else 0), z), BUTTON,
                          segments=10, rings=6, scale=(1, 0.35, 1)))
    P.append(box("Pocket", (0.085, 0.006, 0.075), (0.095, -0.146, 1.285), SHIRT))

    # ---- braces: over each shoulder, front waistband to back waistband
    for sx in (-1, 1):
        strap = [(sx * 0.072, -0.145, 0.985), (sx * 0.085, -0.150, 1.10), (sx * 0.098, -0.140, 1.28),
                 (sx * 0.112, -0.085, 1.40), (sx * 0.115, -0.010, 1.445), (sx * 0.110, 0.075, 1.40),
                 (sx * 0.092, 0.135, 1.25), (sx * 0.070, 0.148, 1.06), (sx * 0.055, 0.150, 0.985)]
        P.append(sweep(f"Brace{sx}", strap, [(0.024, 0.007)] * len(strap), BRACE, segments=8))
        P.append(box(f"Buckle{sx}", (0.034, 0.016, 0.032), (sx * 0.078, -0.152, 1.015), BRASS))
    P.append(box("BraceY", (0.05, 0.016, 0.05), (0, 0.152, 1.145), BRACE))

    # ---- trousers: high waistband, baggy legs gathered into the boots
    P.append(sweep("Waistband", [(0, 0.004, 0.905), (0, 0.004, 1.00)],
                   [(0.198, 0.152), (0.196, 0.150)], TROUSER, segments=18, caps=(False, True)))
    P.append(sweep("Seat", [(0, 0.004, 0.80), (0, 0.004, 0.91)],
                   [(0.195, 0.150), (0.198, 0.152)], TROUSER, segments=18, caps=(True, False)))
    legs = []
    for sx in (1,):
        legs.append(sweep("TrouserLeg",
                          [(sx * 0.100, 0.006, 0.86), (sx * 0.104, 0.004, 0.70), (sx * 0.106, 0.0, 0.55),
                           (sx * 0.104, -0.004, 0.46), (sx * 0.100, -0.004, 0.40)],
                          [(0.118, 0.122), (0.116, 0.124), (0.112, 0.120), (0.106, 0.112), (0.098, 0.102)],
                          TROUSER, segments=14))
        # ---- rubber boots: shaft, foot, toe cap and sole
        legs.append(sweep("BootShaft",
                          [(sx * 0.098, -0.004, 0.425), (sx * 0.096, 0.004, 0.33), (sx * 0.095, 0.010, 0.22),
                           (sx * 0.095, 0.012, 0.13)],
                          [(0.104, 0.108), (0.093, 0.098), (0.080, 0.090), (0.078, 0.090)],
                          BOOT, segments=14, caps=(True, False)))
        foot = sweep("BootFoot",
                     [(sx * 0.095, 0.085, 0.085), (sx * 0.095, 0.02, 0.075), (sx * 0.095, -0.05, 0.070),
                      (sx * 0.095, -0.105, 0.062), (sx * 0.095, -0.145, 0.055)],
                     [(0.078, 0.070), (0.082, 0.062), (0.080, 0.055), (0.070, 0.048), (0.050, 0.038)],
                     BOOT, segments=14)
        legs.append(foot)
        legs.append(box("BootSole", (0.165, 0.245, 0.035), (sx * 0.095, -0.025, 0.021), SOLE))
        legs.append(box("BootHeel", (0.155, 0.075, 0.028), (sx * 0.095, 0.075, 0.022), SOLE))
    P += both(legs)

    # ---- arms: skin all the way, with a shirt sleeve rolled to below the elbow
    arms = []
    arms.append(sweep("Arm",
                      [(0.195, 0.0, 1.398), (0.265, 0.005, 1.280), (0.345, 0.01, 1.145),
                       (0.405, 0.018, 1.025), (0.462, 0.025, 0.905)],
                      [(0.062, 0.062), (0.054, 0.054), (0.047, 0.047), (0.044, 0.046), (0.036, 0.040)],
                      SKIN, segments=14))
    arms.append(sweep("Sleeve",
                      [(0.186, 0.0, 1.398), (0.248, 0.004, 1.318), (0.302, 0.008, 1.222),
                       (0.345, 0.011, 1.145), (0.368, 0.013, 1.098)],
                      [(0.079, 0.077), (0.074, 0.073), (0.069, 0.069), (0.064, 0.064), (0.062, 0.062)],
                      SHIRT, segments=14, caps=(True, False)))
    arms.append(uvsphere("Deltoid", 0.082, (0.182, 0.0, 1.398), SHIRT, segments=14, rings=9,
                         scale=(1.0, 0.95, 0.92)))
    arms.append(sweep("SleeveRoll",
                      [(0.352, 0.011, 1.128), (0.372, 0.013, 1.088), (0.385, 0.015, 1.062)],
                      [(0.064, 0.064), (0.069, 0.069), (0.058, 0.058)], CUFF, segments=14, caps=(False, True)))
    # hand: a soft mitt with a thumb, hanging slightly open as in the concept
    hand = sweep("Hand",
                 [(0.468, 0.026, 0.890), (0.487, 0.022, 0.845), (0.500, 0.018, 0.805), (0.505, 0.014, 0.775)],
                 [(0.034, 0.040), (0.044, 0.050), (0.044, 0.048), (0.034, 0.036)], SKIN, segments=12)
    arms.append(hand)
    arms.append(sweep("Thumb", [(0.455, -0.012, 0.858), (0.455, -0.030, 0.822), (0.458, -0.036, 0.800)],
                      [(0.019, 0.019), (0.017, 0.017), (0.013, 0.013)], SKIN, segments=8))
    for i, off in enumerate((-0.020, -0.006, 0.008, 0.021)):
        length = (0.040, 0.046, 0.044, 0.036)[i]
        arms.append(sweep(f"Finger{i}",
                          [(0.502 + off * 0.25, 0.014 + off, 0.780), (0.506 + off * 0.3, 0.016 + off, 0.780 - length)],
                          [(0.013, 0.013), (0.011, 0.011)], SKIN, segments=7))
    P += both(arms)

    # ---- head: a broad skull with a heavy jaw, deep-set eyes and a full grey beard
    HC = Vector((0, 0.004, 1.592))
    skull = uvsphere("Skull", 0.112, HC, SKIN, segments=24, rings=15, scale=(0.95, 1.06, 1.18))
    shape_verts(skull, lambda v, c=HC: Vector((
        v.x * (1.0 + 0.09 * max(0.0, -(v.z - c.z) / 0.13)),
        v.y * (0.90 if v.y > 0 else 1.0) + (0.008 if v.y > 0 else 0.0),
        v.z)))
    P.append(skull)
    P.append(uvsphere("Jaw", 0.082, HC + Vector((0, -0.020, -0.074)), SKIN, segments=18, rings=11,
                      scale=(1.08, 1.00, 0.70)))
    P.append(uvsphere("Nose", 0.027, HC + Vector((0, -0.098, 0.004)), SKIN, segments=16, rings=10,
                      scale=(0.70, 1.30, 1.05)))
    P.append(uvsphere("NoseTip", 0.019, HC + Vector((0, -0.119, -0.014)), SKIN, segments=14, rings=9,
                      scale=(1.05, 0.85, 0.85)))
    P += both([uvsphere("Ear", 0.032, HC + Vector((0.110, 0.010, -0.006)), SKIN, segments=12, rings=8,
                        scale=(0.36, 0.70, 1.20))])
    P += both([uvsphere("Cheek", 0.034, HC + Vector((0.056, -0.070, -0.020)), SKIN, segments=12, rings=8,
                        scale=(0.90, 0.55, 0.58))])

    eyes = []
    for sx in (1,):
        ec = HC + Vector((sx * 0.047, -0.090, 0.028))
        eyes += eye("Eye", ec, 0.0195, WHITE, IRIS, PUPIL, look=(0, -1, 0.05), iris_scale=0.60)
        eyes.append(uvsphere("Lid", 0.0208, ec + Vector((0, 0.001, 0.014)), SKIN, segments=14, rings=8,
                             scale=(1.06, 1.0, 0.56)))
        eyes.append(uvsphere("EyeBag", 0.019, ec + Vector((0, 0.002, -0.019)), SKIN, segments=12, rings=7,
                             scale=(1.08, 0.85, 0.42)))
        eyes.append(brow("Brow", HC + Vector((sx * 0.049, -0.098, 0.054)), 0.040, 0.0095, HAIR, tilt=-7 * sx))
    P += both(eyes)

    # moustache above the mouth, beard below it, sideburns up to the ears
    P.append(uvsphere("Moustache", 0.036, HC + Vector((0, -0.100, -0.030)), HAIR, segments=16, rings=9,
                      scale=(1.00, 0.60, 0.26)))
    beard = uvsphere("Beard", 0.086, HC + Vector((0, -0.030, -0.078)), HAIR, segments=20, rings=12,
                     scale=(1.04, 1.10, 0.84))
    shape_verts(beard, lambda v, top=HC.z - 0.042: Vector((
        v.x, v.y, v.z if v.z < top else top + (v.z - top) * 0.10)))
    P.append(beard)
    P += both([uvsphere("Sideburn", 0.024, HC + Vector((0.098, -0.034, -0.030)), HAIR, segments=12, rings=8,
                        scale=(0.45, 1.20, 1.45))])
    mouth_pts = arc_path((0, -0.096, HC.z - 0.046), 0.025, 203, 337, steps=9, plane="xz", squash=0.42)
    P.append(sweep("Mouth", mouth_pts, [0.004] + [0.0065] * 7 + [0.004], MOUTH, segments=6))

    # grey hair under the cap, then the flat cap and its brim
    for i in range(14):
        a = math.radians(-92 + 184 * i / 13)
        r = 0.106
        P.append(uvsphere(f"Hair{i}", 0.027, HC + Vector((math.sin(a) * r, math.cos(a) * r * 1.04 + 0.012, 0.028)),
                          HAIR, segments=10, rings=6, scale=(1.1, 1.1, 0.85)))
    cap = uvsphere("Cap", 0.132, HC + Vector((0, 0.016, 0.110)), CAP, segments=24, rings=13,
                   scale=(1.0, 1.06, 0.55))
    shape_verts(cap, lambda v, bottom=HC.z + 0.064: Vector((v.x, v.y, max(v.z, bottom))))
    P.append(cap)
    brim = uvsphere("Brim", 1.0, HC + Vector((0, -0.062, 0.074)), CAP, segments=20, rings=10,
                    scale=(0.084, 0.064, 0.0075))
    shape_verts(brim, lambda v, back=HC.y - 0.016: Vector((
        v.x, min(v.y, back), v.z - (v.x / 0.084) ** 2 * 0.014)))
    P.append(brim)

    body = join("GardenMan", P)
    shade_flat_edges(body)
    _finish(body, J, "garden_man", clips=_gardener_clips())


def _gardener_clips():
    """Animations the game asks for by name, plus the hoeing loop for the garden."""
    return {
        "idle": (96, False, {
            "spine": rig.breathe("spine", 96, 1.1),
            "chest": rig.breathe("chest", 96, 1.5, phase=0.4),
            "head": [(0, (2, 0, 0)), (32, (1, 3, 1)), (64, (3, -2, -1))],
            "upperarm.L": [(0, (0, 0, 2)), (48, (0, 0, 4))],
            "upperarm.R": [(0, (0, 0, -2)), (48, (0, 0, -4))],
        }),
        "talking": (72, False, {
            "head": [(0, (0, 0, 0)), (10, (-5, 4, 0)), (24, (3, -3, -2)), (38, (-4, -1, 1)),
                     (52, (2, 5, 2)), (64, (-2, 0, 0))],
            "neck": [(0, (0, 0, 0)), (18, (3, 0, 0)), (40, (-2, 0, 0)), (60, (2, 0, 0))],
            "chest": [(0, (0, 0, 0)), (24, (-2, 2, 0)), (50, (1, -2, 0))],
            "upperarm.L": [(0, (0, 0, 0)), (20, (-14, 0, 6)), (40, (-4, 0, 2)), (58, (-11, 0, 5))],
            "forearm.L": [(0, (0, 0, 0)), (20, (-24, 0, 0)), (40, (-8, 0, 0)), (58, (-20, 0, 0))],
            "hand.L": [(0, (0, 0, 0)), (20, (10, 0, 0)), (44, (-6, 0, 0))],
        }),
        "laughing": (48, False, {
            "head": [(0, (0, 0, 0)), (8, (-16, 0, 0)), (16, (-11, 0, 0)), (24, (-17, 0, 0)),
                     (32, (-12, 0, 0)), (40, (-15, 0, 0))],
            "neck": [(0, (0, 0, 0)), (8, (-7, 0, 0)), (24, (-5, 0, 0)), (40, (-7, 0, 0))],
            "chest": [(0, (0, 0, 0)), (8, (5, 0, 0)), (14, (2, 0, 0)), (20, (5, 0, 0)),
                      (26, (2, 0, 0)), (32, (5, 0, 0)), (40, (3, 0, 0))],
            "spine": [(0, (0, 0, 0)), (12, (3, 0, 0)), (28, (1, 0, 0)), (40, (3, 0, 0))],
            "upperarm.L": [(0, (0, 0, 0)), (12, (-8, 0, 9)), (28, (-4, 0, 6)), (40, (-7, 0, 8))],
            "upperarm.R": [(0, (0, 0, 0)), (12, (-8, 0, -9)), (28, (-4, 0, -6)), (40, (-7, 0, -8))],
        }),
        "wave": (56, False, {
            "upperarm.R": [(0, (0, 0, 0)), (14, (-62, 0, -26)), (44, (-62, 0, -26)), (56, (0, 0, 0))],
            "forearm.R": [(0, (0, 0, 0)), (14, (-40, 0, 0)), (22, (-40, 24, 0)), (30, (-40, -18, 0)),
                          (38, (-40, 22, 0)), (46, (-38, 0, 0)), (56, (0, 0, 0))],
            "hand.R": [(0, (0, 0, 0)), (20, (0, 14, 0)), (34, (0, -12, 0)), (46, (0, 0, 0))],
            "head": [(0, (0, 0, 0)), (18, (-3, -6, 0)), (44, (-3, -6, 0)), (56, (0, 0, 0))],
        }),
        "hoeing": (72, False, {
            "spine": [(0, (12, 0, 0)), (18, (18, 0, 0)), (36, (12, 0, 0)), (54, (17, 0, 0))],
            "chest": [(0, (6, 0, 0)), (18, (10, 0, 0)), (36, (6, 0, 0)), (54, (9, 0, 0))],
            "head": [(0, (8, 0, 0)), (36, (11, 0, 0))],
            "upperarm.L": [(0, (-30, 0, 10)), (18, (-54, 0, 12)), (36, (-30, 0, 10)), (54, (-50, 0, 12))],
            "forearm.L": [(0, (-26, 0, 0)), (18, (-10, 0, 0)), (36, (-26, 0, 0)), (54, (-12, 0, 0))],
            "upperarm.R": [(0, (-44, 0, -12)), (18, (-66, 0, -14)), (36, (-44, 0, -12)), (54, (-62, 0, -14))],
            "forearm.R": [(0, (-32, 0, 0)), (18, (-14, 0, 0)), (36, (-32, 0, 0)), (54, (-16, 0, 0))],
        }),
    }


# ============================================================================= Harold
def harold():
    """Slim bookish graduate student: horn-rimmed glasses, white tee, running shorts. 1.78 m."""
    J = {
        "toe": Vector((0.088, -0.150, 0.035)),
        "ankle": Vector((0.088, 0.012, 0.095)),
        "knee": Vector((0.097, 0.0, 0.480)),
        "hip_joint": Vector((0.097, 0.0, 0.945)),
        "hip": Vector((0.0, 0.0, 0.97)),
        "waist": Vector((0.0, 0.0, 1.13)),
        "chest": Vector((0.0, 0.0, 1.31)),
        "neck": Vector((0.0, 0.0, 1.465)),
        "chin": Vector((0.0, 0.0, 1.545)),
        "skull": Vector((0.0, 0.0, 1.77)),
        "shoulder": Vector((0.185, 0.0, 1.445)),
        "elbow": Vector((0.300, 0.01, 1.180)),
        "wrist": Vector((0.395, 0.022, 0.915)),
        "fingers": Vector((0.425, 0.026, 0.810)),
    }

    SKIN = mat("HSkin", (0.91, 0.73, 0.61), rough=0.7)
    TEE = mat("Tee", (0.93, 0.92, 0.90), rough=0.95)
    SHORTS = mat("Shorts", (0.19, 0.23, 0.36), rough=0.9)
    PIPING = mat("Piping", (0.95, 0.95, 0.94), rough=0.85)
    SOCK = mat("Sock", (0.95, 0.95, 0.93), rough=0.95)
    SHOE = mat("Shoe", (0.90, 0.89, 0.86), rough=0.9)
    RUBBER = mat("ShoeRubber", (0.94, 0.93, 0.90), rough=0.75)
    STRIPE = mat("ShoeStripe", (0.17, 0.21, 0.35), rough=0.8)
    LACE = mat("Lace", (0.96, 0.96, 0.94), rough=0.9)
    HAIR = mat("HHair", (0.35, 0.23, 0.15), rough=0.85)
    FRAME = mat("Frame", (0.13, 0.11, 0.10), rough=0.4)
    WHITE = mat("HEyeWhite", (0.95, 0.95, 0.93), rough=0.2)
    IRIS = mat("HIris", (0.33, 0.22, 0.14), rough=0.18)
    PUPIL = mat("HPupil", (0.05, 0.05, 0.06), rough=0.2)
    MOUTH = mat("HMouth", (0.52, 0.29, 0.26), rough=0.5)

    P = []

    # ---- torso under a loose t-shirt
    P.append(sweep("Tee",
                   [(0, 0.004, 0.955), (0, 0.004, 1.05), (0, 0.002, 1.16), (0, -0.002, 1.27),
                    (0, -0.004, 1.38), (0, -0.002, 1.44), (0, 0, 1.475)],
                   [(0.158, 0.106), (0.158, 0.106), (0.158, 0.105), (0.164, 0.104),
                    (0.172, 0.103), (0.176, 0.100), (0.108, 0.086)],
                   TEE, segments=18, caps=(True, False)))
    P.append(sweep("HNeck", [(0, 0, 1.425), (0, 0, 1.55)], [(0.052, 0.050), (0.049, 0.047)], SKIN, segments=14))
    P.append(sweep("TeeCollar", [(0, 0, 1.462), (0, 0, 1.488)], [(0.072, 0.067), (0.068, 0.063)],
                   TEE, segments=16, caps=(False, False)))

    # ---- shorts with white piping, bare legs, socks and canvas sneakers
    P.append(sweep("Waistband", [(0, 0.004, 1.035), (0, 0.004, 1.085)],
                   [(0.158, 0.113), (0.157, 0.112)], SHORTS, segments=18, caps=(False, True)))
    P.append(sweep("Hips", [(0, 0.004, 0.845), (0, 0.004, 0.94), (0, 0.004, 1.04)],
                   [(0.138, 0.102), (0.150, 0.108), (0.158, 0.113)], SHORTS, segments=18, caps=(True, False)))
    legs = []
    for sx in (1,):
        legs.append(sweep("ShortsLeg",
                          [(sx * 0.072, 0.004, 0.96), (sx * 0.080, 0.002, 0.87), (sx * 0.084, 0.0, 0.805)],
                          [(0.086, 0.094), (0.085, 0.092), (0.082, 0.088)], SHORTS, segments=14))
        legs.append(sweep("Piping",
                          [(sx * 0.0842, 0.0, 0.8125), (sx * 0.0842, 0.0, 0.8015)],
                          [(0.0845, 0.0905), (0.0845, 0.0905)], PIPING, segments=14, caps=(False, False)))
        legs.append(sweep("Leg",
                          [(sx * 0.092, 0.002, 0.825), (sx * 0.095, 0.0, 0.66), (sx * 0.097, -0.002, 0.49),
                           (sx * 0.093, 0.004, 0.37), (sx * 0.090, 0.008, 0.25)],
                          [(0.070, 0.072), (0.058, 0.060), (0.047, 0.049), (0.047, 0.050), (0.036, 0.038)],
                          SKIN, segments=14))
        legs.append(sweep("Sock",
                          [(sx * 0.089, 0.009, 0.255), (sx * 0.088, 0.011, 0.185), (sx * 0.088, 0.012, 0.115)],
                          [(0.040, 0.042), (0.040, 0.042), (0.040, 0.043)], SOCK, segments=14))
        shoe = sweep("Shoe",
                     [(sx * 0.088, 0.075, 0.095), (sx * 0.088, 0.02, 0.085), (sx * 0.088, -0.045, 0.078),
                      (sx * 0.088, -0.105, 0.068), (sx * 0.088, -0.142, 0.058)],
                     [(0.044, 0.050), (0.049, 0.048), (0.049, 0.045), (0.044, 0.040), (0.032, 0.030)],
                     SHOE, segments=14)
        legs.append(shoe)
        legs.append(sweep("ShoeToe",
                          [(sx * 0.088, -0.100, 0.060), (sx * 0.088, -0.140, 0.052), (sx * 0.088, -0.158, 0.044)],
                          [(0.047, 0.042), (0.038, 0.034), (0.024, 0.024)], RUBBER, segments=12))
        legs.append(box("ShoeSole", (0.100, 0.245, 0.022), (sx * 0.088, -0.030, 0.034), RUBBER))
        legs.append(box("ShoeStripe", (0.104, 0.245, 0.006), (sx * 0.088, -0.030, 0.049), STRIPE))
        for i, y in enumerate((-0.02, -0.05, -0.08)):
            legs.append(box(f"Lace{i}", (0.052, 0.009, 0.007), (sx * 0.088, y, 0.100), LACE))
    P += both(legs)

    # ---- arms with short tee sleeves
    arms = []
    arms.append(sweep("HArm",
                      [(0.166, 0.0, 1.438), (0.236, 0.005, 1.310), (0.300, 0.01, 1.180),
                       (0.350, 0.016, 1.048), (0.392, 0.022, 0.918)],
                      [(0.050, 0.050), (0.042, 0.042), (0.036, 0.036), (0.033, 0.034), (0.027, 0.029)],
                      SKIN, segments=14))
    arms.append(sweep("HSleeve",
                      [(0.158, 0.0, 1.440), (0.200, 0.003, 1.382), (0.236, 0.006, 1.318)],
                      [(0.066, 0.065), (0.061, 0.060), (0.055, 0.054)], TEE, segments=14, caps=(True, True)))
    arms.append(uvsphere("HDeltoid", 0.062, (0.158, 0.0, 1.424), TEE, segments=14, rings=9,
                         scale=(1.0, 0.98, 0.95)))
    arms.append(sweep("HHand",
                      [(0.396, 0.023, 0.912), (0.412, 0.020, 0.868), (0.422, 0.016, 0.830),
                       (0.424, 0.013, 0.802)],
                      [(0.026, 0.031), (0.034, 0.040), (0.034, 0.038), (0.026, 0.028)], SKIN, segments=12))
    arms.append(sweep("HThumb", [(0.386, -0.012, 0.882), (0.384, -0.028, 0.850), (0.386, -0.033, 0.830)],
                      [(0.015, 0.015), (0.013, 0.013), (0.010, 0.010)], SKIN, segments=8))
    for i, off in enumerate((-0.016, -0.005, 0.006, 0.016)):
        length = (0.034, 0.039, 0.037, 0.030)[i]
        arms.append(sweep(f"HFinger{i}",
                          [(0.421 + off * 0.2, 0.013 + off, 0.806), (0.424 + off * 0.25, 0.015 + off, 0.806 - length)],
                          [(0.0105, 0.0105), (0.009, 0.009)], SKIN, segments=7))
    P += both(arms)

    # ---- head: narrower than the gardener's, with a soft jaw
    HC = Vector((0, 0.002, 1.662))
    skull = uvsphere("HSkull", 0.103, HC, SKIN, segments=22, rings=14, scale=(0.97, 1.05, 1.21))
    shape_verts(skull, lambda v, c=HC: Vector((
        v.x * (1.0 - 0.18 * max(0.0, -(v.z - c.z) / 0.12)),
        v.y, v.z)))
    P.append(skull)
    P.append(uvsphere("HJaw", 0.060, HC + Vector((0, -0.020, -0.070)), SKIN, segments=16, rings=10,
                      scale=(1.02, 1.05, 0.72)))
    P.append(uvsphere("HNose", 0.021, HC + Vector((0, -0.092, -0.014)), SKIN, segments=14, rings=9,
                      scale=(0.80, 1.35, 1.05)))
    ears = [uvsphere("HEar", 0.027, HC + Vector((0.100, 0.010, -0.010)), SKIN, segments=12, rings=8,
                     scale=(0.34, 0.68, 1.15))]
    P += both(ears)

    eyes = []
    for sx in (1,):
        ec = HC + Vector((sx * 0.042, -0.074, 0.022))
        eyes += eye("HEye", ec, 0.0215, WHITE, IRIS, PUPIL, look=(0, -1, 0.04), iris_scale=0.56)
        eyes.append(uvsphere("HLid", 0.0225, ec + Vector((0, -0.002, 0.012)), SKIN, segments=14, rings=8,
                             scale=(1.06, 1.0, 0.48)))
        eyes.append(brow("HBrow", HC + Vector((sx * 0.044, -0.092, 0.048)), 0.038, 0.0080, HAIR,
                         tilt=-5 * sx))
    P += both(eyes)

    mouth_pts = arc_path((0, -0.086, HC.z - 0.058), 0.024, 207, 333, steps=9, plane="xz", squash=0.40)
    P.append(sweep("HMouth", mouth_pts, [0.003] + [0.0045] * 7 + [0.003], MOUTH, segments=6))

    # ---- wavy brown hair: a shell over the skull plus tufts at the crown
    hair = uvsphere("HHairShell", 0.108, HC + Vector((0, 0.006, 0.014)), HAIR, segments=22, rings=14,
                    scale=(0.98, 1.05, 1.14))
    shape_verts(hair, lambda v, c=HC + Vector((0, 0.006, 0.016)): Vector((
        v.x, v.y,
        v.z if v.z > c.z - 0.012 else c.z - 0.012 - (c.z - 0.012 - v.z) * 0.08)))
    shape_verts(hair, lambda v, c=HC: v if v.y > -0.03 else Vector((
        v.x, v.y, min(v.z, c.z + 0.062 - abs(v.x) * 0.20))))
    P.append(hair)
    import random
    random.seed(1964)
    for i in range(12):
        a = math.radians(-96 + 192 * i / 11)
        r = 0.055 + random.uniform(-0.006, 0.010)
        P.append(uvsphere(f"HTuft{i}", random.uniform(0.024, 0.032),
                          HC + Vector((math.sin(a) * r, math.cos(a) * r * 1.10 + 0.014,
                                       0.078 + random.uniform(-0.010, 0.012))),
                          HAIR, segments=10, rings=7, scale=(1.0, 1.0, 0.62)))

    # ---- thick horn-rimmed glasses
    for sx in (-1, 1):
        rim = []
        for i in range(22):
            a = 2 * math.pi * i / 22
            # horn-rims: wider than tall, with softened square corners
            cx = math.copysign(abs(math.cos(a)) ** 0.70, math.cos(a))
            cz = math.copysign(abs(math.sin(a)) ** 0.70, math.sin(a))
            rim.append(Vector((sx * 0.043 + cx * 0.034, -0.100 - abs(cz) * 0.004, HC.z + 0.022 + cz * 0.024)))
        rim.append(rim[0])
        P.append(sweep(f"Rim{sx}", rim, [0.0052] * len(rim), FRAME, segments=6, caps=(False, False)))
        P.append(sweep(f"Temple{sx}",
                       [(sx * 0.075, -0.096, HC.z + 0.030), (sx * 0.100, -0.040, HC.z + 0.028),
                        (sx * 0.106, 0.034, HC.z + 0.014)],
                       [(0.0045, 0.0045), (0.004, 0.004), (0.0035, 0.0035)], FRAME, segments=6))
    P.append(sweep("Bridge", [(-0.012, -0.102, HC.z + 0.032), (0, -0.105, HC.z + 0.036),
                              (0.012, -0.102, HC.z + 0.032)],
                   [(0.0045, 0.0045), (0.005, 0.005), (0.0045, 0.0045)], FRAME, segments=6))

    body = join("Harold", P)
    shade_flat_edges(body)
    _finish(body, J, "harold", clips=_harold_clips())


def _harold_clips():
    return {
        "idle": (96, False, {
            "spine": rig.breathe("spine", 96, 0.9),
            "chest": rig.breathe("chest", 96, 1.3, phase=0.4),
            "head": [(0, (0, 0, 0)), (30, (-2, 4, 1)), (62, (2, -3, -1))],
            "upperarm.L": [(0, (0, 0, 1)), (48, (0, 0, 3))],
            "upperarm.R": [(0, (0, 0, -1)), (48, (0, 0, -3))],
        }),
        "walk": (32, True, {
            "thigh.L": [(0, (26, 0, 0)), (8, (6, 0, 0)), (16, (-22, 0, 0)), (24, (4, 0, 0))],
            "thigh.R": [(0, (-22, 0, 0)), (8, (4, 0, 0)), (16, (26, 0, 0)), (24, (6, 0, 0))],
            "shin.L": [(0, (-6, 0, 0)), (8, (-30, 0, 0)), (16, (-4, 0, 0)), (24, (-16, 0, 0))],
            "shin.R": [(0, (-4, 0, 0)), (8, (-16, 0, 0)), (16, (-6, 0, 0)), (24, (-30, 0, 0))],
            "foot.L": [(0, (-12, 0, 0)), (8, (6, 0, 0)), (16, (12, 0, 0)), (24, (0, 0, 0))],
            "foot.R": [(0, (12, 0, 0)), (8, (0, 0, 0)), (16, (-12, 0, 0)), (24, (6, 0, 0))],
            "hips": [(0, (2, 4, 0)), (8, (2, 0, 0)), (16, (2, -4, 0)), (24, (2, 0, 0))],
            "chest": [(0, (0, -3, 0)), (16, (0, 3, 0))],
            "upperarm.L": [(0, (22, 0, 4)), (16, (-20, 0, 4))],
            "upperarm.R": [(0, (-20, 0, -4)), (16, (22, 0, -4))],
            "forearm.L": [(0, (-14, 0, 0)), (16, (-22, 0, 0))],
            "forearm.R": [(0, (-22, 0, 0)), (16, (-14, 0, 0))],
            "head": [(0, (-1, -2, 0)), (16, (-1, 2, 0))],
        }),
        "run": (22, True, {
            "thigh.L": [(0, (48, 0, 0)), (6, (10, 0, 0)), (11, (-32, 0, 0)), (17, (6, 0, 0))],
            "thigh.R": [(0, (-32, 0, 0)), (6, (6, 0, 0)), (11, (48, 0, 0)), (17, (10, 0, 0))],
            "shin.L": [(0, (-26, 0, 0)), (6, (-66, 0, 0)), (11, (-8, 0, 0)), (17, (-44, 0, 0))],
            "shin.R": [(0, (-8, 0, 0)), (6, (-44, 0, 0)), (11, (-26, 0, 0)), (17, (-66, 0, 0))],
            "foot.L": [(0, (-18, 0, 0)), (11, (16, 0, 0))],
            "foot.R": [(0, (16, 0, 0)), (11, (-18, 0, 0))],
            "hips": [(0, (8, 6, 0)), (11, (8, -6, 0))],
            "spine": [(0, (6, 0, 0))],
            "chest": [(0, (0, -6, 0)), (11, (0, 6, 0))],
            "upperarm.L": [(0, (46, 0, 8)), (11, (-34, 0, 8))],
            "upperarm.R": [(0, (-34, 0, -8)), (11, (46, 0, -8))],
            "forearm.L": [(0, (-62, 0, 0)), (11, (-48, 0, 0))],
            "forearm.R": [(0, (-48, 0, 0)), (11, (-62, 0, 0))],
            "head": [(0, (-3, -2, 0)), (11, (-3, 2, 0))],
        }),
        "talking": (72, False, {
            "head": [(0, (0, 0, 0)), (12, (-4, -5, -1)), (28, (3, 3, 1)), (44, (-3, 2, 0)), (60, (2, -4, -1))],
            "neck": [(0, (0, 0, 0)), (20, (2, 0, 0)), (46, (-2, 0, 0))],
            "chest": [(0, (0, 0, 0)), (26, (-1, -2, 0)), (52, (1, 2, 0))],
            "upperarm.L": [(0, (0, 0, 0)), (16, (-20, 0, 8)), (36, (-8, 0, 3)), (56, (-16, 0, 6))],
            "forearm.L": [(0, (0, 0, 0)), (16, (-34, 0, 0)), (36, (-14, 0, 0)), (56, (-28, 0, 0))],
            "hand.L": [(0, (0, 0, 0)), (16, (14, 0, 0)), (40, (-8, 0, 0))],
            "upperarm.R": [(0, (0, 0, 0)), (24, (-10, 0, -5)), (52, (-4, 0, -2))],
        }),
        "writing": (84, False, {
            "upperarm.L": [(0, (-52, 0, 16)), (84, (-52, 0, 16))],
            "forearm.L": [(0, (-74, 0, 0)), (84, (-74, 0, 0))],
            "upperarm.R": [(0, (-46, 0, -20)), (20, (-48, 0, -18)), (40, (-45, 0, -22)), (62, (-48, 0, -17))],
            "forearm.R": [(0, (-80, 0, 0)), (20, (-74, 0, 0)), (40, (-82, 0, 0)), (62, (-75, 0, 0))],
            "hand.R": [(0, (0, 0, 0)), (14, (0, 7, 0)), (30, (0, -5, 0)), (48, (0, 8, 0)), (66, (0, -4, 0))],
            "head": [(0, (14, 0, 0)), (40, (16, -2, 0))],
            "neck": [(0, (8, 0, 0))],
            "spine": [(0, (5, 0, 0))],
        }),
    }


# ============================================================================= shared
def shade_flat_edges(obj, angle_degrees: float = 38.0) -> None:
    """Smooth shading with an auto-smooth angle: round limbs stay smooth, creases stay crisp."""
    shade_smooth(obj)
    mod = obj.modifiers.new("Smooth by Angle", "SMOOTH_BY_ANGLE") if "SMOOTH_BY_ANGLE" in {
        i.identifier for i in bpy.types.Modifier.bl_rna.properties["type"].enum_items} else None
    if mod is not None:
        mod.angle = math.radians(angle_degrees)
    elif hasattr(obj.data, "use_auto_smooth"):
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(angle_degrees)


def _finish(body, joints, name, clips) -> None:
    skeleton = build_armature(joints)
    bind(body, skeleton)
    for clip_name, (frames, loop, tracks) in clips.items():
        clip(skeleton, clip_name, frames, tracks, loop=loop)
    bpy.context.scene.frame_set(0)
    if skeleton.animation_data:
        skeleton.animation_data.action = bpy.data.actions.get("idle")

    folder = ASSETS / "characters" / name
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / "rigged.glb"
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", use_selection=False,
                              export_apply=False, export_yup=True, export_animation_mode="ACTIONS",
                              export_image_format="AUTO")
    faces = len(body.data.polygons)
    print(f"EXPORTED {out.relative_to(ROOT)}  faces={faces}  clips={list(clips)}")
    if os.environ.get("NO_PREVIEW") != "1":
        for label, yaw in (("front", 0), ("three_quarter", 32), ("side", 90)):
            render_preview(folder / f"preview_{label}.png", yaw, size=720)
        head = joints["skull"]
        render_preview(folder / "preview_face.png", 14, size=720,
                       focus=Vector((0, 0, head.z - 0.115)), frame_radius=0.175)


BUILDERS = {"garden_man": garden_man, "harold": harold}

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["garden_man"]
    reset()
    BUILDERS[args[0]]()
