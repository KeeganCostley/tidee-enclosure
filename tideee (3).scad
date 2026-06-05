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
pcb_hole_inset_v = 4.0;   // vertical inset: (86 - 78) / 2 = 4 mm
pcb_hole_inset_h = 3.5;   // horizontal inset: (50 - 43) / 2 = 3.5 mm
pcb_hole_d       = 3.5;   // measured hole diameter (M3 clearance)

pcb_top_face_offset = 4;  // mm from top-front corner to the TOP edge of the PCB
                          // 4 → window top at v=12 mm (6 mm clear of the r_side=6 corner
                          // rounding so it isn't clipped); top bosses at v=8 mm (on the
                          // flat face, not inside the roof); lip above screen = 12 mm
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
wordmark_text   = "tidee";
wordmark_size   = 11;
wordmark_depth  = 0.6;
wordmark_offset_from_bottom = 14;

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

// All rib geometry:
//   above screen  → wavy_rib        (face capsule only)
//   screen zone   → skipped         (clean window frame, no stubs)
//   below screen  → wavy_wrap_ring  (same sine wave, wraps onto side walls)
module wave_ridges() {
  L          = face_len - ridge_y_start - 4;
  n_rows_est = ceil(log(1 + L * (ridge_ratio - 1) / ridge_gap_base) / log(ridge_ratio));
  scr_top      = pcb_top_face_offset + glass_from_pcb_top;  // 12 mm
  scr_bot      = scr_top + screen_window_h;                  // 83 mm
  scr_margin   = 4;                   // mm gap above/below screen edges
  v_wrap_start = scr_bot + scr_margin;                       // 87 mm
  v_wrap_end   = face_len - ridge_y_start;                   // ~118 mm
  y_shallow    = 15;          // side-depth of topmost wrap ring (mm)
  y_deep       = D - r_back;  // side-depth of bottommost ring (mm)

  for (i = [0 : 60]) {
    pos = ridge_gap_base * (pow(ridge_ratio, i) - 1) / (ridge_ratio - 1);
    if (pos < L) {
      v   = face_len - ridge_y_start - pos;
      t   = (n_rows_est > 1) ? min(i / (n_rows_est - 1), 1) : 0;
      amp = wave_amp_bot + (wave_amp_top - wave_amp_bot) * t;

      if (v < scr_top - scr_margin) {
        // Above screen: front-face capsule only
        wavy_rib(v, amp=amp, phase=i * wave_phase_step);
      } else if (v > v_wrap_start) {
        // Below screen: single wavy object spanning front face + sides
        z_level = H_front - v * cos(front_lean);
        tw      = (v - v_wrap_start) / (v_wrap_end - v_wrap_start);
        max_y   = y_shallow + (y_deep - y_shallow) * tw;
        wavy_wrap_ring(z_level, amp=amp, phase=i * wave_phase_step, max_y=max_y);
      }
      // v in screen zone: skip — clean uninterrupted window frame
    }
  }
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
  pin_d   = 3.4;             // slightly under pcb_hole_d (3.5 mm) — easy slide fit
  pin_h   = pcb_stack_z - wall;  // 7.6 mm — PCB face sits flush with outer wall
  for (u = [u_left, u_right])
    for (v = [v_top, v_bot])
      on_front_face(v, u)
        // Pin extends inward from the inner face surface
        translate([0, 0, -wall - pin_h])
          cylinder(d=pin_d, h=pin_h, $fn=20);
}

module usb_pocket_cut() {
  translate([-usb_w/2,
             D - wall - usb_pocket_d,
             usb_z_center - usb_h/2])
    cube([usb_w, wall + usb_pocket_d + 1, usb_h]);
}

// Inward stop ledge — two narrow shelves on the inner side walls just inside
// the back opening.  The cover plate (61.4 mm wide) rests on these ledges
// (which narrow the effective opening to ≈ 60.8 mm) so it cannot fall
// through before the snap arms have been aligned and pressed home.
module cover_stop_ledge() {
  ledge_in  = 2.0;          // protrudes inward from inner wall face (X)
  ledge_y   = 2.5;          // depth into cavity from the opening face (Y)
  y_face    = D - r_back;   // 43 mm — back opening plane
  x_inner   = half_w(y_face) - wall;  // ≈ 32.4 mm inner wall surface at that Y

  for (side = [-1, 1]) {
    x0 = (side > 0) ? x_inner - ledge_in : -x_inner;
    translate([x0, y_face - ledge_y, 0])
      cube([ledge_in, ledge_y, H_back]);
  }
}

// Rectangular notch recesses in the inner side walls — used SUBTRACTIVELY.
// The cover's cantilever snap arms click into these notches.
module snap_catches() {
  notch_d = 2.2;              // depth into wall (X direction)
  notch_h = 5.4;              // notch height in Y (insert direction)
  notch_w = 3.2;              // notch width in Z
  notch_y  = D - clip_inset_back;          // Y position of notch centre
  x_inner  = half_w(notch_y) - wall;       // inner wall surface at that Y
  z_levels = [25, H_back - 25];
  for (side = [-1, 1])
    for (z = z_levels) {
      x0 = (side > 0) ? x_inner : -(x_inner + notch_d);
      translate([x0, notch_y - notch_h/2, z - notch_w/2])
        cube([notch_d, notch_h, notch_w]);
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
      // rings wrap around front + sides at golden-ratio Z spacings;
      // clipping is handled inside wave_ridges() itself.
      wave_ridges();
      // interior pillars
      mount_bosses();
      // stop ledge — prevents cover from falling through before snapping
      cover_stop_ledge();
    }
    // subtractive features
    screen_window_cut();
    wordmark_emboss();
    wordmark_rib_clear();  // clears rib centre over the logo, keeps side stubs
    usb_pocket_cut();
    snap_catches();   // notch recesses in side walls for cover clips
    // open the back fully — start cut at D-r_back (=43 mm) where the
    // inner cavity is already 62 mm wide and fully visible from behind.
    // (Starting at D-wall=47 mm would expose only a ~4 mm inner radius
    // at the corners, making the cavity look closed from the rear.)
    translate([-W_front/2 - 5, D - r_back, -1])
      cube([W_front + 10, r_back + 2, H_back + 2]);
  }
}

// =============================================================
// BACK COVER (snap-on lid; print flat)
// =============================================================
module back_cover() {
  cw = W_back - 2*wall - 0.6;
  ch = H_back - 2*wall - 0.6;

  // Cantilever snap arm parameters
  arm_t    = 0.8;             // thin for easy flex
  arm_w    = 5.0;             // arm width in Y
  arm_z    = clip_inset_back; // arm length = clip_inset_back so tip reaches notch
  bump_h   = 2.5;             // bump must bridge the 1.9 mm gap to inner wall + overlap
  bump_l   = 2.8;             // bump length in Z
  flex_gap = 2.5;             // must be ≥ bump compression needed (2.2 mm) to clear opening

  difference() {
    union() {
      // Main plate
      translate([-cw/2, -ch/2, 0])
        cube([cw, ch, cover_t]);

      // 4 cantilever snap arms — one per shell notch
      for (side = [-1, 1])
        for (zy = [-ch/2 + 25, -ch/2 + H_back - 25]) {
          // Arm body: sits just inside the cover edge, runs full arm_z in Z
          arm_x  = (side > 0) ? cw/2 - arm_t : -cw/2;
          bump_x = (side > 0) ? cw/2          : -cw/2 - bump_h;
          translate([arm_x, zy - arm_w/2, 0])
            cube([arm_t, arm_w, arm_z]);
          // Rectangular bump at arm tip with a leading chamfer for smooth insertion.
          // hull() tapers protrusion to zero at the very tip (Z=arm_z),
          // giving a ramp that cams the arm inward as the cover is pressed in.
          hull() {
            translate([(side>0) ? cw/2 : -cw/2 - 0.01,
                       zy - arm_w/2, arm_z - 0.2])
              cube([0.01, arm_w, 0.2]);          // tapered tip: no protrusion
            translate([bump_x, zy - arm_w/2, arm_z - bump_l])
              cube([bump_h, arm_w, bump_l - 0.2]); // full bump behind the tip
          }
        }

      // Finger-pull lip
      translate([-cw/4, ch/2 - 3, 0])
        cube([cw/2, 3, cover_t + 1.0]);
    }

    // Vent grid
    for (col = [-2:1:2])
      for (row = [-2:1:2])
        translate([col * 7, row * 7, -0.5])
          cylinder(d=2, h=cover_t+1, $fn=16);

    // Flex slots — isolate each arm from the cover body so it can bend in X
    for (side = [-1, 1])
      for (zy = [-ch/2 + 25, -ch/2 + H_back - 25]) {
        sx = (side > 0) ? cw/2 - arm_t - flex_gap : -cw/2 + arm_t;
        translate([sx, zy - arm_w/2 - 0.1, -0.1])
          cube([flex_gap, arm_w + 0.2, arm_z + 0.2]);
      }

    // USB-C cable exit hole — generous clearance for a straight cable.
    // Centred on usb_z_center (shell Z = 13 mm = PCB bottom edge).
    // 16 mm wide × 10 mm tall gives plenty of room for connector + cable body.
    translate([-(usb_w/2 + 1),
               -ch/2 + usb_z_center - usb_h/2 - 1.5,
               -0.1])
      cube([usb_w + 2, usb_h + 3, cover_t + 0.2]);
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
