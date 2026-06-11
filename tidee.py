"""
Tidee Enclosure -- build123d script
Hardware: 2.8" CYD ESP32-S3 dev board (LCDwiki ES3C28P)
Run with: py -3.12 tidee.py

Construction strategy:
  outer_solid = hull-of-4-circles (top view) extruded tall
                INTERSECT hull-of-4-circles (side view) extruded wide
  inner_solid = same with wall inset
  shell = outer - inner, then features added / subtracted
  wave ribs = cube-slab mask intersected with expanded outer, minus outer
              (mirrors OpenSCAD wavy_wrap_ring exactly)
"""

from __future__ import annotations
import math
from build123d import *
from ocp_vscode import show


def _as_solid(shape) -> "Solid | None":
    """
    Normalise whatever build123d returns from a boolean op to a single Solid.

    build123d (depending on version) can return:
      • Solid        -- ideal case, use directly
      • Compound     -- multiple disconnected pieces, fuse them
      • ShapeList    -- list-like result, iterate and fuse
    This helper guarantees callers always get a Solid (or None if empty).
    """
    if shape is None:
        return None
    # Happy path: already has .volume -> treat as a usable solid
    if hasattr(shape, "volume"):
        return shape
    # Iterable (ShapeList / Compound) -- collect pieces
    try:
        pieces = [s for s in shape if hasattr(s, "volume")]
    except TypeError:
        return None
    if not pieces:
        return None
    result = pieces[0]
    for s in pieces[1:]:
        try:
            candidate = result.fuse(s)
            if hasattr(candidate, "volume"):   # only keep if still a Solid
                result = candidate
            # else: fuse produced ShapeList (disconnected pieces), skip
        except Exception:
            pass
    return result   # guaranteed Solid (pieces[0] at minimum)

# ─────────────────────────────────────────────────────────────────
# PARAMETERS
# ─────────────────────────────────────────────────────────────────

W_front    = 88.0
W_back     = 68.0
D          = 50.0
H_front    = 124.0
front_lean = 10.0     # degrees -- front face leans back
top_slope  = 10.0     # degrees -- top drops front-to-back
wall       = 3.0
r_front    = 14.0
r_back     = 7.0
r_side     = 10.0
top_fillet = 8.0      # mm -- TRUE 3D fillet on the top perimeter (pebble dome).
                      #   The top ~(top_fillet+2) mm of the cavity is filled
                      #   SOLID so the outer top edge can round over by this full
                      #   radius without thinning the 3 mm wall (a post-hoc fillet
                      #   on a hollow wall is capped at ~wall; this is not).
                      #   Set 0 to disable (falls back to a small edge-break).

# Derived
top_front_y = H_front * math.tan(math.radians(front_lean))            # ≈ 21.87 @10°
top_depth   = D - top_front_y                                           # ≈ 28.13
H_back      = H_front - top_depth * math.tan(math.radians(top_slope)) # ≈ 119.04
face_len    = math.sqrt(top_front_y**2 + H_front**2)                  # ≈ 125.9

# Highest z still on the CLEAN, planar front face.  The top fillet rounds the
# surface over the top ~top_fillet mm, and the cavity is capped here, so both
# the front-Y sampler and the rib series must stop at or below this line.
z_top_clear = H_front - (top_fillet + 2.0)                            # ≈ 114 @8mm


def half_w(y: float) -> float:
    """Half-width of trapezoid at depth y from front."""
    return W_front / 2 - ((W_front - W_back) / 2) * (y / D)


# PCB / Board
pcb_w               = 50.0
pcb_h               = 86.0
pcb_stack_z         = 10.6
boss_pin_d          = 2.6
boss_pad_d          = 5.6
pcb_top_face_offset = 8.0
glass_from_pcb_top  = 8.0
boss_u_offset       = 20.5

# Screen window
screen_w = 51.0
screen_h = 71.0

# USB housing
usb_housing_w = 14.0
usb_housing_h = 8.0
usb_housing_d = 12.0

# Wave ribs (smooth swept rounded beads)
ridge_dia       = 1.8    # bead diameter (finer = more refined; was 2.2 blocky)
ridge_proud     = 0.9    # mm the bead tip stands proud of the outer face
gap_base        = 4.5    # mm -- rib-to-rib gap at base (denser grip zone => +1 bottom rib)
gap_ratio       = 1.22   # geometric growth per rib (spreads faster toward the top)
wave_amp_top    = 1.5    # flatter top wave (was 2.4)
wave_amp_bot    = 0.8
wave_amp_caprib = 0.5    # the single cap rib at the very top -- nearly flat
wave_wavelen    = 70.0
wave_phase_step = 35.0
wave_segments   = 80     # path samples per rib (smooth sweep, not box count)

# Wordmark
wordmark_text               = "tidee"
wordmark_size               = 13.0   # slightly smaller (was 15)
wordmark_depth              = 1.5
wordmark_offset_from_bottom = 28.0   # raised a touch so 3 grip ribs sit below it and the lone mid-rib is absorbed into the flank band
wordmark_clear_w            = 46.0   # rib-free band width around the logo
wordmark_clear_h            = 14.0   # rib-free band height (sized to the smaller mark)

# Back cover -- FLUSH RABBET JOINT (friction press-fit, adapted from StockTracker)
#   The cover is a thin flange that seats into a recess (so its outer face is
#   FLUSH with the back), with a plug rib that press-fits into the opening all
#   the way around.  No snaps / no cantilever arms -- retention is friction
#   spread over the whole perimeter.  Verified against the StockTracker .3mf.
cover_t    = 1.5    # flange thickness == recess depth (sits flush with back face)
rebate_lip = 1.5    # shoulder width per side that the flange rests on
plug_depth = 4.0    # how far the plug rib reaches into the opening
plug_wall  = 2.0    # thickness of the plug rib wall
plug_cham  = 1.0    # lead-in chamfer at the plug tip (eases insertion)
fit_clear  = 0.15   # clearance per side, plug wall vs opening wall (StockTracker-perfect)
notch_w    = 16.0   # fingernail-pry notch width
notch_h    = 3.0    # notch depth into the cover edge

# Derived cover geometry
#  - The back opening (plug passage) is the inner-cavity cross-section at the back.
#  - The recess (flange seat) is that opening grown by rebate_lip on every side,
#    cut only cover_t deep into the 3 mm back wall (leaving a shoulder).
open_w   = 2.0 * (half_w(D - r_back) - wall)         # plug-passage width  (inner cavity)
open_z0  = usb_housing_h + 3.0                         # opening bottom (clears USB housing + recess lip)
open_z1  = z_top_clear - rebate_lip - 1.0             # opening top (recess stays below the dome)
open_h   = open_z1 - open_z0
recess_w = open_w + 2.0 * rebate_lip                  # flange-seat width
recess_h = open_h + 2.0 * rebate_lip
y_open   = D - r_back                                  # opening plane in Y (43 mm)
corner_r = max(r_back - wall, 2.0)                     # opening corner radius


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def on_front_face(v: float):
    """Return world (y, z) for a point v mm down the slanted front face from the top."""
    lr = math.radians(front_lean)
    return (top_front_y - v * math.sin(lr),
            H_front     - v * math.cos(lr))


def _front_face_outer_y(wz: float) -> float:
    """
    Return the world Y of the ACTUAL outer front surface at height wz.

    on_front_face() traces the raw polygon corner-line.  The side-view hull
    uses circles of radius r_side at each corner (computed by _corner_centre),
    so the real outer surface is the EXTERNAL TANGENT between the front-bottom
    and front-top corner circles -- typically ~3.3 mm further toward the viewer
    (smaller Y) than the raw polygon edge.

    This function computes that tangent line directly from the circle centres,
    matching the geometry of _build_prism_solid(inset=0).
    """
    raw   = [(0.0, 0.0), (D, 0.0), (D, H_back), (top_front_y, H_front)]
    # Circle centres for the two front corners (same call pattern as _build_prism_solid)
    c_bot = _corner_centre(raw[3], raw[0], raw[1], r_side)   # front-bottom
    c_top = _corner_centre(raw[2], raw[3], raw[0], r_side)   # front-top

    # Direction vector along the tangent line (from bottom circle toward top circle)
    dy = c_top[0] - c_bot[0]
    dz = c_top[1] - c_bot[1]
    ln = math.hypot(dy, dz)
    dir_y = dy / ln
    dir_z = dz / ln

    # Outward normal (perpendicular, pointing toward viewer = smaller Y)
    n_y = -dir_z
    n_z =  dir_y

    # Tangent touch-point on the bottom circle
    p_y = c_bot[0] + r_side * n_y
    p_z = c_bot[1] + r_side * n_z

    # Y on the tangent line at height wz
    return p_y + (wz - p_z) * (dir_y / dir_z)


def _sample_front_y(outer_solid, n: int = 18):
    """
    Build a Z→actual-front-face-Y lookup table from the real outer solid.

    Slices outer_solid with thin 2mm-wide (in X) horizontal slabs and takes
    the minimum Y of each cross-section.  This gives the TRUE outer surface Y
    at each height, bypassing the inaccurate analytical formula above.

    Returns (z_list, y_list) for use with _interp_front_y().
    """
    # z_lo sits just ABOVE the front-face tangent touch-point on the base
    # corner-circle (computed at z ≈ 8.22 mm for r_side=10, front_lean=10° —
    # verified in the geometry lab).  Sampling below that lands on the rounded
    # base curl (a downward-facing surface), which would corrupt the table and
    # tip near-base ribs onto the underside.  Keep every sample on the clean,
    # viewer-facing front face.
    z_lo   = 7.0             # extend just onto the base-curl transition so the
                             # lowest rib (z≈8) gets a valid surface-Y sample
    z_hi   = z_top_clear     # stop below the top dome / fillet zone
    z_list = [z_lo + (z_hi - z_lo) * i / (n - 1) for i in range(n)]
    y_list = []
    for z in z_list:
        slab = Box(2.0, 200.0, 1.0,
                   align=(Align.CENTER, Align.CENTER, Align.CENTER))
        slab = slab.moved(Location(Vector(0.0, 0.0, z)))
        try:
            sec   = outer_solid.intersect(slab)
            y_val = sec.bounding_box().min.Y
        except Exception:
            y_val = _front_face_outer_y(z)   # formula fallback
        y_list.append(y_val)
    return z_list, y_list


def _interp_front_y(wz: float, z_list: list, y_list: list) -> float:
    """Linear interpolation of the (z_list, y_list) front-face lookup table."""
    if wz <= z_list[0]:
        return y_list[0]
    if wz >= z_list[-1]:
        return y_list[-1]
    for i in range(len(z_list) - 1):
        if z_list[i] <= wz <= z_list[i + 1]:
            t = (wz - z_list[i]) / (z_list[i + 1] - z_list[i])
            return y_list[i] + t * (y_list[i + 1] - y_list[i])
    return y_list[-1]


def _corner_centre(p0, p1, p2, r: float):
    """
    Return the arc centre (a distance r from corner p1) that fits a fillet
    of radius r at the corner formed by p0-p1-p2.
    """
    d1x = p1[0] - p0[0];  d1z = p1[1] - p0[1]
    d2x = p2[0] - p1[0];  d2z = p2[1] - p1[1]
    l1  = math.hypot(d1x, d1z);  l2 = math.hypot(d2x, d2z)
    if l1 < 1e-9 or l2 < 1e-9:
        return p1
    d1x /= l1;  d1z /= l1
    d2x /= l2;  d2z /= l2
    # Inward bisector
    bx  = d2x - d1x;  bz = d2z - d1z
    bl  = math.hypot(bx, bz)
    if bl < 1e-9:
        return p1
    bx /= bl;  bz /= bl
    # Distance along bisector to arc centre
    cross  = d1x * d2z - d1z * d2x
    dot    = d1x * d2x + d1z * d2z
    sin_h  = abs(cross) / math.sqrt(max((1 - dot) * (1 + dot), 1e-12))
    sin_h  = max(sin_h, 0.1)
    dist   = r / sin_h
    return (p1[0] + bx * dist, p1[1] + bz * dist)


# ─────────────────────────────────────────────────────────────────
# CORE PRISM BUILDER
# ─────────────────────────────────────────────────────────────────

def _build_prism_solid(inset: float = 0.0):
    """
    Build outer (inset=0) or inner (inset=wall) solid:
      intersection of top-view prism and side-view prism.

    Key insight (verified):
      - Build each face using hull of 4 circles in appropriate plane
      - Extrude with:  extrude(face, amount=...)  (NOT BuildPart+add+extrude)
      - The Plane.YZ extrude direction is +X in world space
      - The Plane.XY extrude direction is +Z in world space
    """
    # ── Top-view hull (XY plane) ──────────────────────────────────
    wf  = W_front / 2.0 - inset
    wb  = W_back  / 2.0 - inset
    dep = D - inset * 2.0
    rf  = max(r_front - inset, 0.5)
    rb  = max(r_back  - inset, 0.5)

    with BuildSketch(Plane.XY) as tv:
        for cx, cy, r in [
            (-(wf - rf), inset, rf),
            ( (wf - rf), inset, rf),
            ( (wb - rb), dep,   rb),
            (-(wb - rb), dep,   rb),
        ]:
            add(Circle(r).moved(Location((cx, cy, 0))))
        make_hull()

    tv_face    = tv.sketch.face()
    top_prism  = extrude(tv_face, amount=H_front + 20)

    # ── Side-view hull (YZ plane) ─────────────────────────────────
    r_sv = max(r_side - inset, 0.5)
    yi   = inset
    yd   = D - inset
    zlo  = inset
    zbk  = H_back  - inset
    zfr  = H_front - inset
    ytf  = top_front_y + inset * math.tan(math.radians(front_lean))

    raw = [(yi, zlo), (yd, zlo), (yd, zbk), (ytf, zfr)]
    n   = len(raw)
    cc  = [_corner_centre(raw[(i-1)%n], raw[i], raw[(i+1)%n], r_sv) for i in range(n)]

    with BuildSketch(Plane.YZ) as sv:
        for cy, cz in cc:
            add(Circle(r_sv).moved(Location((cy, cz, 0))))
        make_hull()

    sv_face = sv.sketch.face()
    x_ext   = W_front / 2.0 + 20.0
    side_prism = extrude(sv_face, amount=x_ext * 2.0).moved(
        Location(Vector(-x_ext, 0, 0))
    )

    # ── Intersection ─────────────────────────────────────────────
    return top_prism.intersect(side_prism)


def make_outer_solid():
    return _build_prism_solid(inset=0.0)


def make_inner_solid():
    return _build_prism_solid(inset=wall)


# ─────────────────────────────────────────────────────────────────
# SCREEN WINDOW CUT
# ─────────────────────────────────────────────────────────────────

def make_screen_cut():
    """
    51 x 71mm rectangular window through the slanted front face.
    Uses a rotated Box instead of sketch+extrude to avoid build123d's
    unreliable extrude direction outside a BuildPart context.

    Rotation(-front_lean, 0, 0) aligns:
      +Y  ->  face inward normal  (0, cos(lean), -sin(lean))
      +Z  ->  face upward direction (0, sin(lean),  cos(lean))
    20mm depth ensures it punches from 10mm outside to 10mm inside the 3mm wall.
    """
    v_c    = pcb_top_face_offset + glass_from_pcb_top + screen_h / 2   # = 51.5mm
    wy, wz = on_front_face(v_c)

    cut = Box(screen_w, 20.0, screen_h,
              align=(Align.CENTER, Align.CENTER, Align.CENTER))
    cut = cut.moved(Rotation(-front_lean, 0, 0))
    cut = cut.moved(Location(Vector(0, wy, wz)))
    return cut


# ─────────────────────────────────────────────────────────────────
# PCB MOUNT BOSSES
# ─────────────────────────────────────────────────────────────────

def make_boss_pins():
    """
    4 PCB mount boss+pin cylinders protruding from inner front face.

    Uses Cylinder + Rotation instead of BuildSketch+extrude, because
    extrude() on a tilted custom-plane sketch is unreliable outside
    a BuildPart context (face winding can be ambiguous).

    Rotation maths:
      Rx(θ) maps (0,0,1) -> (0, -sin θ, cos θ)
      We want -> face_normal_in = (0, cos lr, -sin lr)
      -> sin θ = -cos lr,  cos θ = -sin lr
      -> θ = -(90deg + front_lean)          [−100deg for front_lean = 10deg]
    """
    lr      = math.radians(front_lean)
    pin_h   = pcb_stack_z - wall   # 7.6 mm -- visible height from inner surface
    pad_h   = 3.5                   # wider base height
    overlap = 1.5                   # mm the root is buried in the wall

    # Rotation that aligns cylinder +Z with face_normal_in
    rot_deg = -(90.0 + front_lean)  # −100deg for 10deg lean

    positions = [
        (12.0,  boss_u_offset),
        (12.0, -boss_u_offset),
        (90.0,  boss_u_offset),
        (90.0, -boss_u_offset),
    ]

    pieces = []
    for v, u in positions:
        try:
            wy, wz = on_front_face(v)

            # Origin: 'overlap' mm INSIDE the wall (rooted in wall material)
            iy = wy + (wall - overlap) * math.cos(lr)
            iz = wz - (wall - overlap) * math.sin(lr)

            # ── Build boss along local +Z before rotation ──────────────
            # Solid.make_cylinder() is a pure OCC factory -- always returns a Solid
            # (unlike Cylinder() which can return ShapeList outside BuildPart)
            # Pad: from Z=0 (1.5mm into wall) to Z=pad_h+overlap (3.5mm into cavity)
            pad = Solid.make_cylinder(boss_pad_d / 2, pad_h + overlap)

            # Pin: sits on top of pad, protrudes to pin_h past inner surface
            pin = Solid.make_cylinder(boss_pin_d / 2, pin_h - pad_h)
            pin = pin.moved(Location(Vector(0, 0, pad_h + overlap)))

            boss = pad.fuse(pin)

            # Rotate +Z -> face_normal_in, then translate to position on face
            boss = boss.moved(Rotation(rot_deg, 0, 0)).moved(
                Location(Vector(u, iy, iz))
            )
            pieces.append(boss)
            print(f"    boss v={v:.0f} u={u:+.1f} -> iy={iy:.1f} iz={iz:.1f} [OK]")
        except Exception as ex:
            print(f"    boss v={v:.0f} u={u:+.1f} FAILED: {ex}")

    if not pieces:
        print("    All bosses failed!")
        return None

    return pieces   # return list; make_front_shell fuses each to shell individually


# ─────────────────────────────────────────────────────────────────
# USB HOUSING CUT
# ─────────────────────────────────────────────────────────────────

def make_usb_housing_cut():
    """
    Pocket at base of back wall for USB-C pass-through.
    Flush with outer back face (Y=D), cutting usb_housing_d into the wall.
    """
    box = Box(usb_housing_w, usb_housing_d, usb_housing_h,
              align=(Align.CENTER, Align.MAX, Align.MIN))
    return box.moved(Location(Vector(0, D, 0)))


# ─────────────────────────────────────────────────────────────────
# BACK OPENING CUT
# ─────────────────────────────────────────────────────────────────

def make_back_opening_cut():
    """
    Stepped RABBET opening for the flush press-fit cover.

    Two stacked cuts through the back wall (outer back surface at Y=D=50,
    inner cavity back at Y=D-wall=47):

      1. PLUG PASSAGE -- the through-hole the cover's plug rib drops into.
         Outline = inner cavity cross-section (open_w x open_h), rounded
         corners.  Runs from inside the cavity out to the recess floor.
      2. RECESS (flange seat) -- a shallow pocket cover_t deep, grown by
         rebate_lip on every side (recess_w x recess_h).  The flange drops in
         here flush with the back face.  The ring of wall between (1) and (2)
         is the SHOULDER the flange rests on.
    """
    cz = (open_z0 + open_z1) / 2.0

    # 1) plug passage -- from inside the cavity out to the recess floor
    y_passage_start = D - wall - 3.0          # 44 mm, inside the cavity
    y_passage_end   = D - cover_t             # 48.5 mm, recess floor
    passage = Box(open_w, (y_passage_end - y_passage_start) + 0.02, open_h,
                  align=(Align.CENTER, Align.MIN, Align.CENTER))
    try:
        passage = fillet(passage.edges().filter_by(Axis.Y), corner_r)
    except Exception as ex:
        print(f"    opening passage fillet skipped ({ex}); sharp corners")
    passage = passage.moved(Location(Vector(0, y_passage_start, cz)))

    # 2) recess pocket -- cover_t deep into the outer back surface
    recess = Box(recess_w, cover_t + 0.5, recess_h,
                 align=(Align.CENTER, Align.MIN, Align.CENTER))
    try:
        recess = fillet(recess.edges().filter_by(Axis.Y), corner_r + rebate_lip)
    except Exception as ex:
        print(f"    opening recess fillet skipped ({ex}); sharp corners")
    recess = recess.moved(Location(Vector(0, D - cover_t, cz)))

    # Return the two parts to be subtracted SEPARATELY -- never fuse them into
    # one cutter.  A failed fuse used to throw and leave the whole back SOLID;
    # subtracting each part independently guarantees the opening always forms.
    return [passage, recess]


# ─────────────────────────────────────────────────────────────────
# (old BACK TOP LEDGE removed -- the rabbet shoulder replaces it)
# ─────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────
# WORDMARK
# ─────────────────────────────────────────────────────────────────

def make_wordmark_shapes(face_y_table=(None, None)):
    """
    Returns (text_cut, rib_clear_box):
      text_cut     -- shape to subtract for deboss
      rib_clear_box -- shape to subtract rib material around the wordmark
    """
    lr        = math.radians(front_lean)
    v_text    = face_len - wordmark_offset_from_bottom
    _wy_raw, wz = on_front_face(v_text)
    # Use sampled table for accurate surface Y; fall back to formula if unavailable
    z_tab, y_tab = face_y_table
    if z_tab is not None:
        wy_face = _interp_front_y(wz, z_tab, y_tab)
    else:
        wy_face = _front_face_outer_y(wz)   # legacy fallback

    face_normal = Vector(0, -math.cos(lr),  math.sin(lr))  # outward (toward viewer)
    inward_n    = Vector(0,  math.cos(lr), -math.sin(lr))  # inward  (into wall)
    face_x      = Vector(1,  0,             0)

    # ── Text deboss ────────────────────────────────────────────────
    # extrude() with negative amount on a tilted custom plane is unreliable
    # outside BuildPart (face-winding ambiguity).  Workaround:
    #   1. Offset the sketch plane INWARD by wordmark_depth along inward_n
    #   2. Extrude OUTWARD (positive amount) by wordmark_depth + margin
    # The resulting solid spans [face - 0.2mm ... face + wordmark_depth],
    # so subtracting it from the shell carves the correct deboss depth.
    dp_origin = Vector(0, wy_face, wz) + inward_n * wordmark_depth
    deboss_plane = Plane(origin=dp_origin, x_dir=face_x, z_dir=face_normal)
    # Try Bold -> Regular -> slot fallback
    # build123d Text() requires FontStyle enum, not a plain string
    text_solid = None
    for _style in (FontStyle.BOLD, FontStyle.REGULAR, None):
        try:
            with BuildSketch(deboss_plane) as st:
                if _style is not None:
                    Text(wordmark_text, font_size=wordmark_size,
                         font="Arial", font_style=_style,
                         align=(Align.CENTER, Align.CENTER))
                else:
                    Text(wordmark_text, font_size=wordmark_size,
                         font="Arial",
                         align=(Align.CENTER, Align.CENTER))
            _faces = st.sketch.faces()
            _parts = [extrude(f, amount=wordmark_depth + 0.2) for f in _faces]
            text_solid = _binary_fuse(_parts) if len(_parts) > 1 else _parts[0]
            print(f"    Text rendered (style={_style}, {len(_faces)} faces) [OK]")
            break
        except Exception as ex:
            print(f"    Text style={_style} failed: {ex}")
    if text_solid is None:
        print("    All text attempts failed, using slot")
        with BuildSketch(deboss_plane) as st:
            Rectangle(42.0, wordmark_size * 1.2)
        _faces = st.sketch.faces()
        _parts = [extrude(f, amount=wordmark_depth + 0.2) for f in _faces]
        text_solid = _binary_fuse(_parts) if len(_parts) > 1 else _parts[0]
    text_cut = text_solid

    # ── Rib-clear zone ─────────────────────────────────────────────
    # Positive extrude from actual face outward removes the proud rib bumps
    # (1.6mm) from the wordmark panel, leaving a flat surface for the text.
    # 14mm tall: clears ribs z≈13–27mm; rib-0 (z=10mm) stays visible below.
    face_plane = Plane(origin=Vector(0, wy_face, wz), x_dir=face_x, z_dir=face_normal)
    with BuildSketch(face_plane) as sc:
        Rectangle(50.0, 12.0)
    rib_clear = extrude(sc.sketch.face(), amount=ridge_dia + 1.0)

    # Diagnostic: confirm clear zone z-range
    cos_lr = math.cos(math.radians(front_lean))
    half_h = 6.0 * cos_lr   # 12mm height on face -> world-Z half-extent
    print(f"    DIAG rib_clear: wz={wz:.1f}mm, world-Z range={wz - half_h:.1f}..{wz + half_h:.1f}mm, extrude_depth={ridge_dia + 1.0:.1f}mm OUTWARD")

    return text_cut, rib_clear


# ─────────────────────────────────────────────────────────────────
# WAVE RIB SYSTEM  (cube-slab mask -- mirrors OpenSCAD approach)
# ─────────────────────────────────────────────────────────────────

def _binary_fuse(shapes: list):
    """
    Merge a list of Solids into one using a balanced binary tree.
    O(n log n) OCCT work vs O(n²) for sequential fuse.
    Each level merges equally-sized shapes -> OCCT handles it efficiently.
    """
    if not shapes:
        return None
    if len(shapes) == 1:
        return shapes[0]
    mid   = len(shapes) // 2
    left  = _binary_fuse(shapes[:mid])
    right = _binary_fuse(shapes[mid:])
    if left is None:
        return right
    if right is None:
        return left
    try:
        return left.fuse(right)
    except Exception:
        return left   # drop the failing half rather than crash


def _wavy_wrap_ring(z_level: float, amp: float, phase_deg: float,
                    face_y_table=(None, None)):
    """
    One wave rib as a single smooth SWEPT bead (refined rounded ridge).

    A circular profile (radius ridge_dia/2) is swept along a smooth wave path
    running across the front face at height z_level, modulated in Z by
    amp*sin(...).  The bead stands `ridge_proud` mm proud of the ACTUAL outer
    face surface; the rest is buried in the wall for a clean fuse.

    Why sweep instead of the old box-stack: sweeping a CIRCLE is rotationally
    symmetric, so the result is twist-proof and ONE continuous solid.  The old
    approach stacked ~48 axis-aligned boxes that stopped overlapping wherever
    the wave got steep -- which is what broke the ribs into the blocky,
    disconnected 'railway-track' segments.
    """
    lr   = math.radians(front_lean)
    rr   = ridge_dia / 2.0
    z_tab, y_tab = face_y_table

    n_pts = max(int(wave_segments), 24)
    x_ext = W_front / 2.0 + 2.0

    # Logo clear-zone (rib-free band so the big wordmark reads cleanly).
    # Ribs that cross it are split into left/right runs around the band.
    _wy_wm, z_wm = on_front_face(face_len - wordmark_offset_from_bottom)
    logo_z_lo = z_wm - wordmark_clear_h / 2.0
    logo_z_hi = z_wm + wordmark_clear_h / 2.0
    logo_hw   = wordmark_clear_w / 2.0

    # Collect point RUNS: a new run starts whenever the rib leaves the face
    # (edge trim) or enters the logo clear-zone.
    runs = []
    cur  = []
    def _flush():
        if len(cur) >= 2:
            runs.append(list(cur))
        cur.clear()

    for j in range(n_pts + 1):
        xc  = -x_ext + (2.0 * x_ext) * j / n_pts
        z_w = z_level + amp * math.sin(
            math.radians(360.0 * xc / wave_wavelen + phase_deg)
        )
        v = (H_front - z_w) / math.cos(lr)
        if v <= 0.0 or v >= face_len:
            _flush(); continue
        _wy_raw, wz = on_front_face(v)

        # Actual outer hull surface Y (sampled table when available)
        if z_tab is not None:
            wy_face = _interp_front_y(wz, z_tab, y_tab)
        else:
            wy_face = _front_face_outer_y(wz)

        # Trim so the rounded bead stays ON the front face (no nub past corner)
        if abs(xc) > half_w(wy_face) - rr - 0.5:
            _flush(); continue

        # Logo clear-zone: break the rib here so it skirts the wordmark
        if logo_z_lo < wz < logo_z_hi and abs(xc) < logo_hw:
            _flush(); continue

        # Bead CENTRE: proud tip at wy_face - ridge_proud, centre one radius
        # behind the tip -> stands ridge_proud proud, rest buried (solid weld).
        cy = wy_face - ridge_proud + rr
        cur.append(Vector(xc, cy, wz))
    _flush()

    if not runs:
        return None

    solids = []
    for pts in runs:
        if len(pts) < 2:
            continue
        try:
            edges  = [Edge.make_line(pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
            path_w = Wire(edges)
            t0     = (pts[1] - pts[0]).normalized()
            nrm    = Vector(0, 0, 1).cross(t0)
            if nrm.length < 1e-6:
                nrm = Vector(0, 1, 0)
            nrm    = nrm.normalized()
            rp     = Plane(origin=pts[0], x_dir=nrm, z_dir=t0)
            with BuildSketch(rp) as rs:
                Circle(rr)
            seg = sweep(rs.sketch.face(), path=path_w, multisection=False)
        except Exception as ex:
            # Fallback: overlapping spheres along the SAME path -- spacing is
            # well under the bead diameter, so they merge into one continuous
            # ridge that cannot segment.  Bulletproof across build123d versions.
            print(f"    rib z={z_level:.1f} sweep failed ({ex}); sphere fallback")
            try:
                beads = [Solid.make_sphere(rr).moved(Location(p)) for p in pts]
                seg   = _binary_fuse(beads)
            except Exception as ex2:
                print(f"    rib z={z_level:.1f} fallback failed: {ex2}")
                seg = None
        if seg is not None:
            solids.append(seg)

    if not solids:
        return None
    result = solids[0] if len(solids) == 1 else _binary_fuse(solids)

    try:
        if result is None or result.volume < 0.3:
            return None
    except Exception:
        return None

    return result


def make_wave_ridges(outer_solid, face_y_table=(None, None)):
    """Full wave rib system: geometric Z spacing, dense at bottom, sparse at top.

    The viewer-facing front face physically begins at z ≈ 8.22 mm -- the point
    where the front-face tangent touches the base corner-circle (r_side=10,
    front_lean=10°).  Above that line the face is clean and planar; below it the
    surface curls under as the rounded base, so a rib there would tip onto the
    underside.  We therefore start the rib series at z_min = 10 mm (1.9 mm of
    clearance above the tangent) -- this packs the densest ribs into the base
    grip zone, exactly as the design checklist's #1 intent requires, instead of
    wasting the lower ~12 mm of grip face (the old z_min=20 did just that).

    The earlier worry about "sideways tabs" near the base was an X-clip artefact,
    not a front-Y problem: half_w (sharp trapezoid) vs the actual rounded width
    differ by only ~0.5 mm at the base (verified in the geometry lab), so the
    existing half_w clip is fine all the way down.

    Zone breakdown (approximate):
      z=10–109mm  -> grip + side-strip ribs (screen window removes centre)
      z=109–118mm -> full-width ribs (above screen)
    """
    z_min       = 8.0            # start at the very base of the flat front face
                                  # (front-face tangent is z≈8.22; this sits the
                                  # lowest rib right where the face meets the base
                                  # curl, minimising the dead gap at the bottom)
    z_max_rib   = z_top_clear     # stop below the top dome / fillet zone
    top_clear_z = 9.0             # keep the last series rib this far below the
                                  # dedicated top rib, so they don't double up
    # gap_base and gap_ratio are module-level parameters (see top of file)

    all_ribs = []
    i = 0
    while i < 80:
        pos   = gap_base * (gap_ratio ** i - 1.0) / (gap_ratio - 1.0)
        z_lvl = z_min + pos
        if z_lvl >= z_max_rib - top_clear_z:
            break

        v = (H_front - z_lvl) / math.cos(math.radians(front_lean))
        if 0.0 < v < face_len:
            t_amp = (z_lvl - z_min) / max(z_max_rib - z_min, 1.0)
            amp   = wave_amp_bot + (wave_amp_top - wave_amp_bot) * t_amp
            phase = i * wave_phase_step
            rib   = _wavy_wrap_ring(z_lvl, amp, phase, face_y_table)
            if rib is not None:
                all_ribs.append(rib)
                print(f"    rib {i:2d}: z={z_lvl:.1f}  amp={amp:.2f}  vol={rib.volume:.0f}mm3")
            else:
                print(f"    rib {i:2d}: z={z_lvl:.1f}  skipped")
        i += 1

    # Dedicated top rib -- sits just below the top dome (the highest clean face).
    z_top = z_top_clear
    top_rib = _wavy_wrap_ring(z_top, wave_amp_caprib, 0.0, face_y_table)
    if top_rib is not None:
        all_ribs.append(top_rib)
        print(f"    top rib: z={z_top:.1f}  vol={top_rib.volume:.0f}mm3")

    if not all_ribs:
        print("  No ribs generated.")
        return None

    print(f"  {len(all_ribs)} ribs ready.")
    return all_ribs


# ─────────────────────────────────────────────────────────────────
# FRONT SHELL ASSEMBLY
# ─────────────────────────────────────────────────────────────────

def make_front_shell():
    print("  Building outer solid...")
    outer = make_outer_solid()

    # ── True 3D top dome: fillet the top perimeter of the SOLID outer body ──
    # Applied BEFORE hollowing, so the radius is limited by the form, not the
    # 3 mm wall.  The cavity is capped below z_top_clear (see inner build), so
    # this rounds into solid plastic -- a genuine pebble dome that curls in
    # across the width like the base, not a wall-thinning edge-break.
    top_filleted = False
    if top_fillet > 0.05:
        print(f"  Top dome fillet (solid, r={top_fillet})...")
        try:
            top_e = outer.edges().filter_by_position(
                axis=Axis.Z, minimum=z_top_clear, maximum=H_front + 1.0
            )
            if len(top_e) > 0:
                outer = fillet(top_e, top_fillet)
                top_filleted = True
                print(f"    filleted {len(top_e)} top edges [OK]")
            else:
                print("    no top edges in range")
        except Exception as ex:
            print(f"    Solid top fillet failed ({ex}); using post-hollow fallback")

    # ── Build front-face Y lookup table from the actual geometry ──
    print("  Sampling front-face Y table (replaces inaccurate formula)...")
    face_y_table = _sample_front_y(outer)
    _z_tab, _y_tab = face_y_table
    print(f"    z={_z_tab[0]:.0f}mm -> actual_y={_y_tab[0]:+.3f}  "
          f"z={_z_tab[-1]:.0f}mm -> actual_y={_y_tab[-1]:+.3f}")

    print("  Building inner solid...")
    inner = make_inner_solid()

    # Cap the cavity below the dome so the top fillet rounds into solid plastic.
    # Nothing lives in the top ~10 mm of the cavity (PCB/screen sit lower), so
    # filling it solid costs almost no material and makes the dome wall-safe.
    if top_fillet > 0.05:
        cap = Box(W_front + 60, D + 60, z_top_clear + 40,
                  align=(Align.CENTER, Align.CENTER, Align.MAX))
        cap = cap.moved(Location(Vector(0, 0, z_top_clear)))
        try:
            inner = inner.intersect(cap)
        except Exception as ex:
            print(f"    inner cap failed: {ex}")

    # ── Wave ribs -- fuse to outer BEFORE hollowing ─────────────────
    #
    # Why here: fusing to a hollow shell unreliable in OCC -- the proud
    # part (Y < wy, outside outer face) needs to be added to a SOLID
    # body, not a thin-walled shell.  After inner is subtracted the
    # proud ribs survive because they sit entirely outside inner_solid
    # (inner front face is at wy + wall·cos(10deg) ≈ wy + 3 mm).
    print("  Wave ribs (fuse to outer solid, before hollow)...")
    rib_list = make_wave_ridges(outer, face_y_table)
    outer_ribs = outer
    if rib_list:
        for i, r in enumerate(rib_list):
            v_before = outer_ribs.volume
            try:
                candidate = outer_ribs.fuse(r)
                if hasattr(candidate, "volume"):
                    outer_ribs = candidate
                else:
                    # ShapeList result -- try _as_solid
                    s = _as_solid(candidate)
                    if s is not None:
                        outer_ribs = s
            except Exception as ex:
                print(f"    rib {i} fuse-to-outer failed: {ex}")
            print(f"    fuse rib {i:2d}: delta={outer_ribs.volume - v_before:+.0f}")
        print(f"    {len(rib_list)} ribs fused to outer [OK]")
        print(f"    DIAG outer vol={outer.volume:.0f}  outer+ribs vol={outer_ribs.volume:.0f}  delta={outer_ribs.volume - outer.volume:.0f}")
    else:
        print("    No ribs generated.")

    # ── Hollow ────────────────────────────────────────────────────
    print("  Hollowing (outer+ribs - inner)...")
    shell = _as_solid(outer_ribs - inner) or outer_ribs
    print(f"    DIAG shell vol after hollow = {shell.volume:.0f}")

    # ── Base chamfer (Z ≈ 0 perimeter edges) ──────────────────────
    print("  Base chamfer...")
    try:
        base_e = shell.edges().filter_by_position(
            axis=Axis.Z, minimum=-0.02, maximum=0.5, inclusive=(True, True)
        )
        if len(base_e) > 0:
            shell = chamfer(base_e, 1.0)
    except Exception as ex:
        print(f"    Skipped: {ex}")

    # ── Top edge fillet (fallback only) ────────────────────────────
    # The pebble dome is the solid fillet on `outer` above.  This runs ONLY if
    # that failed, giving at least a small wall-safe edge-break on the top.
    if not top_filleted:
        print("  Top fillet (post-hollow fallback)...")
        try:
            top_e = shell.edges().filter_by_position(
                axis=Axis.Z, minimum=H_front - 8.0, maximum=H_front + 1.0
            )
            if len(top_e) > 0:
                shell = fillet(top_e, min(2.5, max(top_fillet, 0.1)))
        except Exception as ex:
            print(f"    Skipped: {ex}")

    # ── Back opening (stepped rabbet for flush press-fit cover) ────
    print("  Back opening rabbet...")
    for _i, _part in enumerate(make_back_opening_cut()):
        try:
            shell = _as_solid(shell - _part) or shell
        except Exception as ex:
            print(f"    opening part {_i} failed: {ex}")

    # (back top ledge removed -- the rabbet shoulder now seats the cover)

    # ── Screen window ──────────────────────────────────────────────
    # Also removes rib material that crosses the screen area.
    print("  Screen window cut...")
    try:
        shell = _as_solid(shell - make_screen_cut()) or shell
    except Exception as ex:
        print(f"    Failed: {ex}")

    # ── USB-C access ───────────────────────────────────────────────
    # The USB-C opening is a NOTCH in the bottom of the COVER (see
    # make_back_cover), NOT a cut in the shell -- so the shell base stays
    # fully SOLID.  The old make_usb_housing_cut() punched z=0..8 and opened
    # the base; it is intentionally no longer applied here.

    # ── Wordmark deboss ────────────────────────────────────────────
    # rib_clear removes proud rib material from the wordmark zone
    # before the text is debossed into the now-flat surface.
    print("  Wordmark deboss...")
    try:
        text_cut, rib_clear = make_wordmark_shapes(face_y_table)
        vol_before = shell.volume
        shell = _as_solid(shell - rib_clear) or shell   # flatten wordmark zone first
        print(f"    DIAG rib_clear removed: {vol_before - shell.volume:.0f} mm3 (before={vol_before:.0f} after={shell.volume:.0f})")
        shell = _as_solid(shell - text_cut) or shell    # then deboss text
    except Exception as ex:
        print(f"    Failed: {ex}")

    # ── Boss pins ──────────────────────────────────────────────────
    print("  Boss pins...")
    boss_list = make_boss_pins()
    if boss_list:
        for i, b in enumerate(boss_list):
            try:
                shell = _as_solid(shell.fuse(b)) or shell
                print(f"    boss {i} fused [OK]")
            except Exception as ex:
                print(f"    boss {i} fuse to shell failed: {ex}")
    else:
        print("    make_boss_pins() returned nothing -- pins skipped")

    return shell


# ─────────────────────────────────────────────────────────────────
# BACK COVER
# ─────────────────────────────────────────────────────────────────

def make_back_cover():
    """
    Back cover -- FLUSH RABBET (friction press-fit). Built in its own local
    frame for printing flat (flange face down on the bed):
        X = width (centred), Z = height (0..recess_h), Y = thickness
        Y=0 is the OUTER (flush) face; +Y points into the case.

    Parts:
      - FLANGE: thin plate (recess_w x recess_h x cover_t) that drops into the
        shell recess and finishes flush with the back face.
      - PLUG RIB: a picture-frame wall that slides into the opening; its outer
        walls grip the opening walls by friction (clearance = fit_clear/side).
      - LEAD-IN CHAMFER on the plug tip eases insertion.
      - FINGERNAIL SCOOP in the flange bottom edge to pry it back out.
    """
    plug_outer_w = open_w - 2.0 * fit_clear
    plug_outer_h = open_h - 2.0 * fit_clear
    plug_inner_w = plug_outer_w - 2.0 * plug_wall
    plug_inner_h = plug_outer_h - 2.0 * plug_wall

    # ── Flange (flush plate) ───────────────────────────────────────
    print("  Cover: flange...")
    flange = Box(recess_w, cover_t, recess_h, align=(Align.CENTER, Align.MIN, Align.CENTER))
    try:
        flange = fillet(flange.edges().filter_by(Axis.Y), corner_r + rebate_lip)
    except Exception as ex:
        print(f"    flange fillet skipped: {ex}")

    # ── Plug rib (picture-frame wall) ──────────────────────────────
    print("  Cover: plug rib...")
    try:
        outer = Box(plug_outer_w, plug_depth, plug_outer_h,
                    align=(Align.CENTER, Align.MIN, Align.CENTER))
        outer = outer.moved(Location(Vector(0, cover_t, 0)))
        try:
            outer = fillet(outer.edges().filter_by(Axis.Y), corner_r)
        except Exception:
            pass
        inner = Box(plug_inner_w, plug_depth + 1.0, plug_inner_h,
                    align=(Align.CENTER, Align.MIN, Align.CENTER))
        inner = inner.moved(Location(Vector(0, cover_t - 0.5, 0)))
        try:
            inner = fillet(inner.edges().filter_by(Axis.Y), max(corner_r - plug_wall, 1.0))
        except Exception:
            pass
        rib = outer - inner

        # Lead-in chamfer on the plug tip (the +Y end), outer edges only
        try:
            tip_y = cover_t + plug_depth
            tip_edges = rib.edges().filter_by_position(
                axis=Axis.Y, minimum=tip_y - 0.05, maximum=tip_y + 0.05
            )
            if len(tip_edges) > 0:
                rib = chamfer(tip_edges, plug_cham)
        except Exception as ex:
            print(f"    plug chamfer skipped: {ex}")

        cover = flange.fuse(rib)
    except Exception as ex:
        print(f"    plug rib failed: {ex}")
        cover = flange

    # ── USB-C notch in the cover bottom edge ───────────────────────
    # Cuts clean through flange + plug at bottom-centre so the USB-C cable
    # reaches the board's port.  Keeps the shell base solid (the port is on
    # the back panel, not the case base).  Doubles as the fingernail pry point.
    print("  Cover: USB-C notch...")
    try:
        usb = Box(usb_housing_w, cover_t + plug_depth + 2.0, usb_housing_h,
                  align=(Align.CENTER, Align.MIN, Align.MIN))
        usb = usb.moved(Location(Vector(0, -0.5, -recess_h / 2.0 - 0.01)))
        cover = cover - usb
    except Exception as ex:
        print(f"    USB notch skipped: {ex}")

    return cover


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 62)
    print("Tidee Enclosure -- build123d")
    print(f"  Body:         {W_front}mm front x {W_back}mm back x {D}mm deep")
    print(f"  Height:       {H_front}mm front, {H_back:.2f}mm back")
    print(f"  Face length:  {face_len:.2f}mm")
    print(f"  top_front_y:  {top_front_y:.2f}mm")
    print(f"  Cover:        flush rabbet, {recess_w:.1f}x{recess_h:.1f}mm flange, "
          f"plug {plug_depth:.1f}mm deep, fit clearance {fit_clear:.2f}mm")
    print("=" * 62)

    output_dir = r"C:\Users\Khygan\Documents\Openscan +claude"

    print("\n[1/2] Front shell...")
    front_shell = make_front_shell()
    bb = front_shell.bounding_box()
    print(f"  volume = {round(front_shell.volume):,} mm³")
    print(f"  bbox: X {bb.min.X:.1f}..{bb.max.X:.1f}  "
          f"Y {bb.min.Y:.1f}..{bb.max.Y:.1f}  "
          f"Z {bb.min.Z:.1f}..{bb.max.Z:.1f}")

    print("\n[2/2] Back cover...")
    back_cover = make_back_cover()
    print(f"  volume = {round(back_cover.volume):,} mm³")

    print("\nExporting STLs...")
    try:
        export_stl(front_shell, rf"{output_dir}\front_shell.stl")
        print(f"  -> front_shell.stl")
    except Exception as ex:
        print(f"  Export error: {ex}")

    try:
        export_stl(back_cover, rf"{output_dir}\back_cover.stl")
        print(f"  -> back_cover.stl")
    except Exception as ex:
        print(f"  Export error: {ex}")

    print("\nOpening preview...")
    from ocp_vscode import set_port
    set_port(3939)
    show(front_shell, back_cover.moved(Location(Vector(W_front + 30, 0, 0))),
         port=3939, reset_camera="reset",
         names=["front_shell", "back_cover"])
    print("Done.")
