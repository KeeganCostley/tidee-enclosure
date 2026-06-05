// ============================================================
// SEISMONITOR ENCLOSURE — Organic dome monolith (v1)
// Parametric OpenSCAD — reverse-engineered from
// SeisMonitor_Prototype001b.stl (Rhinoceros, Apr 2026)
//
// Body construction: hull() of 4 positioned elliptical cross-
// sections reproduces the expanding-then-tapering dome profile
// and ~20 mm X-lean of the original Rhino prototype.
//
// Overall envelope (matching STL): ≈145 × 108 × 97 mm
//   Base (Z=0):   108 × 80 mm ellipse
//   Widest (Z=25): 141 × 107 mm ellipse  (+X bulge)
//   Mid (Z=65):   109 × 69 mm ellipse    (centre drifts −X)
//   Top (Z=97):    36 × 15 mm ellipse    (further −X lean)
//
// Parts:
//   PART = "shell"       → main enclosure body
//   PART = "base_cover"  → flat snap-on base plate
//   PART = "all"         → both side-by-side
//
// Print suggestion: dome-up orientation, tree supports for the
// undercut base rim, 0.2 mm layers, 3 perimeters, PETG or PLA.
// ============================================================

PART = "all";   // "shell", "base_cover", or "all"

$fn = 64;

// ─── Wall thickness ──────────────────────────────────────────
wall = 3.0;

// ─── Cross-section control points ────────────────────────────
// [z_height, x_center_offset, y_center_offset, x_radius, y_radius]
// Offsets are relative to the base footprint centre.
// Derived from STL slice analysis.
cs = [
  [  0,    0.0,    0.0,  54.0,  40.0 ],   // Z=0  — base footprint
  [ 25,   -2.4,   -0.3,  70.7,  53.5 ],   // Z=25 — widest section
  [ 65,  -14.7,   -1.8,  54.7,  34.5 ],   // Z=65 — upper taper start
  [ 97,  -18.5,  -11.2,  17.9,   7.4 ],   // Z=97 — top crown
];

// ─── Screen / display placeholder ────────────────────────────
// Screen is on the FRONT face (−Y face of the dome).
// Coordinate system: base centre = (0,0,0).
// At Z=55: outer front face ≈ Y = −40.7 mm  (from hull() interpolation).
// The cut slab runs from Y=−52 to Y=−30 → passes through the 3 mm front wall.
// Adjust w/h once PCB / display specs are confirmed.
scr_w       = 65;    // screen window width (mm)
scr_h       = 45;    // screen window height (mm)
scr_z_ctr   = 55;    // Z-centre of window
scr_y_cut   = -52;   // Y-start of cut slab (outside the front face)
scr_y_len   = 25;    // slab depth in Y (must span the ~3 mm wall)

// ─── USB-C / power port (rear base) ──────────────────────────
// At Z=10: outer back face ≈ Y = +45.3 mm  (hull() interpolation).
// The cut slab runs from Y=+42 to Y=+55 → passes through the ~3 mm rear wall.
usb_w       = 14;
usb_h       = 7;
usb_z_ctr   = 10;    // height above base
usb_y_cut   = 42;    // Y-start of cut slab (just inside back face)
usb_y_len   = 14;    // slab depth in Y (must span the rear wall)

// ─── Base cover clearance ────────────────────────────────────
cover_t       = 2.5;
cover_gap     = 0.4;   // radial gap between shell rim and cover

// ─── Helpers ─────────────────────────────────────────────────

// Thin elliptical disk used as a hull() seed.
module ellipse_disk(rx, ry, h = 0.01) {
  scale([rx, ry, 1]) cylinder(r = 1, h = h, $fn = 64);
}

// ─── Core solids ─────────────────────────────────────────────

// Outer envelope: hull of the 4 cross-sections.
module outer_solid() {
  hull()
    for (c = cs)
      translate([c[1], c[2], c[0]])
        ellipse_disk(c[3], c[4]);
}

// Inner cavity: same profile, radii shrunk by wall, floor raised by wall.
module inner_solid() {
  hull()
    for (c = cs)
      translate([c[1], c[2], (c[0] == 0) ? wall : c[0]])
        ellipse_disk(max(1, c[3] - wall), max(1, c[4] - wall));
}

// ─── Features ────────────────────────────────────────────────

// Screen window: rectangular cut through the −Y (front) face.
// The slab starts outside the dome (scr_y_cut) and runs scr_y_len inward,
// passing cleanly through the ≈3 mm front wall.
module screen_window_cut() {
  translate([-scr_w/2, scr_y_cut, scr_z_ctr - scr_h/2])
    cube([scr_w, scr_y_len, scr_h]);
}

// USB-C pocket: through the +Y (rear) face near the base.
// Slab starts just below the outer back surface and runs inward.
module usb_pocket_cut() {
  translate([-usb_w/2, usb_y_cut, usb_z_ctr - usb_h/2])
    cube([usb_w, usb_y_len, usb_h]);
}

// Bottom opening: removes the base so the PCB can be inserted,
// leaving a perimeter rim of width wall.
// (Uncomment once PCB dimensions are confirmed.)
/*
module base_opening() {
  // slightly smaller than base footprint
  hull()
    translate([cs[0][1], cs[0][2], -1])
      ellipse_disk(cs[0][3] - wall - 2, cs[0][4] - wall - 2, h=wall+2);
}
*/

// ─── Main shell ──────────────────────────────────────────────
module shell() {
  difference() {
    union() {
      // Hollow wall
      difference() {
        outer_solid();
        inner_solid();
      }
      // TODO: add PCB mount bosses, snap catches, etc.
    }

    // Screen cut-out
    screen_window_cut();

    // USB port
    usb_pocket_cut();
  }
}

// ─── Base cover (flat snap-on disc) ──────────────────────────
module base_cover() {
  rx = cs[0][3] - wall - cover_gap;
  ry = cs[0][4] - wall - cover_gap;
  // Simple flat disc — add snap arms / screws once feature list finalised
  scale([rx, ry, 1]) cylinder(r=1, h=cover_t, $fn=64);
}

// ─── Render selection ────────────────────────────────────────
if (PART == "shell") {
  color("#BEC8B8") shell();
} else if (PART == "base_cover") {
  color("#BEC8B8") base_cover();
} else {
  color("#BEC8B8") shell();
  color("#BEC8B8") translate([170, 0, 0]) base_cover();
}
