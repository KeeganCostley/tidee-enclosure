// =============================================================
// TIDEEE ENCLOSURE — Wave-relief monolith (v2 — robust build)
// For 2.8" CYD ESP32-S3 dev board (LCDwiki ES3C28P)
//
// Body construction: INTERSECTION of two extruded 2D profiles
//   (top-view trapezoid)  ∩  (side-view tilted/sloped silhouette)
// This gives a manifold solid every time — no polyhedron winding,
// no minkowski (which is slow and finicky).
//
// Features:
//   - Trapezoidal footprint (88 → 68 mm, R14 front / R7 back)
//   - Front face leans back 5°, top slopes 10° down to back,
//     back face vertical 90° to base
//   - Golden-ratio horizontal wave ribs (proud, on front face)
//   - "tideee" wordmark debossed near the bottom of the front face
//   - Screen window cut through the front face near the top
//   - 4 PCB mount bosses on the inner front face
//   - USB-C panel-mount pocket through the back face (near base)
//   - Snap-fit rear cover (TV remote style: top tongue + bottom snap arm)
//
// Two parts:
//   PART = "front_shell"  → the wave-relief body (open at back)
//   PART = "back_cover"   → the trapezoidal screw-on lid
//
// Print suggestion: 0.2 mm layer, 3 perimeters, 20% gyroid infill,
//   matte PETG or PLA. Print the FRONT SHELL face-up (screen face
//   down on the bed) with tree supports for the overhanging top.
// =============================================================

PART = "all";  // "front_shell", "back_cover", or "all"

$fn = 48;

// -------------------------------------------------------------
// OUTER DIMENSIONS (mm)
// -------------------------------------------------------------
W_front     = 88;     // width at front edge of base
W_back      = 68;     // width at back edge of base
D           = 50;     // depth (front-to-back)
H_front     = 124;    // height at the front edge (from base to top-front corner)
                      // (+20 mm vs original to give cable-bend room below the USB port)
front_lean  = 9;      // degrees: top of front face leans back
top_slope   = 10;     // degrees: top surface drops from front to back
wall        = 3.0;    // wall thickness

r_front     = 14;     // top-view corner radius at the FRONT edge
r_back      = 7;      // top-view corner radius at the BACK edge
r_side      = 10;     // side-profile edge-rounding radius (all 4 corners)
                      // 10 → top-front corners are visibly mellowed to match the base

// derived
top_front_y = H_front * tan(front_lean);                          // ≈ 9.10
top_depth   = D - top_front_y;                                     // ≈ 40.90
H_back      = H_front - top_depth * tan(top_slope);                // ≈ 96.79
face_len    = sqrt(top_front_y*top_front_y + H_front*H_front);     // ≈ 104.4

// half-width of trapezoid at a given y (depth into device)
function half_w(y) = W_front/2 - ((W_front - W_back)/2) * (y / D);

// -------------------------------------------------------------
// CYD BOARD (LCDwiki ES3C28P, 2.8")
// -------------------------------------------------------------
pcb_w           = 50;
pcb_h           = 86;
pcb_stack_z     = 10.6;
pcb_hole_inset_v = 4.0;   // vertical inset: (86 - 78) / 2 = 4 mm
pcb_hole_inset_h = 3.5;   // horizontal inset: (50 - 43) / 2 = 3.5 mm
pcb_hole_d       = 3.5;   // measured hole diameter on PCB
boss_pin_d       = 2.6;   // printed pin diameter — undersized for FDM tolerance

pcb_top_face_offset = 8;  // mm from top-front corner to the TOP edge of the PCB
                          // 8 → window top at v=16 mm (6 mm clear of the r_side=10 corner
                          // rounding so it isn't clipped); top bosses at v=12 mm (just
                          // below the rounded zone); lip above screen = 16 mm
glass_from_pcb_top  = 8;  // mm from PCB top edge to top edge of screen glass
                          // (measured on physical board)

screen_window_w = 51.0;   // 50 mm glass + 0.5 mm clearance each side
screen_window_h = 71.0;   // 70 mm glass + 0.5 mm clearance each side

// -------------------------------------------------------------
// USB-C PASS-THROUGH POCKET (rear-bottom, vertical back wall)
// -------------------------------------------------------------
usb_w           = 14;
usb_h           = 7;
usb_pocket_d    = 4;
usb_z_center    = 20;   // raised from 13 to match PCB sitting higher in the taller shell

// -------------------------------------------------------------
// WAVE RELIEF (golden-ratio spacing, sine-modulated ribs)
// -------------------------------------------------------------
ridge_dia       = 1.2;     // rib cross-section diameter (was 1.6 — slimmer, more refined)
ridge_gap_base  = 4.5;     // minimum gap between ribs at densest point (was 2.5 — bottom less crowded)
ridge_ratio     = 1.22;    // golden-ratio spacing factor
ridge_y_start   = 2;       // was 6 — brings bottom rib right to the base edge

// sine modulation along each ridge's length
wave_amp_top    = 1.6;     // amplitude at the sparsest (top) ridge — was 2.4
wave_amp_bot    = 0.4;     // amplitude at the densest (bottom) ridge
wave_wavelen    = 70;      // sine wavelength along the rib (mm)
wave_phase_step = 35;      // degrees of phase shift per row
wave_segments   = 48;      // capsule segments per rib — was 28, smoother curves

// -------------------------------------------------------------
// WORDMARK
// -------------------------------------------------------------
wordmark_text   = "tidee";
wordmark_size   = 11;
wordmark_depth  = 0.6;
wordmark_offset_from_bottom = 20;  // was 14 — raised out of the base stringing zone

// -------------------------------------------------------------
// REAR COVER & CLIPS
// -------------------------------------------------------------
cover_t         = 2.5;
clip_size       = 1.6;
clip_inset_back = 8;    // notches at Y=42 mm, just inside the back opening edge


// =============================================================
// 2D PROFILES
// =============================================================

// Top-view: trapezoidal footprint with R14 front, R7 back corners.
module footprint_top_2d() {
  hull() {
    translate([-W_front/2 + r_front, r_front])         circle(r=r_front);
    translate([ W_front/2 - r_front, r_front])         circle(r=r_front);
    translate([ W_back/2  - r_back,  D - r_back])      circle(r=r_back);
    translate([-W_back/2  + r_back,  D - r_back])      circle(r=r_back);
  }
}

// Side-view (in YZ plane, drawn here as XY): the leaning/sloping silhouette.
//   point order, clockwise starting at bottom-front:
//     BF (0, 0) → BB (D, 0) → TB (D, H_back) → TF (top_front_y, H_front)
module footprint_side_2d() {
  offset(r=r_side) offset(r=-r_side)
    polygon([[0,0], [D,0], [D,H_back], [top_front_y,H_front]]);
}

// =============================================================
// 3D SOLIDS
// =============================================================

// Top-view prism: extrudes the trapezoid up along Z, oversized.
module top_view_prism() {
  linear_extrude(height = H_front + 20)
    footprint_top_2d();
}

// Side-view prism: extrudes the side polygon ACROSS the device's width (X).
// The polygon is in XY, so we rotate the extrusion so:
//   poly-x (which encodes depth Y) → world Y
//   poly-y (which encodes height Z) → world Z
//   extrusion direction              → world X
module side_view_prism() {
  W_extrude = W_front + 40;
  translate([-W_extrude/2, 0, 0])
    rotate([90, 0, 90])
      linear_extrude(height = W_extrude)
        footprint_side_2d();
}

// Outer solid: intersection of the two prisms = the desired body shape.
module outer_solid() {
  intersection() {
    top_view_prism();
    side_view_prism();
  }
}

// Inner cavity: same two profiles, inset by wall thickness in 2D.
module inner_solid() {
  intersection() {
    linear_extrude(height = H_front + 20)
      offset(r=-wall) footprint_top_2d();
    translate([-(W_front + 40)/2, 0, 0])
      rotate([90, 0, 90])
        linear_extrude(height = W_front + 40)
          offset(r=-wall) footprint_side_2d();
  }
}

// =============================================================
// FACE-LOCAL POSITIONING
// Place child geometry on the slanted front face at distance
// v_along_face from the top, offset by u horizontally.
// Local frame: +z = outward face normal; +y = down along face.
// =============================================================
module on_front_face(v_along_face, u=0) {
  world_y = top_front_y - v_along_face * sin(front_lean);
  world_z = H_front     - v_along_face * cos(front_lean);
  translate([u, world_y, world_z])
    rotate([90 - front_lean, 0, 0])   // 90-lean aligns local Z with the true face
      children();                      // normal (face leans back, not forward)
}

// =============================================================
// FEATURES
// =============================================================

// Above-screen face ribs — sine-modulated hull capsules on the tilted front face.
// Below-screen ribs use wavy_wrap_ring (see below) for a continuous wrapped object.
module wavy_rib(v_along_face, amp, phase) {
  world_y = top_front_y - v_along_face * sin(front_lean);
  w_here  = 2 * half_w(world_y) - 4;
  n       = wave_segments;
  step    = w_here / n;
  on_front_face(v_along_face) {
    for (i = [0 : n - 1]) {
      x0 = -w_here/2 + i * step;
      x1 = -w_here/2 + (i+1) * step;
      y0 = amp * sin(360 * x0 / wave_wavelen + phase);
      y1 = amp * sin(360 * x1 / wave_wavelen + phase);
      hull() {
        translate([x0, y0, 0]) sphere(d=ridge_dia, $fn=14);
        translate([x1, y1, 0]) sphere(d=ridge_dia, $fn=14);
      }
    }
  }
}

// Full-wrap wavy ring: ONE continuous rib object that spans the front face,
// the rounded front corners, and the side walls — no seam or join.
//
// The Z-centre of the ring oscillates sinusoidally with X using the same
// sine function as wavy_rib, so the style is identical on every surface.
//
// Implementation: N thin vertical slices, each placed at the sine-correct Z
// for its X.  Their union forms a wavy slab; intersecting with the expanded
// outer envelope and differencing against outer_solid leaves only the proud
// ring material on the outside surface.
//
//   z_level  nominal Z of the ring centre at X=0
//   amp      sine amplitude (mm)
//   phase    sine phase (degrees)
//   max_y    how far back onto the side walls the ring reaches (mm)
module wavy_wrap_ring(z_level, amp, phase, max_y) {
  n    = wave_segments * 2;      // double segments — wider path needs more
  xext = W_front / 2 + 10;
  step = (2 * xext) / n;

  difference() {
    intersection() {
      // Outer surface expanded by one rib-radius — the shell to keep
      intersection() {
        linear_extrude(H_front + 20)
          offset(r = ridge_dia/2) footprint_top_2d();
        translate([-(W_front + 40)/2, 0, 0])
          rotate([90, 0, 90])
            linear_extrude(W_front + 40)
              offset(r = ridge_dia/2) footprint_side_2d();
      }
      // Wavy slab: each slice centred at the sine-correct Z for its X
      union() {
        for (j = [0 : n - 1]) {
          xj = -xext + j * step;
          zj = z_level + amp * sin(360 * xj / wave_wavelen + phase);
          translate([xj, 0, zj - ridge_dia/2])
            cube([step + 0.01, max_y + 1, ridge_dia]);
        }
      }
    }
    outer_solid();   // trim to proud surface only
  }
}

// All rib geometry: every rib is a wavy_wrap_ring.
//
// Side-wall reach (max_y) uses a symmetric V-shape taper:
//   • y_deep  at the face BOTTOM  (rings wrap fully around the base corners)
//   • y_deep  at the face TOP     (rings wrap fully around the roof corners)  ← NEW
//   • y_shallow at the face CENTRE (minimum wrap around the screen bezel zone)
//
// This mirrors the "mellowed corner" arc at the base onto the top edge,
// creating a subtle 4-corner star silhouette when viewed from the front.
// screen_window_cut() in front_shell() carves the screen opening cleanly.
module wave_ridges() {
  L          = face_len - ridge_y_start - 4;
  n_rows_est = ceil(log(1 + L * (ridge_ratio - 1) / ridge_gap_base) / log(ridge_ratio));
  y_shallow  = 5;           // minimum side-depth — at the screen-bezel centre
  y_deep     = D - r_back;  // maximum side-depth — at both top and bottom extremes (43 mm)
  v_max      = face_len - ridge_y_start;  // ~118 mm — full face span

  for (i = [0 : 60]) {
    pos = ridge_gap_base * (pow(ridge_ratio, i) - 1) / (ridge_ratio - 1);
    if (pos < L) {
      v       = face_len - ridge_y_start - pos;
      t       = (n_rows_est > 1) ? min(i / (n_rows_est - 1), 1) : 0;
      amp     = wave_amp_bot + (wave_amp_top - wave_amp_bot) * t;
      z_level = H_front - v * cos(front_lean);
      // V-shape taper: abs(2t-1) is 1 at both extremes (v=0, v=v_max) and 0 at centre.
      tw_norm = v / v_max;               // 0 at face top, 1 at face bottom
      tw_sym  = abs(2 * tw_norm - 1);   // symmetric: 1 at top & bottom, 0 at centre
      max_y   = y_shallow + (y_deep - y_shallow) * tw_sym;
      wavy_wrap_ring(z_level, amp=amp, phase=i * wave_phase_step, max_y=max_y);
    }
  }

  // Dedicated top-edge rib — fixed 6 mm from the face top (independent of
  // ridge_y_start so it stays visible even when ridge_y_start is reduced).
  wavy_wrap_ring(H_front - 6 * cos(front_lean),
                 amp=wave_amp_top, phase=0, max_y=y_deep);
}

module screen_window_cut() {
  // v_center: PCB top offset + gap to glass top + half window height
  v_center = pcb_top_face_offset + glass_from_pcb_top + screen_window_h/2;
  on_front_face(v_center) {
    translate([-screen_window_w/2, -screen_window_h/2, -wall - 2])
      cube([screen_window_w, screen_window_h, wall + 6]);
  }
}

module wordmark_emboss() {
  v_pos = face_len - wordmark_offset_from_bottom;
  on_front_face(v_pos) {
    translate([0, 0, -wordmark_depth])
      linear_extrude(height = wordmark_depth + 0.1)
        text(wordmark_text, size=wordmark_size,
             halign="center", valign="center",
             font="Liberation Sans:style=Bold");
  }
}

// Clears proud rib material from the wordmark centre only.
// Ribs continue on both sides of the logo — the cleared width is just
// wide enough to span the "tideee" text, leaving ~15 mm stubs each side.
module wordmark_rib_clear() {
  w_clear = 50;    // approx "tideee" text width + small margin
  h_clear = 16;    // tall enough to bracket both ribs that cross the logo
  v_pos   = face_len - wordmark_offset_from_bottom;
  on_front_face(v_pos) {
    translate([-w_clear/2, -h_clear/2, 0])
      cube([w_clear, h_clear, ridge_dia + 0.5]);
  }
}

// PCB mount bosses — sit on the INNER surface of the front face,
// reach 7.6 mm into the cavity so the PCB back-surface is at the
// right depth for glass-flush with the outer front face (pcb stack = 10.6 mm,
// wall = 3 mm  →  inner face to PCB back = 7.6 mm).
module mount_bosses() {
  v_top   = pcb_top_face_offset + pcb_hole_inset_v;
  v_bot   = pcb_top_face_offset + pcb_h - pcb_hole_inset_v;
  u_left  = -pcb_w/2 + pcb_hole_inset_h;
  u_right =  pcb_w/2 - pcb_hole_inset_h;
  pin_d   = boss_pin_d;      // set at top of file — tune for FDM tolerance
  pin_h   = pcb_stack_z - wall;  // 7.6 mm — PCB face sits flush with outer wall
  for (u = [u_left, u_right])
    for (v = [v_top, v_bot])
      on_front_face(v, u) {
        // Pin extends inward from the inner face surface.
        // +1.5 mm overlap into wall ensures mesh is merged (not a separate shell).
        translate([0, 0, -wall - pin_h])
          cylinder(d=pin_d, h=pin_h + 1.5, $fn=20);
        // Boss pad: wider cylinder anchors pin to inner wall face
        translate([0, 0, -wall - 2.0])
          cylinder(d=pin_d + 3.0, h=3.5, $fn=20);
      }
}

module usb_pocket_cut() {
  translate([-usb_w/2,
             D - wall - usb_pocket_d,
             usb_z_center - usb_h/2])
    cube([usb_w, wall + usb_pocket_d + 1, usb_h]);
}

// TV-remote style back closure:
//   - Cover top tongue hooks under back_top_ledge() (no screws)
//   - Cover bottom has a flexible snap arm that clicks past the lower opening edge
//   - To remove: flex the snap arm with a fingernail and slide cover downward

// Ledge at the top of the back opening — cover top tongue slides under this.
// Lives inside the shell wall; never protrudes past the Y=43 mm opening plane.
module back_top_ledge() {
  ledge_w = 2 * (half_w(D - r_back) - wall) - 0.6;  // ≈ 64.2 mm — fits inside opening
  ledge_h = 2.5;   // Z height — tongue slots under this
  ledge_d = 3.5;   // Y depth into shell from opening plane
  y_face  = D - r_back;  // 43 mm — opening plane
  translate([-ledge_w/2, y_face - ledge_d, H_back - wall - ledge_h])
    cube([ledge_w, ledge_d, ledge_h]);
}

// =============================================================
// FRONT SHELL (the main printed body)
// =============================================================
module front_shell() {
  union() {
    difference() {
      union() {
        // wall shell = outer minus inner
        difference() {
          outer_solid();
          inner_solid();
        }
        // rings wrap around front + sides at golden-ratio Z spacings
        wave_ridges();
        // PCB mount pillars on inner front face
        mount_bosses();
      }
      // subtractive features
      screen_window_cut();
      wordmark_emboss();
      wordmark_rib_clear();
      usb_pocket_cut();
      // open the back — cut from D-r_back (=43 mm) outward
      translate([-W_front/2 - 5, D - r_back, -1])
        cube([W_front + 10, r_back + 2, H_back + 2]);
    }
    // Ledge inside the top of the back opening — cover tongue hooks under here.
    back_top_ledge();
  }
}

// =============================================================
// BACK COVER  (TV-remote snap closure — no screws)
//
//   Operation (like a TV remote battery compartment):
//     INSERT: slide top tongue under the ledge, then press bottom in — snaps shut.
//     REMOVE: push snap tab inward with a fingernail, slide cover downward.
//
//   Cover is oriented with +Z = outward (away from shell), +Y = up (toward ledge).
//   Origin at centre of the outer face.
//
//   Top tongue (Y = ch/2 → ch/2+tongue_h): hooks under back_top_ledge().
//     - tongue_h = 2.0 mm tall, full panel thickness — slides under the 2.5 mm ledge.
//
//   Bottom snap arm (centred, inner face, near Y = -ch/2):
//     - arm_thick = 1.0 mm (thin enough to flex ~1.5 mm with finger pressure)
//     - arm_len   = 9.0 mm (long enough for comfortable flex)
//     - arm_w     = 14.0 mm wide
//     - bump_h    = 1.4 mm proud of arm face — catches on lower opening edge (Z=wall=3mm)
//     - bump is a chamfered wedge: gentle ramp on insert side, steeper on lock side
// =============================================================
module back_cover() {
  cw        = 2 * (half_w(D - r_back) - wall) - 0.6;  // ≈ 64.2 mm
  ledge_h   = 2.5;    // must match back_top_ledge() ledge_h
  ch        = H_back - 2*wall - ledge_h - 0.4;  // panel height clears the ledge
  cham      = 0.8;
  tongue_h  = ledge_h - 0.3;   // 2.2 mm — slots under the 2.5 mm ledge

  // U-slot snap tab — lives within the panel bottom, no hanging arm.
  // A slot cut through the OUTER face layer frees a thin inner-face tab.
  // Tab root: Y = -ch/2 + tab_len;  free end: Y = -ch/2 (panel bottom edge).
  // Bump on inner face protrudes +Z into shell, catches on shell inner back
  // wall (Shell Y ≈ 40 mm) when cover is fully pressed in.
  // Release: fingernail notch at outer face bottom lets you tilt cover outward.
  tab_thick  = 1.0;   // inner-face layer left after slot — thin = easy flex
  tab_len    = 9.0;
  tab_w      = 14.0;
  bump_h     = 1.4;
  slot_gap   = 0.6;   // clearance around tab inside the slot

  difference() {
    union() {
      // ── Main panel body ──────────────────────────────────────
      hull() {
        translate([-cw/2,        -ch/2,        0             ]) cube([cw,          ch,          0.01]);
        translate([-cw/2 + cham, -ch/2 + cham, cover_t - 0.01]) cube([cw - 2*cham, ch - 2*cham, 0.01]);
      }
      // ── Top tongue — hooks under back_top_ledge() ────────────
      translate([-cw/2, ch/2, 0])
        cube([cw, tongue_h, cover_t]);
      // ── Snap bump on inner face at panel bottom centre ────────
      // Hull wedge: full bump_h at the free end (Y = -ch/2), tapers to zero
      // 3 mm up.  Bump protrudes in +Z (into shell when installed).
      translate([-tab_w/2, -ch/2, cover_t])
        hull() {
          cube([tab_w, 0.1,     bump_h]);   // full height at bottom edge
          translate([0, bump_h*2, 0])
            cube([tab_w, 0.1, 0.01]);       // tapered to zero 3 mm above
        }
    }

    // ── Vent grid ────────────────────────────────────────────
    for (col = [-2:1:2])
      for (row = [-1:1:1])
        translate([col * 8, row * 8, -0.5])
          cylinder(d=2.2, h=cover_t+1, $fn=16);

    // ── USB-C cable exit hole ──────────────────────────────
    translate([-(usb_w/2 + 1),
               -ch/2 + usb_z_center - usb_h/2 - 1.5,
               -0.1])
      cube([usb_w + 2, usb_h + 3, cover_t + 0.2]);

    // ── U-slot: frees the snap tab to flex ───────────────────
    // Cuts through the outer face layer (Z = 0 … cover_t−tab_thick)
    // around the tab footprint (X/Y), leaving the inner tab intact.
    translate([-tab_w/2 - slot_gap, -ch/2 - 0.1,  -0.1])
      cube([tab_w + 2*slot_gap, tab_len + slot_gap, cover_t - tab_thick + 0.1]);

    // ── Fingernail notch — outer face, bottom centre ──────────
    // Lets you tilt the cover bottom outward to disengage the snap.
    translate([-tab_w/2, -ch/2 - 0.1, cover_t * 0.3])
      cube([tab_w, 2.5, cover_t * 0.5]);
  }
}

// =============================================================
// RENDER SELECTION
// =============================================================
if (PART == "front_shell") {
  color("#D0C8C0") front_shell();
} else if (PART == "back_cover") {
  color("#D0C8C0") back_cover();
} else {
  // Both parts side-by-side for print prep
  color("#D0C8C0") front_shell();
  color("#D0C8C0") translate([W_front + 25, 0, 0]) back_cover();
}
