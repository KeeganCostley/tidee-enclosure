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
//   - Clip-on rear cover with snap catches
//
// Two parts:
//   PART = "front_shell"  → the wave-relief body (open at back)
//   PART = "back_cover"   → the trapezoidal snap-on lid
//
// Print suggestion: 0.2 mm layer, 3 perimeters, 20% gyroid infill,
//   matte PETG or PLA. Print the FRONT SHELL face-up (screen face
//   down on the bed) with tree supports for the overhanging top.
// =============================================================

PART = "front_shell";  // "front_shell" or "back_cover"

$fn = 48;

// -------------------------------------------------------------
// OUTER DIMENSIONS (mm)
// -------------------------------------------------------------
W_front     = 88;     // width at front edge of base
W_back      = 68;     // width at back edge of base
D           = 50;     // depth (front-to-back)
H_front     = 104;    // height at the front edge (from base to top-front corner)
front_lean  = 5;      // degrees: top of front face leans back
top_slope   = 10;     // degrees: top surface drops from front to back
wall        = 3.0;    // wall thickness

r_front     = 14;     // top-view corner radius at the FRONT edge
r_back      = 7;      // top-view corner radius at the BACK edge
r_side      = 6;      // side-profile edge-rounding radius (top/bottom edges)

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
pcb_hole_inset  = 2.5;
pcb_hole_d      = 2.6;
boss_screw_d    = 1.7;   // M2 tapping hole (screw threads in from inside)
boss_screw_depth = 6;    // engagement depth

pcb_top_face_offset = 8;  // mm from top-front corner, along the slanted face,
                          // to the TOP edge of the PCB / screen.

screen_window_w = 50.5;
screen_window_h = 70.5;

// -------------------------------------------------------------
// USB-C PASS-THROUGH POCKET (rear-bottom, vertical back wall)
// -------------------------------------------------------------
usb_w           = 14;
usb_h           = 7;
usb_pocket_d    = 4;
usb_z_center    = 13;

// -------------------------------------------------------------
// WAVE RELIEF (golden-ratio spacing, sine-modulated ribs)
// -------------------------------------------------------------
ridge_dia       = 1.6;
ridge_gap_base  = 2.5;
ridge_ratio     = 1.22;
ridge_y_start   = 6;

// sine modulation along each ridge's length
wave_amp_top    = 2.4;     // amplitude at the sparsest (top) ridge (mm)
wave_amp_bot    = 0.4;     // amplitude at the densest (bottom) ridge (mm)
wave_wavelen    = 70;      // sine wavelength along the rib (mm)
wave_phase_step = 35;      // degrees of phase shift per row
wave_segments   = 28;      // capsule segments per rib (smoother = higher)

// -------------------------------------------------------------
// WORDMARK
// -------------------------------------------------------------
wordmark_text   = "tideee";
wordmark_size   = 11;
wordmark_depth  = 0.6;
wordmark_offset_from_bottom = 14;

// -------------------------------------------------------------
// REAR COVER & CLIPS
// -------------------------------------------------------------
cover_t         = 2.5;
clip_size       = 1.6;
clip_inset_back = 6;

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
    rotate([90 + front_lean, 0, 0])
      children();
}

// =============================================================
// FEATURES
// =============================================================

// Proud horizontal ribs at golden-ratio spacing (densest at the bottom),
// each rib sine-modulated along its length. The dense bottom ribs barely
// wiggle (amp small); the sparse top ribs visibly wave (amp larger).
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

module wave_ridges() {
  L = face_len - ridge_y_start - 4;
  // count rows that will fit (rough)
  n_rows_est = ceil(log(1 + L * (ridge_ratio - 1) / ridge_gap_base) / log(ridge_ratio));
  for (i = [0 : 60]) {
    pos = ridge_gap_base * (pow(ridge_ratio, i) - 1) / (ridge_ratio - 1);
    if (pos < L) {
      v = face_len - ridge_y_start - pos;       // distance from TOP of face
      // skip ribs that cross the screen window
      skip = (v > pcb_top_face_offset - 4 &&
              v < pcb_top_face_offset + screen_window_h + 4);
      if (!skip) {
        // amplitude grows from bottom (i=0) to top (i large)
        t   = (n_rows_est > 1) ? i / (n_rows_est - 1) : 0;
        amp = wave_amp_bot + (wave_amp_top - wave_amp_bot) * t;
        wavy_rib(v, amp=amp, phase=i * wave_phase_step);
      }
    }
  }
}

module screen_window_cut() {
  v_center = pcb_top_face_offset + screen_window_h/2;
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

// PCB mount bosses — sit on the INNER surface of the front face,
// reach 7.6 mm into the cavity so the PCB back-surface is at the
// right depth for glass-flush with the outer front face (pcb stack = 10.6 mm,
// wall = 3 mm  →  inner face to PCB back = 7.6 mm).
module mount_bosses() {
  v_top   = pcb_top_face_offset + pcb_hole_inset;
  v_bot   = pcb_top_face_offset + pcb_h - pcb_hole_inset;
  u_left  = -pcb_w/2 + pcb_hole_inset;
  u_right =  pcb_w/2 - pcb_hole_inset;
  boss_h  = pcb_stack_z - wall;   // 7.6 mm into the cavity
  for (u = [u_left, u_right])
    for (v = [v_top, v_bot])
      on_front_face(v, u)
        translate([0, 0, wall])
          difference() {
            cylinder(d=6, h=boss_h, $fn=24);
            // M2 tapping hole — screw comes in from the PCB side (back opening)
            translate([0, 0, boss_h - boss_screw_depth])
              cylinder(d=boss_screw_d, h=boss_screw_depth + 0.1, $fn=12);
          }
}

module usb_pocket_cut() {
  translate([-usb_w/2,
             D - wall - usb_pocket_d,
             usb_z_center - usb_h/2])
    cube([usb_w, wall + usb_pocket_d + 1, usb_h]);
}

// Small inward beads on the inside of each side wall, near the back.
module snap_catches() {
  z_levels = [25, H_back - 25];
  for (side = [-1, 1])
    for (z = z_levels) {
      x_inner = side * (W_back/2 - wall - 0.3);
      translate([x_inner, D - clip_inset_back, z])
        rotate([0, 90, 0])
          cylinder(d=clip_size, h=3, center=true, $fn=12);
    }
}

// =============================================================
// FRONT SHELL (the main printed body)
// =============================================================
module front_shell() {
  difference() {
    union() {
      // wall shell = outer minus inner
      difference() {
        outer_solid();
        inner_solid();
      }
      // proud waves
      wave_ridges();
      // interior pillars
      mount_bosses();
      // snap catches inside walls
      snap_catches();
    }
    // subtractive features
    screen_window_cut();
    wordmark_emboss();
    usb_pocket_cut();
    // open the back: remove a slab spanning the back face
    translate([-W_front/2 - 5, D - cover_t, -1])
      cube([W_front + 10, cover_t + 2, H_back + 2]);
  }
}

// =============================================================
// BACK COVER (snap-on lid; print flat)
// =============================================================
module back_cover() {
  cw = W_back - 2*wall - 0.6;
  ch = H_back - 2*wall - 0.6;
  difference() {
    union() {
      translate([-cw/2, -ch/2, 0])
        cube([cw, ch, cover_t]);
      // 4 snap bumps (one per shell catch)
      for (side = [-1, 1])
        for (zy = [-ch/2 + 25, ch/2 - 25])
          translate([side * (cw/2 - 0.5), zy, cover_t + clip_size/2])
            rotate([0, 90, 0])
              cylinder(d=clip_size, h=2.5, center=true, $fn=12);
      // finger-pull lip at top
      translate([-cw/4, ch/2 - 3, 0])
        cube([cw/2, 3, cover_t + 1.0]);
    }
    // vent grid
    for (col = [-2:1:2])
      for (row = [-2:1:2])
        translate([col * 7, row * 7, -0.5])
          cylinder(d=2, h = cover_t + 1, $fn=16);
  }
}

// =============================================================
// RENDER SELECTION
// =============================================================
if (PART == "front_shell") {
  color("black") front_shell();
} else if (PART == "back_cover") {
  color("black") back_cover();
} else {
  color("black") front_shell();
  color("black") translate([W_front + 30, 0, 0]) back_cover();
}
