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
front_lean = 9.0      # degrees -- front face leans back
top_slope  = 10.0     # degrees -- top drops front-to-back
wall       = 3.0
r_front    = 14.0
r_back     = 7.0
r_side     = 10.0

# Derived
top_front_y = H_front * math.tan(math.radians(front_lean))            # ≈ 19.64
top_depth   = D - top_front_y                                           # ≈ 30.36
H_back      = H_front - top_depth * math.tan(math.radians(top_slope)) # ≈ 118.65
face_len    = math.sqrt(top_front_y**2 + H_front**2)                  # ≈ 125.5


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

# Wave ribs
ridge_dia       = 2.2
gap_base        = 3.0    # mm -- rib-to-rib gap at base (densest zone)
gap_ratio       = 1.15   # geometric growth per rib (15% wider each step)
wave_amp_top    = 2.4
wave_amp_bot    = 0.8
wave_wavelen    = 70.0
wave_phase_step = 35.0
wave_segments   = 48

# Wordmark
wordmark_text               = "tidee"
wordmark_size               = 11.0
wordmark_depth              = 1.5
wordmark_offset_from_bottom = 32.0

# Back cover
cover_t   = 2.5
ledge_h   = 2.5
ledge_d   = 3.5

tab_thick = 1.5
tab_len   = 8.0
tab_w     = 8.0
bump_h    = 1.4
slot_gap  = 0.6

# Derived cover geometry
cw      = 2.0 * (half_w(D - r_back) - wall) - 0.6   # inner back width (cover panel width)
ch_full = H_back - 2.0 * wall - ledge_h
ch      = ch_full - usb_housing_h - 0.4              # panel height above USB housing
ledge_z = H_back - wall - ledge_h                    # Z bottom of ledge


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


def _sample_front_y(outer_solid, n: int = 14):
    """
    Build a Z→actual-front-face-Y lookup table from the real outer solid.

    Slices outer_solid with thin 2mm-wide (in X) horizontal slabs and takes
    the minimum Y of each cross-section.  This gives the TRUE outer surface Y
    at each height, bypassing the inaccurate analytical formula above.

    Returns (z_list, y_list) for use with _interp_front_y().
    """
    z_lo   = 6.0
    z_hi   = H_front - 3.0   # ~121 mm
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
      -> θ = -(90deg + front_lean)          [−99deg for front_lean = 9deg]
    """
    lr      = math.radians(front_lean)
    pin_h   = pcb_stack_z - wall   # 7.6 mm -- visible height from inner surface
    pad_h   = 3.5                   # wider base height
    overlap = 1.5                   # mm the root is buried in the wall

    # Rotation that aligns cylinder +Z with face_normal_in
    rot_deg = -(90.0 + front_lean)  # −99deg for 9deg lean

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
    Remove the back wall to open the shell for the hatch cover.

    Geometry notes:
      - Inner cavity back surface is at Y ≈ D-r_back-wall = 40 mm
      - Outer back surface extends to Y = D = 50 mm
      - Cut must start BEFORE the inner back surface and extend PAST the outer
      - Width = inner cavity width (preserve rounded side-wall corners)
      - Height starts at usb_housing_h (preserve USB pocket at base)
    """
    open_w  = 2.0 * (half_w(D - r_back) - wall) + 0.5   # ≈ 65.3 mm
    open_h  = H_back - usb_housing_h + 2.0               # ≈ 112.65 mm
    y_start = D - r_back - wall - 3.0                    # ≈ 37 mm (before inner back wall)
    depth   = D + 5.0 - y_start                          # ≈ 18 mm (past outer back surface)

    box = Box(open_w, depth, open_h, align=(Align.CENTER, Align.MIN, Align.MIN))
    return box.moved(Location(Vector(0, y_start, usb_housing_h)))


# ─────────────────────────────────────────────────────────────────
# BACK TOP LEDGE
# ─────────────────────────────────────────────────────────────────

def make_back_top_ledge():
    """
    Shelf inside the top of the back opening.
    Width=cw, height=ledge_h, depth=ledge_d toward interior from opening plane.
    Y: (D-r_back-ledge_d) -> (D-r_back)  i.e. 39.5mm -> 43mm
    Z bottom = ledge_z ≈ 113.15mm
    """
    y_opening = D - r_back           # 43 mm -- opening plane
    y_start   = y_opening - ledge_d  # 39.5 mm -- inside shell
    box = Box(cw, ledge_d, ledge_h, align=(Align.CENTER, Align.MIN, Align.MIN))
    return box.moved(Location(Vector(0, y_start, ledge_z)))


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
                         font="Liberation Sans", font_style=_style,
                         align=(Align.CENTER, Align.CENTER))
                else:
                    Text(wordmark_text, font_size=wordmark_size,
                         font="Liberation Sans",
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
    One wave rib: boxes placed DIRECTLY on the front face surface.

    No rotation, no shell boolean ops.  Each small box sits FULLY PROUD
    of the outer face surface (matching OpenSCAD offset_3d(ridge_dia)):
        wy_start = wy - ridge_dia      ← rib tip, 1.6mm proud
        Box Y: [wy_start, wy_start + ridge_dia + 0.5]
             = [wy-1.6, wy+0.5]
        Y < wy  ->  proud bead (full ridge_dia height outside surface)
        Y > wy  ->  0.5mm embedded in wall for fuse connectivity

    align=(MIN, MIN, CENTER):  starts at (xj, wy_start), centred in Z.
    Adjacent boxes overlap in Z (ridge_dia 1.6mm > ΔZ ≈ 0.5mm) so
    _binary_fuse produces one solid connected rib per level.
    """
    lr    = math.radians(front_lean)
    n_seg = wave_segments                  # 48
    x_ext = W_front / 2.0 + 2.0           # just cover the front face
    step  = (2.0 * x_ext) / n_seg

    boxes = []
    for j in range(n_seg):
        xj = -x_ext + j * step
        xc = xj + step * 0.5              # segment centre X

        # Wave Z offset
        z_w = z_level + amp * math.sin(
            math.radians(360.0 * xc / wave_wavelen + phase_deg)
        )

        # Face position at this wave height
        v = (H_front - z_w) / math.cos(lr)
        if v <= 0.0 or v >= face_len:
            continue
        _wy_raw, wz = on_front_face(v)   # wz is correct; _wy_raw is the raw polygon edge

        # Actual outer hull surface Y -- use sampled table when available
        z_tab, y_tab = face_y_table
        if z_tab is not None:
            wy_face = _interp_front_y(wz, z_tab, y_tab)
        else:
            wy_face = _front_face_outer_y(wz)

        # Clip to face width using the corrected face Y
        if abs(xc) > half_w(wy_face) + 1.0:
            continue

        # Place box FULLY proud of the outer surface.
        # OpenSCAD original used offset_3d(ridge_dia) so the rib sits
        # entirely outside the face -- full ridge_dia (1.6mm) proud.
        # We replicate that with:
        #   wy_start = wy_face - ridge_dia   ← rib tip, 1.6mm in front of actual face
        #   box Y width = ridge_dia + 0.5mm overlap inside wall
        # The 0.5mm overlap ensures OCC fuse registers the intersection.
        wy_start = wy_face - ridge_dia
        box = Box(step + 0.05, ridge_dia + 0.5, ridge_dia,
                  align=(Align.MIN, Align.MIN, Align.CENTER))
        box = box.moved(Location(Vector(xj, wy_start, wz)))
        boxes.append(box)

    if not boxes:
        return None

    result = _binary_fuse(boxes)
    if result is None:
        return None

    try:
        if result.volume < 1.0:
            return None
    except Exception:
        return None

    return result


def make_wave_ridges(outer_solid, face_y_table=(None, None)):
    """Full wave rib system: geometric Z spacing, dense at bottom, sparse at top.

    Starts at z=38mm (screen-bottom zone).  Below z≈32mm the outer solid's
    rounded base-corner tangent is entangled with the bottom-curve surface,
    so the probe face_y table gives a value that places ribs on the downward-
    facing corner rather than the viewer-facing front face -- they show up as
    sideways tabs, not front-face ribs.  Starting at z=38mm avoids this zone
    entirely; the face_y table is accurate and the front face is clean there.

    Zone breakdown (approximate):
      z=38–109mm  -> side-strip ribs only (screen window removes centre)
      z=109–118mm -> full-width ribs (above screen)
    """
    z_min     = 20.0             # start well above base-corner geometry (circle zone ends ~z=16.5mm)
    z_max_rib = H_front - 6.0   # ~118mm -- stop before top rib
    # gap_base and gap_ratio are module-level parameters (see top of file)

    all_ribs = []
    i = 0
    while i < 80:
        pos   = gap_base * (gap_ratio ** i - 1.0) / (gap_ratio - 1.0)
        z_lvl = z_min + pos
        if z_lvl >= z_max_rib:
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

    # Dedicated top rib
    _wy_t, z_top = on_front_face(6.0)
    top_rib = _wavy_wrap_ring(z_top, wave_amp_top, 0.0, face_y_table)
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

    # ── Build front-face Y lookup table from the actual geometry ──
    print("  Sampling front-face Y table (replaces inaccurate formula)...")
    face_y_table = _sample_front_y(outer)
    _z_tab, _y_tab = face_y_table
    print(f"    z={_z_tab[0]:.0f}mm -> actual_y={_y_tab[0]:+.3f}  "
          f"z={_z_tab[-1]:.0f}mm -> actual_y={_y_tab[-1]:+.3f}")

    print("  Building inner solid...")
    inner = make_inner_solid()

    # ── Wave ribs -- fuse to outer BEFORE hollowing ─────────────────
    #
    # Why here: fusing to a hollow shell unreliable in OCC -- the proud
    # part (Y < wy, outside outer face) needs to be added to a SOLID
    # body, not a thin-walled shell.  After inner is subtracted the
    # proud ribs survive because they sit entirely outside inner_solid
    # (inner front face is at wy + wall·cos(9deg) ≈ wy + 3 mm).
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
    shell = outer_ribs - inner
    print(f"    DIAG shell vol after hollow = {shell.volume:.0f}")

    # ── Base chamfer (Z ≈ 0 perimeter edges) ──────────────────────
    print("  Base chamfer...")
    try:
        base_e = shell.edges().filter_by_position(
            axis=Axis.Z, minimum=-0.02, maximum=0.5, inclusive=(True, True)
        )
        if len(base_e) > 0:
            shell = chamfer(base_e, 2.5)
    except Exception as ex:
        print(f"    Skipped: {ex}")

    # ── Top edge fillet ────────────────────────────────────────────
    print("  Top fillet...")
    try:
        top_e = shell.edges().filter_by_position(
            axis=Axis.Z, minimum=H_front - 8.0, maximum=H_front + 1.0
        )
        if len(top_e) > 0:
            shell = fillet(top_e, 3.0)
    except Exception as ex:
        print(f"    Skipped: {ex}")

    # ── Back opening ───────────────────────────────────────────────
    print("  Back opening cut...")
    try:
        shell = shell - make_back_opening_cut()
    except Exception as ex:
        print(f"    Failed: {ex}")

    # ── Back top ledge ─────────────────────────────────────────────
    print("  Back top ledge...")
    try:
        shell = shell.fuse(make_back_top_ledge())
    except Exception as ex:
        print(f"    Failed: {ex}")

    # ── Screen window ──────────────────────────────────────────────
    # Also removes rib material that crosses the screen area.
    print("  Screen window cut...")
    try:
        shell = shell - make_screen_cut()
    except Exception as ex:
        print(f"    Failed: {ex}")

    # ── USB housing pocket ─────────────────────────────────────────
    print("  USB housing cut...")
    try:
        shell = shell - make_usb_housing_cut()
    except Exception as ex:
        print(f"    Failed: {ex}")

    # ── Wordmark deboss ────────────────────────────────────────────
    # rib_clear removes proud rib material from the wordmark zone
    # before the text is debossed into the now-flat surface.
    print("  Wordmark deboss...")
    try:
        text_cut, rib_clear = make_wordmark_shapes(face_y_table)
        vol_before = shell.volume
        shell = shell - rib_clear   # flatten wordmark zone first
        print(f"    DIAG rib_clear removed: {vol_before - shell.volume:.0f} mm3 (before={vol_before:.0f} after={shell.volume:.0f})")
        shell = shell - text_cut    # then deboss text
    except Exception as ex:
        print(f"    Failed: {ex}")

    # ── Boss pins ──────────────────────────────────────────────────
    print("  Boss pins...")
    boss_list = make_boss_pins()
    if boss_list:
        for i, b in enumerate(boss_list):
            try:
                shell = shell.fuse(b)
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
    Back hatch cover.
    Local coords: X=width (centred), Y=thickness (0=inner, cover_t=outer), Z=height.
    Z=0 is bottom of panel (sits above USB housing when installed).
    Total height = ch (main panel) + tongue_h (top tab).
    """
    tongue_h = ledge_h - 0.3    # 2.2mm top tongue fits under shell ledge
    arch_w   = usb_housing_w + 4.0   # 18mm USB cable clearance arch
    arch_h   = usb_housing_h + 1.0   # 9mm

    total_h  = ch + tongue_h

    # ── Main panel ─────────────────────────────────────────────────
    print("  Cover: panel...")
    panel = Box(cw, cover_t, total_h, align=(Align.CENTER, Align.MIN, Align.MIN))

    # ── Arch cutout at bottom for USB cable ────────────────────────
    print("  Cover: arch cut...")
    try:
        arch = Box(arch_w, cover_t + 0.4, arch_h,
                   align=(Align.CENTER, Align.MIN, Align.MIN))
        arch = arch.moved(Location(Vector(0, -0.2, 0)))
        # Chamfer the top of the arch in X (the long edges, length=arch_w)
        # Only chamfer the long horizontal edges to avoid thin-edge failures
        try:
            arch_top_long = [
                e for e in arch.edges().filter_by_position(
                    axis=Axis.Z, minimum=arch_h - 0.1, maximum=arch_h + 0.1
                )
                if e.length > arch_w * 0.5  # only long edges
            ]
            if arch_top_long:
                arch = chamfer(arch_top_long, 1.0)
        except Exception:
            pass  # proceed without chamfer on arch
        panel = panel - arch
    except Exception as ex:
        print(f"    Arch skipped: {ex}")

    # ── Chamfer all edges (try; skip if topology fails) ───────────
    print("  Cover: edge chamfer...")
    try:
        # Only chamfer edges longer than 2mm to avoid thin-edge failures
        long_edges = [e for e in panel.edges() if e.length > 2.0]
        if long_edges:
            panel = chamfer(long_edges, 0.4)
    except Exception as ex:
        print(f"    Chamfer skipped: {ex}")

    # ── Snap tabs (two side tabs) ──────────────────────────────────
    print("  Cover: snap tabs...")
    try:
        tab_x = cw / 2.0 - tab_w / 2.0 - 4.0
        for xp in [tab_x, -tab_x]:
            # Arm: hangs below Z=0 (below panel bottom edge)
            arm = Box(tab_w, tab_thick, tab_len,
                      align=(Align.CENTER, Align.MIN, Align.MAX))
            arm = arm.moved(Location(Vector(xp, 0.0, 0.0)))
            panel = panel.fuse(arm)

            # Snap bump at free end of arm (outermost Z = -tab_len)
            bump = Box(tab_w - 1.0, bump_h, 3.0,
                       align=(Align.CENTER, Align.MAX, Align.MIN))
            bump = bump.moved(Location(Vector(xp, 0.0, -tab_len)))
            try:
                panel = panel.fuse(bump)
            except Exception:
                pass

            # Flex slots: thin gaps on either side of the arm through the panel
            for side in [-1.0, 1.0]:
                slot = Box(slot_gap, cover_t + 0.4, tab_len + slot_gap,
                           align=(Align.MIN, Align.MIN, Align.MAX))
                slot = slot.moved(Location(Vector(xp + side * (tab_w / 2.0), -0.2, 0.0)))
                try:
                    panel = panel - slot
                except Exception:
                    pass

    except Exception as ex:
        print(f"    Tabs failed: {ex}")

    # ── Vent holes (5x3 grid, Ø2.2mm, 8mm spacing) ────────────────
    print("  Cover: vent holes...")
    nx, nz    = 5, 3
    spacing   = 8.0
    grid_cz   = ch * 0.52   # centred in main panel body
    for ix in range(nx):
        for iz in range(nz):
            x = (ix - (nx - 1) / 2.0) * spacing
            z = grid_cz + (iz - (nz - 1) / 2.0) * spacing
            if 4.0 < z < ch - 2.0 and abs(x) < cw / 2.0 - 3.0:
                try:
                    hole = Cylinder(1.1, cover_t + 0.4,
                                    align=(Align.CENTER, Align.CENTER, Align.CENTER))
                    # Rotation(90,0,0) maps cylinder Z-axis -> Y-axis (through the panel)
                    hole = hole.moved(Rotation(90, 0, 0)).moved(
                        Location(Vector(x, cover_t / 2.0, z))
                    )
                    panel = panel - hole
                except Exception:
                    pass

    # ── Fingernail notch at bottom centre (between tabs) ──────────
    print("  Cover: fingernail notch...")
    try:
        notch = Box(20.0, cover_t + 0.4, 3.5,
                    align=(Align.CENTER, Align.MIN, Align.MIN))
        notch = notch.moved(Location(Vector(0, -0.2, -3.5)))
        panel = panel - notch
    except Exception as ex:
        print(f"    Notch skipped: {ex}")

    # ── Horizontal ribs on outer face (matching front face style) ─
    print("  Cover: outer ribs...")
    for i, z_rib in enumerate([ch * 0.70, ch * 0.35]):
        amp   = (wave_amp_top + wave_amp_bot) / 2.0
        phase = i * wave_phase_step

        pts = []
        for j in range(wave_segments + 1):
            t = j / wave_segments
            x = -cw / 2.0 + t * cw
            z = z_rib + amp * math.sin(math.radians(360.0 * x / wave_wavelen + phase))
            pts.append(Vector(x, cover_t, z))

        if len(pts) < 3:
            continue
        try:
            edges    = [Edge.make_line(pts[j], pts[j + 1]) for j in range(len(pts) - 1)]
            path_w   = Wire(edges)
            t0       = (pts[1] - pts[0]).normalized()
            nrm      = Vector(0, 0, 1).cross(t0)
            if nrm.length < 1e-6:
                nrm = Vector(0, 1, 0)
            nrm      = nrm.normalized()
            rp       = Plane(origin=pts[0], x_dir=nrm, z_dir=t0)
            with BuildSketch(rp) as rs:
                Circle(ridge_dia / 2.0)
            rib = sweep(rs.sketch.face(), path=path_w, multisection=False)
            panel = panel.fuse(rib)
        except Exception as ex:
            print(f"    Rib {i} skipped: {ex}")

    return panel


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
    print(f"  Cover panel:  {cw:.2f}mm wide x {ch:.2f}mm tall")
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
    show(front_shell, back_cover.moved(Location(Vector(W_front + 30, 0, 0))),
         port=3940, reset_camera="reset")
    print("Done.")
