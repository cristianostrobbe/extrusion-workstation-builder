"""FreeCAD model of the 3D-printer workstation (3030 frame, no doors).

Headless:  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd cad/workstation.py
In GUI:    Macro > Execute macro... (also applies colors)
Writes cad/workstation.FCStd and cad/workstation.step next to this file.
Dimensions match frame_bom.py / BOM.md (mm). X = width, Y = depth, Z = up.
"""
import os
import FreeCAD as App
import Part
from FreeCAD import Vector, Rotation, Placement

# --- parameters (keep in sync with frame_bom.py) ---
P = 30.0           # profile size (3030, 8 mm slot)
LEFT_IN = 420.0    # clear width of tower bay
RIGHT_IN = 420.0   # clear width of right bay (same as left, so it also takes a P1S)
RIGHT_TOWER = True # right bay also rises to TOTAL_H as a second printer tower
DEPTH = 420.0      # P1S body 389 mm + margin
LOW_H = 600.0      # lower frame height (post bottom to top of the deck beam)
TOTAL_H = 1150.0   # tower frame height: 508 mm clear above the deck panel
CASTER_H = 71.0    # DEPN-W2-40-N mounting height
ENDCAP_H = 24.0    # TPRE-G306-3030-M8 adds 24 mm below the post
BOTTOM_Z = 60.0    # bottom beams raised so their brackets clear the TPRE clamp
PANEL_T = 12.0

OUT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()

doc = App.newDocument("Workstation")


def profile_face(p=P):
    """Simplified EU 30-series section: square, 4 T-slots (8 mm opening), centre bore."""
    h = p / 2
    face = Part.makePlane(p, p, Vector(-h, -h, 0))
    lip, slot_w, cav_w, cav_d = 2.2, 8.2, 16.5, 7.0   # slot depth 9.2 mm
    cutters = []
    for rot in (0, 90, 180, 270):
        opening = Part.makePlane(slot_w, lip + 0.01, Vector(-slot_w / 2, h - lip, 0))
        cavity = Part.makePlane(cav_w, cav_d, Vector(-cav_w / 2, h - lip - cav_d, 0))
        for f in (opening, cavity):
            f.rotate(Vector(0, 0, 0), Vector(0, 0, 1), rot)
            cutters.append(f)
    cutters.append(Part.Face(Part.Wire(Part.makeCircle(3.4))))
    for c in cutters:
        face = face.cut(c)
    return face


SECTION = profile_face()


def member(name, length, axis, x, y, z, group):
    """Profile of `length` along axis 'x'|'y'|'z'; (x, y, z) = min corner of its bounding box."""
    s = SECTION.extrude(Vector(0, 0, length))
    if axis == "x":
        s.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 90)
    elif axis == "y":
        s.rotate(Vector(0, 0, 0), Vector(1, 0, 0), -90)
    bb = s.BoundBox
    s.translate(Vector(x - bb.XMin, y - bb.YMin, z - bb.ZMin))
    o = doc.addObject("Part::Feature", name)
    o.Shape = s
    o.addProperty("App::PropertyLength", "CutLength", "BoM").CutLength = length
    group.addObject(o)
    return o


def box(name, sx, sy, sz, x, y, z, group):
    o = doc.addObject("Part::Feature", name)
    o.Shape = Part.makeBox(sx, sy, sz, Vector(x, y, z))
    group.addObject(o)
    return o


g_frame = doc.addObject("App::DocumentObjectGroup", "Frame_3030")
g_panels = doc.addObject("App::DocumentObjectGroup", "Panels_12mm")
g_hw = doc.addObject("App::DocumentObjectGroup", "Casters")
g_ref = doc.addObject("App::DocumentObjectGroup", "Reference_printers")
g_fast = doc.addObject("App::DocumentObjectGroup", "Brackets_and_fasteners")

z0 = CASTER_H + ENDCAP_H       # underside of the posts
xs = [0.0, P + LEFT_IN, 2 * P + LEFT_IN + RIGHT_IN]      # post x positions (min corner)
ys = [0.0, DEPTH - P]
W = xs[-1] + P

# posts
posts = []
for i, x in enumerate(xs):
    h = TOTAL_H if (i < 2 or RIGHT_TOWER) else LOW_H
    for j, y in enumerate(ys):
        posts.append(member(f"Post_{i}{j}_L{h:.0f}", h, "z", x, y, z0, g_frame))

# beam levels (z of beam bottom, relative to frame bottom)
low_levels = {"Bottom": BOTTOM_Z, "Mid": round(BOTTOM_Z + (LOW_H - P - BOTTOM_Z) / 2), "Deck": LOW_H - P}
bays = [("Left", xs[0] + P, LEFT_IN), ("Right", xs[1] + P, RIGHT_IN)]
for lname, zl in low_levels.items():
    for bname, bx, blen in bays:
        for j, y in enumerate(ys):
            member(f"XBeam_{lname}_{bname}_{'FB'[j]}_L{blen:.0f}", blen, "x", bx, y, z0 + zl, g_frame)
    for i, x in enumerate(xs):
        member(f"YBeam_{lname}_{i}_L{DEPTH - 2 * P:.0f}", DEPTH - 2 * P, "y", x, P, z0 + zl, g_frame)
# tower top(s)
zt = TOTAL_H - P
tower_bays = bays if RIGHT_TOWER else bays[:1]
tower_xs = xs if RIGHT_TOWER else xs[:2]
for bname, bx, blen in tower_bays:
    for j, y in enumerate(ys):
        member(f"XBeam_Top_{bname}_{'FB'[j]}_L{blen:.0f}", blen, "x", bx, y, z0 + zt, g_frame)
for i, x in enumerate(tower_xs):
    member(f"YBeam_Top_{i}_L{DEPTH - 2 * P:.0f}", DEPTH - 2 * P, "y", x, P, z0 + zt, g_frame)

# panels: sit on beam tops, flush with the frame's outer faces.
# Left and right panels meet on the centre line of the middle beam (x_mid).
# Notches are plain rectangles around the posts with CLEAR mm clearance; inside corners get the
# router-bit radius R_IN, outside corners R_OUT. Screw holes on the beam slot centre lines.
CLEAR = 1.0         # clearance panel notch <-> post (also leaves room for the R_IN fillet)
R_IN = 3.0          # inside corner radius (6 mm end mill)
R_OUT = 5.0         # outside corner radius
HOLE_D = 6.5        # clearance hole for M6
CSK_D = 12.5        # 90 deg countersink for DIN 7991 M6 (head 12 mm, sits 0.25 mm below the surface)
x_mid = xs[1] + P / 2
post_boxes = []
for p_ in posts:
    bb = p_.Shape.BoundBox
    post_boxes.append(Part.makeBox(bb.XLength + 2 * CLEAR, bb.YLength + 2 * CLEAR, bb.ZLength,
                                   Vector(bb.XMin - CLEAR, bb.YMin - CLEAR, bb.ZMin)))
PANEL_HOLES = {}


def round_vertical_edges(s, z_mid):
    """Fillet vertical corner edges: concave with R_IN, convex with R_OUT."""
    for radius, want_inside in ((R_IN, 3), (R_OUT, 1)):
        edges = []
        for e in s.Edges:
            v0, v1 = e.Vertexes[0].Point, e.Vertexes[-1].Point
            if not (isinstance(e.Curve, Part.Line) and abs(v0.z - v1.z) > PANEL_T - 0.01):
                continue
            n_in = sum(s.isInside(Vector(v0.x + dx, v0.y + dy, z_mid), 1e-6, True)
                       for dx in (-0.3, 0.3) for dy in (-0.3, 0.3))
            if n_in == want_inside:
                edges.append(e)
        if edges:
            s = s.makeFillet(radius, edges)
    return s


def panel(name, x0, x1, z_top, outer_x):
    s = Part.makeBox(x1 - x0, DEPTH, PANEL_T, Vector(x0, 0, z_top))
    for pb in post_boxes:
        if pb.BoundBox.intersect(s.BoundBox):
            s = s.cut(pb)
    s = round_vertical_edges(s.removeSplitter(), z_top + PANEL_T / 2)
    cx = (x0 + x1) / 2
    holes = [(Vector(cx, P / 2, z_top + PANEL_T), X), (Vector(cx, DEPTH - P / 2, z_top + PANEL_T), X),
             (Vector(outer_x, DEPTH / 2, z_top + PANEL_T), Y)]
    for h, _ in holes:
        s = s.cut(Part.makeCylinder(HOLE_D / 2, PANEL_T, h - Vector(0, 0, PANEL_T)))
        s = s.cut(Part.makeCone(CSK_D / 2, HOLE_D / 2, (CSK_D - HOLE_D) / 2, h, Vector(0, 0, -1)))  # 90 deg countersink
    o = doc.addObject("Part::Feature", name)
    o.Shape = s
    o.addProperty("App::PropertyString", "CutSize", "BoM").CutSize = f"{x1 - x0:.0f} x {DEPTH:.0f} x {PANEL_T:.0f}"
    g_panels.addObject(o)
    PANEL_HOLES[name] = holes


X, Y = Vector(1, 0, 0), Vector(0, 1, 0)
for lname, zl in low_levels.items():
    panel(f"Panel_{lname}_Left", 0, x_mid, z0 + zl + P, P / 2)
    panel(f"Panel_{lname}_Right", x_mid, W, z0 + zl + P, W - P / 2)
panel("Panel_Top_Left", 0, x_mid, z0 + TOTAL_H, P / 2)
if RIGHT_TOWER:
    panel("Panel_Top_Right", x_mid, W, z0 + TOTAL_H, W - P / 2)

# ---------- fasteners ----------
FL_T = 4.5          # TPEA flange thickness
LIP = 2.2           # slot lip thickness
counts = {"bracket": 0, "M6x12": 0, "M6x20CSK": 0, "washer": 0, "tnut": 0}


def prism(origin, a, b, c, la, lb, lc):
    """Box spanned from `origin` by unit vectors a, b, c with lengths la, lb, lc."""
    pts = [origin, origin + a * la, origin + a * la + b * lb, origin + b * lb, origin]
    return Part.Face(Part.makePolygon(pts)).extrude(c * lc)


def screw_set(p0, d, t, clamp_t, length, washer=True, csk=False):
    """Button-head (ISO 7380, + washer) or countersunk (DIN 7991, flush) screw through `clamp_t`
    of material into a TPAH T-nut.
    p0: point on the outer surface of the clamped part, on the screw axis.
    d: unit vector pointing into the profile. t: unit vector along the profile slot."""
    n = d.cross(t)
    parts = []
    if csk:                                                                 # head inside the countersink
        p0 = p0 + d * 0.25
        parts.append(Part.makeCone(6.0, 3.0, 3.0, p0, d))
        parts.append(Part.makeCylinder(3.0, length - 3.0, p0 + d * 3.0, d))
    else:
        w = 1.6 if washer else 0.0
        if washer:
            parts.append(Part.makeCylinder(6.0, w, p0 - d * w, d))
            counts["washer"] += 1
        parts.append(Part.makeCylinder(5.25, 3.3, p0 - d * (w + 3.3), d))  # ISO 7380 M6 head
        parts.append(Part.makeCylinder(3.0, length, p0 - d * w, d))        # shank
    surf = p0 + d * clamp_t                                                 # profile outer face
    parts.append(prism(surf + d * LIP - t * 7.85 - n * 4.0, t, n, d, 15.7, 8.0, 5.0))  # T-nut
    counts["M6x%d%s" % (length, "CSK" if csk else "")] += 1
    counts["tnut"] += 1
    return parts


def bracket(c, eu, ev, name):
    """TPEA-308-3030 under a beam end. c: corner at post face / beam underside / bracket side.
    eu: along the beam away from the post, ev: across the beam (28 mm)."""
    ew = Vector(0, 0, -1)
    outer = Part.Face(Part.makePolygon([c, c + eu * 35, c + ew * 35, c])).extrude(ev * 28)
    ci = c + eu * FL_T + ew * FL_T + ev * 3
    inner = Part.Face(Part.makePolygon([ci, ci + eu * 40, ci + ew * 40, ci])).extrude(ev * 22)
    parts = [outer.cut(inner)]
    mid = ev * 14
    parts += screw_set(c + eu * 20 + mid + ew * FL_T, -ew, eu, FL_T, 12)   # into beam underside
    parts += screw_set(c + eu * FL_T + mid + ew * 20, -eu, -ew, FL_T, 12)  # into post face
    o = doc.addObject("Part::Feature", name)
    o.Shape = Part.makeCompound(parts)
    g_fast.addObject(o)
    counts["bracket"] += 1


levels = [(k, z0 + v) for k, v in low_levels.items()] + [("Top", z0 + zt)]
for lname, zb in levels:
    tower_only = lname == "Top"
    # X beams: brackets at both ends, centred on the beam's depth
    for bname, bx, blen in (tower_bays if tower_only else bays):
        for j, y in enumerate(ys):
            bracket(Vector(bx, y + 1, zb), X, Y, f"Br_{lname}_{bname}{'FB'[j]}_L")
            bracket(Vector(bx + blen, y + 29, zb), -X, -Y, f"Br_{lname}_{bname}{'FB'[j]}_R")
    # Y beams
    for i, x in enumerate(tower_xs if tower_only else xs):
        bracket(Vector(x + 29, P, zb), Y, -X, f"Br_{lname}_Y{i}_F")
        bracket(Vector(x + 1, DEPTH - P, zb), -Y, X, f"Br_{lname}_Y{i}_B")

# panel fixings: 3 per panel, on the slot centre line of the front, back and outer beams
# (no screw on the middle beam: both panels meet over its slot)
for o in g_panels.Group:
    parts = []
    for h, t in PANEL_HOLES[o.Name]:
        parts += screw_set(h, Vector(0, 0, -1), t, PANEL_T, 20, washer=False, csk=True)
    f = doc.addObject("Part::Feature", "Fix_" + o.Name)
    f.Shape = Part.makeCompound(parts)
    g_fast.addObject(f)

# casters + TPRE threaded end caps (each clamped with 2 x M6x12 + T-nut)
for i, x in enumerate(xs):
    for j, y in enumerate(ys):
        cx, cy = x + P / 2, y + P / 2
        body = Part.makeCylinder(25.5, CASTER_H - 10, Vector(cx, cy, 10))
        pad = Part.makeCylinder(20, 10, Vector(cx, cy, 0))
        o = doc.addObject("Part::Feature", f"Caster_{i}{j}")
        o.Shape = body.fuse(pad)
        g_hw.addObject(o)
        boss = Part.makeCylinder(8.25, 10, Vector(cx, cy, CASTER_H))
        base = Part.makeBox(36, 36, 14, Vector(cx - 18, cy - 18, CASTER_H + 10))
        sleeve = Part.makeBox(36, 36, 20, Vector(cx - 18, cy - 18, z0)).cut(
            Part.makeBox(P, P, 20, Vector(x, y, z0)))
        cap = [boss.fuse(base).fuse(sleeve)]
        for sgn in (1, -1):
            cap += screw_set(Vector(cx + sgn * 18, cy, z0 + 9), Vector(-sgn, 0, 0),
                             Vector(0, 0, 1), 3.0, 12, washer=False)
        e = doc.addObject("Part::Feature", f"TPRE_M8_{i}{j}")
        e.Shape = Part.makeCompound(cap)
        g_hw.addObject(e)

# reference envelopes (not part of the BoM)
deck_top = z0 + LOW_H + PANEL_T
for bname, bx, blen in tower_bays:
    box(f"Bambu_P1S_389x389x458_{bname}", 389, 389, 458,
        bx + (blen - 389) / 2, (DEPTH - 389) / 2, deck_top, g_ref)
    box(f"AMS2Pro_372x280x226_{bname}", 372, 280, 226,
        bx + (blen - 372) / 2, (DEPTH - 280) / 2, z0 + TOTAL_H + PANEL_T, g_ref)
if not RIGHT_TOWER:
    box("A1_mini_footprint_347x315x365", 347, 315, 365,
        xs[1] + P + (RIGHT_IN - 347) / 2, (DEPTH - 315) / 2, deck_top, g_ref)

# IKEA SAMLA 11 l reference boxes (39x28x14 cm + 1 cm lid), short side to the front,
# one per lower compartment, standing on the panels.
def samla_11l(name, cx, cy, z):
    W, D, H, T, TAPER, LID = 280.0, 390.0, 140.0, 2.0, 15.0, 10.0

    def rect(w, d, zz):
        return Part.makePolygon([Vector(cx - w / 2, cy - d / 2, zz), Vector(cx + w / 2, cy - d / 2, zz),
                                 Vector(cx + w / 2, cy + d / 2, zz), Vector(cx - w / 2, cy + d / 2, zz),
                                 Vector(cx - w / 2, cy - d / 2, zz)])
    outer = Part.makeLoft([rect(W - 2 * TAPER, D - 2 * TAPER, z), rect(W - 8, D - 8, z + H)], True)
    inner = Part.makeLoft([rect(W - 2 * TAPER - 2 * T, D - 2 * TAPER - 2 * T, z + T),
                           rect(W - 8 - 2 * T, D - 8 - 2 * T, z + H + 1)], True)
    rim = Part.makeBox(W, D, 6, Vector(cx - W / 2, cy - D / 2, z + H - 6)).cut(
        Part.makeBox(W - 8 - 2 * T, D - 8 - 2 * T, 6, Vector(cx - (W - 8) / 2 + T, cy - (D - 8) / 2 + T, z + H - 6)))
    lid = Part.makeBox(W, D, LID, Vector(cx - W / 2, cy - D / 2, z + H))
    o = doc.addObject("Part::Feature", name)
    o.Shape = Part.makeCompound([outer.cut(inner).fuse(rim), lid])
    g_ref.addObject(o)
    return o


samlas = []
for lname in ("Bottom", "Mid"):
    z_panel = z0 + low_levels[lname] + P + PANEL_T
    for bname, bx, blen in bays:
        samlas.append(samla_11l(f"SAMLA_11l_{lname}_{bname}", bx + blen / 2, DEPTH / 2, z_panel))

# IKEA KALLAX 5x5 (182 x 182 x 39 cm, 33.5 cm cubes) standing on the right of the workstation,
# backs aligned to the wall, KALLAX_GAP clear of the frame so the casters can swivel.
# Outer frame 40.5 mm, dividers 16 mm (5 x 335 + 2 x 40.5 + 4 x 16 = 1820). Reference only.
KALLAX_GAP = 40.0
KX, KD, KCELL, KOUT, KIN = 1820.0, 390.0, 335.0, 40.5, 16.0
kx0, ky0 = W + KALLAX_GAP, DEPTH - KD
kallax_shape = Part.makeBox(KX, KD, KX, Vector(kx0, ky0, 0))
cells = []
for ci in range(5):
    for ri in range(5):
        cells.append(Part.makeBox(KCELL, KD + 2, KCELL, Vector(kx0 + KOUT + ci * (KCELL + KIN), ky0 - 1,
                                                                  KOUT + ri * (KCELL + KIN))))
kallax = doc.addObject("Part::Feature", "IKEA_KALLAX_5x5_182x182x39")
kallax.Shape = kallax_shape.cut(Part.makeCompound(cells))
g_ref.addObject(kallax)

# IKEA SKÅDIS 36x56 pegboard example on the tower's left side (reference, not in the BoM).
# Board = 3 mm front plate + 17 mm rim (20 mm deep), rim against the profiles. Hole pattern approximated.
# Fixed with 3 x M6x30 + washer into each of the deck and top Y-beam slots, with a 17 mm printed
# spacer behind the plate at each screw so the plate doesn't bow.
SK_W, SK_H, SK_T, SK_D = 360.0, 560.0, 3.0, 20.0
hw_before = dict(counts)
counts.setdefault("M6x30", 0)
sk_y0 = (DEPTH - SK_W) / 2
sk_z0 = z0 + (LOW_H - P) + (TOTAL_H - (LOW_H - P) - SK_H) / 2      # centred on the tower side face
plate = Part.makeBox(SK_T, SK_W, SK_H, Vector(-SK_D, sk_y0, sk_z0))
rim = Part.makeBox(SK_D - SK_T, SK_W, SK_H, Vector(-SK_D + SK_T, sk_y0, sk_z0)).cut(
    Part.makeBox(SK_D - SK_T, SK_W - 6, SK_H - 6, Vector(-SK_D + SK_T, sk_y0 + 3, sk_z0 + 3)))
screw_y = [sk_y0 + 60, DEPTH / 2, sk_y0 + SK_W - 60]
screw_z = [z0 + LOW_H - P / 2, z0 + TOTAL_H - P / 2]                  # deck and top beam slot centres
slots = []
for ci, yy in enumerate(range(int(sk_y0 + 20), int(sk_y0 + SK_W - 15), 20)):
    for zz in range(int(sk_z0 + 30 + (ci % 2) * 20), int(sk_z0 + SK_H - 40), 40):
        if any(abs(yy - sy) < 14 and abs(zz + 7.5 - sz) < 18 for sy in screw_y for sz in screw_z):
            continue                                                   # keep material around the screws
        slots.append(Part.makeBox(SK_T, 5, 15, Vector(-SK_D, yy - 2.5, zz)))
board = plate.cut(Part.makeCompound(slots)).fuse(rim)
sk_parts = []
for sz in screw_z:
    for sy in screw_y:
        board = board.cut(Part.makeCylinder(3.25, SK_T, Vector(-SK_D, sy, sz), X))
        sk_parts.append(Part.makeCylinder(6.0, SK_D - SK_T, Vector(-SK_D + SK_T, sy, sz), X).cut(
            Part.makeCylinder(3.25, SK_D - SK_T, Vector(-SK_D + SK_T, sy, sz), X)))   # printed spacer
        sk_parts += screw_set(Vector(-SK_D, sy, sz), X, Y, SK_D, 30)
skadis = doc.addObject("Part::Feature", "SKADIS_36x56_Tower_Left")
skadis.Shape = board.removeSplitter()
g_ref.addObject(skadis)
sk_fix = doc.addObject("Part::Feature", "SKADIS_fixings")
sk_fix.Shape = Part.makeCompound(sk_parts)
g_ref.addObject(sk_fix)
skadis_hw = {k: counts[k] - hw_before.get(k, 0) for k in counts if counts[k] - hw_before.get(k, 0)}
counts.clear()
counts.update({k: v for k, v in hw_before.items()})

doc.recompute()

if App.GuiUp:
    import FreeCADGui as Gui
    for o in g_frame.Group:
        o.ViewObject.ShapeColor = (0.78, 0.80, 0.82)
    for o in g_panels.Group:
        o.ViewObject.ShapeColor = (0.82, 0.68, 0.47)
    for o in g_hw.Group:
        o.ViewObject.ShapeColor = (0.15, 0.15, 0.15)
    for o in g_fast.Group:
        o.ViewObject.ShapeColor = (0.55, 0.57, 0.60)
    for o in g_ref.Group:
        o.ViewObject.ShapeColor = (0.2, 0.4, 0.8)
        o.ViewObject.Transparency = 70
    for o in samlas:
        o.ViewObject.ShapeColor = (0.85, 0.90, 0.95)
        o.ViewObject.Transparency = 45
    kallax.ViewObject.ShapeColor = (0.97, 0.97, 0.96)
    kallax.ViewObject.Transparency = 0
    skadis.ViewObject.ShapeColor = (0.96, 0.96, 0.94)
    skadis.ViewObject.Transparency = 0
    sk_fix.ViewObject.ShapeColor = (0.55, 0.57, 0.60)
    sk_fix.ViewObject.Transparency = 0
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()

doc.saveAs(os.path.join(OUT_DIR, "workstation.FCStd"))
Part.export([o for g in (g_frame, g_panels, g_hw, g_fast) for o in g.Group], os.path.join(OUT_DIR, "workstation.step"))

# ---------- DXF cutting files: one per distinct panel shape, viewed from the top ----------
import math


def dxf_entities(face, ox, oy):
    out = []
    for e in face.Edges:
        c = e.Curve
        if isinstance(c, Part.Line) or isinstance(c, Part.LineSegment):
            a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
            out.append(("LINE", 0, 0, a.x - ox, 10, a.y - oy, 11, b.x - ox, 21, b.y - oy))
        elif isinstance(c, Part.Circle):
            cx, cy, r = c.Center.x - ox, c.Center.y - oy, c.Radius
            if e.isClosed():
                out.append(("CIRCLE", 0, 0, cx, 10, cy, 40, r))
            else:
                p1, p2 = e.valueAt(e.FirstParameter), e.valueAt(e.LastParameter)
                if c.Axis.z < 0:
                    p1, p2 = p2, p1
                a1 = math.degrees(math.atan2(p1.y - oy - cy, p1.x - ox - cx)) % 360
                a2 = math.degrees(math.atan2(p2.y - oy - cy, p2.x - ox - cx)) % 360
                out.append(("ARC", 0, 0, cx, 10, cy, 40, r, 50, a1, 51, a2))
        else:
            raise ValueError("unsupported edge " + str(type(c)))
    return out


def write_dxf(path, ents, csk=()):
    """ents on layer CUT (outline + through holes); csk = (x, y) countersink centres, layer CSK90."""
    lines = ["0", "SECTION", "2", "ENTITIES"]
    tagged = [("CUT", e) for e in ents] + [("CSK90_D12.5_TOP", ("CIRCLE", 0, 0, x, 10, y, 40, CSK_D / 2)) for x, y in csk]
    for layer, ent in tagged:
        kind = ent[0]
        lines += ["0", kind, "8", layer]
        if kind == "LINE":
            _, _, _, x1, _, y1, _, x2, _, y2 = ent
            lines += ["10", f"{x1:.3f}", "20", f"{y1:.3f}", "11", f"{x2:.3f}", "21", f"{y2:.3f}"]
        elif kind == "CIRCLE":
            _, _, _, cx, _, cy, _, r = ent
            lines += ["10", f"{cx:.3f}", "20", f"{cy:.3f}", "40", f"{r:.3f}"]
        else:
            _, _, _, cx, _, cy, _, r, _, a1, _, a2 = ent
            lines += ["10", f"{cx:.3f}", "20", f"{cy:.3f}", "40", f"{r:.3f}", "50", f"{a1:.4f}", "51", f"{a2:.4f}"]
    lines += ["0", "ENDSEC", "0", "EOF"]
    open(path, "w").write("\n".join(lines) + "\n")


panel_dir = os.path.join(OUT_DIR, "panels")
os.makedirs(panel_dir, exist_ok=True)
for fn in os.listdir(panel_dir):
    if fn.endswith(".dxf"):
        os.remove(os.path.join(panel_dir, fn))
shapes = {}
def bottom_face(o):
    return min((f for f in o.Shape.Faces if abs(f.normalAt(0, 0).z) > 0.99), key=lambda f: f.CenterOfMass.z)


for o in g_panels.Group:
    bb = o.Shape.BoundBox
    ents = dxf_entities(bottom_face(o), bb.XMin, bb.YMin)
    key = tuple(sorted(tuple(round(v, 1) if isinstance(v, float) else v for v in e) for e in ents))
    shapes.setdefault(key, []).append(o)
panel_sheet = []
for i, (key, objs) in enumerate(shapes.items(), 1):
    o = objs[0]
    bb = o.Shape.BoundBox
    fname = f"panel_{chr(64 + i)}_{bb.XLength:.0f}x{bb.YLength:.0f}_qty{len(objs)}.dxf"
    write_dxf(os.path.join(panel_dir, fname), dxf_entities(bottom_face(o), bb.XMin, bb.YMin),
              [(h.x - bb.XMin, h.y - bb.YMin) for h, _ in PANEL_HOLES[o.Name]])
    panel_sheet.append((fname, [x.Name for x in objs]))
    for x in objs:
        x.addProperty("App::PropertyString", "CutFile", "BoM").CutFile = fname

# summary for checking against BOM.md
from collections import Counter
cuts = Counter(round(o.CutLength.Value) for o in g_frame.Group)
print(f"Overall frame: {W:.0f} x {DEPTH:.0f} x {TOTAL_H:.0f} mm, height incl. end caps + casters {TOTAL_H + z0:.0f}")
print("Hardware in model:", counts)
print("SKADIS example hardware (not in BoM):", skadis_hw, "+ 6 printed spacers")
print("Cut list:", dict(sorted(cuts.items(), reverse=True)), "pieces:", sum(cuts.values()))
print("Panels:", Counter(o.CutSize for o in g_panels.Group))
for fname, names in panel_sheet:
    print("  ", fname, "->", ", ".join(names))
print("P1S clearance to tower top beam:", z0 + TOTAL_H - P - (deck_top + 458), "mm")
