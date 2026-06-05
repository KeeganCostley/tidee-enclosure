// =============================================================
// TIDEEE ENCLOSURE — Wave-relief monolith (v6 — symmetric form)
// For 2.8" CYD ESP32-S3 dev board (LCDwiki ES3C28P)
//
// Body construction: INTERSECTION of two extruded 2D profiles
//   (top-view trapezoid)  ∩  (side-view tilted silhouette)
//
// KEY CHANGE vs v5: top_slope = 0  (top surface is now HORIZONTAL,
// parallel to the base).  This makes the top-front and bottom-front
// corners geometrically identical, so with the same r_side they
// produce a perfect mirror-image mellow when viewed from the front.
// The "vague star" silhouette is now symmetric top-to-bottom.
//
// Two parts:
//   PART = "front_shell"  → the wave-relief body (open at back)
//   PART = "back_cover"   → the snap-on lid
//   PART = "all"          → both side-by-side
//
// Print suggestion: 0.2 mm layer, 3 perimeters, 20% gyroid infill,
//   matte PETG or PLA.
// =============================================================

PART = "all";  // "front_shell", "back_cover", or "all"

$fn = 48;

// -------------------------------------------------------------
// OUTER DIMENSIONS (mm)
// -------------------------------------------------------------
W_front     = 88;     // width at front edge of base
W_back      = 68;     // width at back edge of base
D           = 50;     // depth (front-to-back)
H_front     = 124;    // height at the front edge
front_lean  = 5;      // degrees: top of front face leans back
top_slope   = 0;      // degrees: 0 = horizontal top → symmetric corners top/bottom
wall        = 3.0;    // wall thickness

r_front     = 14;     // top-view corner radius at the FRONT edge
r_back      = 7;      // top-view corner radius at the BACK edge
r_side      = 20;     // side-profile corner rounding — large value = dramatic
                      // rounded-rectangle silhouette; top mirrors base exactly

// derived
top_front_y = H_front * tan(front_lean);                          // ≈ 10.85
top_depth   = D - top_front_y;                                     // ≈ 39.15
H_back      = H_front - top_depth * tan(top_slope);               // = H_front = 124 mm
face_len    = sqrt(top_front_y*top_front_y + H_front*H_front);    // ≈ 124.5 mm

// half-width of trapezoid at a given y (depth into device)
function half_w(y) = W_front/2 - ((W_front - W_back)/2) * (y / D);

// -------------------------------------------------------------
// CYD BOARD (LCDwiki ES3C28P, 2.8")
// -------------------------------------------------------------
pcb_w           = 50;
pcb_h           = 86;
pcb_stack_z     = 10.6;
pcb_hole_inset_v = 4.0;
pcb_hole_inset_h = 3.5;
pcb_hole_d       = 3.5;

pcb_top_face_offset = 22; // mm from top-front corner to top edge of PCB
                          // 22 → window top at v=30 mm (10 mm clear of the r_side=20
                          // rounded zone); top bosses at v=26 mm (on flat face)
glass_from_pcb_top  = 8;  // mm from PCB top edge to top of screen glass

screen_window_w = 51.0;   // 50 mm glass + 0.5 mm each side
screen_window_h = 71.0;   // 70 mm glass + 0.5 mm each side

// -------------------------------------------------------------
// USB-C PASS-THROUGH POCKET (rear, vertical back wall)
// -------------------------------------------------------------
usb_w           = 14;
usb_h           = 7;
usb_pocket_d    = 4;
usb_z_center    = 20;

// -------------------------------------------------------------
// WAVE RELIEF
// -------------------------------------------------------------
ridge_dia       = 1.6;
ridge_gap_base  = 2.5;
ridge_ratio     = 1.22;
ridge_y_start   = 6;

wave_amp_top    = 2.4;
wave_amp_bot    = 0.4;
wave_wavelen    = 70;
wave_phase_step = 35;
wave_segments   = 28;

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
clip_inset_back = 8;


// =============================================================
// 2D PROFILES
// =============================================================

module footprint_top_2d() {
  hull() {
    translate([-W_front/2 + r_front, r_front])         circle(r=r_front);
    translate([ W_front/2 - r_front, r_front])         circle(r=r_front);
    translate([ W_back/2  - r_back,  D - r_back])      circle(r=r_back);
    translate([-W_back/2  + r_back,  D - r_back])      circle(r=r_back);
  }
}

// Side-view silhouette.  With top_slope=0, the top surface is horizontal
// (H_back = H_front), so the top-front corner mirrors the base-front corner.
//   BF (0,0) → BB (D,0) → TB (D,H_back) → TF (top_front_y,H_front)
module footprint_side_2d() {
  offset(r=r_side) offset(r=-r_side)
    polygon([[0,0], [D,0], [D,H_back], [top_front_y,H_front]]);
}


// =============================================================
// 3D SOLIDS
// =============================================================

module top_view_prism() {
  linear_extrude(height = H_front + 20)
    footprint_top_2d();
}

module side_view_prism() {
  W_extrude = W_front + 40;
  translate([-W_extrude/2, 0, 0])
    rotate([90, 0, 90])
      linear_extrude(height = W_extrude)
        footprint_side_2d();
}

module outer_solid() {
  intersection() {
    top_view_prism();
    side_view_prism();
  }
}

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
// =============================================================
module on_front_face(v_along_face, u=0) {
  world_y = top_front_y - v_along_face * sin(front_lean);
  world_z = H_front     - v_along_face * cos(front_lean);
  translate([u, world_y, world_z])
    rotate([90 - front_lean, 0, 0])
      children();
}


// =============================================================
// FEATURES
// =============================================================

module wavy_wrap_ring(z_level, amp, phase, max_y) {
  n    = wave_segments * 2;
  xext = W_front / 2 + 10;
  step = (2 * xext) / n;

  difference() {
    intersection() {
      intersection() {
        linear_extrude(H_front + 20)
          offset(r = ridge_dia/2) footprint_top_2d();
        translate([-(W_front + 40)/2, 0, 0])
          rotate([90, 0, 90])
            linear_extrude(W_front + 40)
              offset(r = ridge_dia/2) footprint_side_2d();
      }
      union() {
        for (j = [0 : n - 1]) {
          xj = -xext + j * step;
          zj = z_level + amp * sin(360 * xj / wave_wavelen + phase);
          translate([xj, 0, zj - ridge_dia/2])
            cube([step + 0.01, max_y + 1, ridge_dia]);
        }
      }
    }
    outer_solid();
  }
}

// V-shape taper: ribs wrap deepest at both top AND bottom extremes,
// shallowest at centre — perfectly matching the symmetric corner geometry.
module wave_ridges() {
  L          = face_len - ridge_y_start - 4;
  n_rows_est = ceil(log(1 + L * (ridge_ratio - 1) / ridge_gap_base) / log(ridge_ratio));
  y_shallow  = 5;
  y_deep     = D - r_back;
  v_max      = face_len - ridge_y_start;

  for (i = [0 : 60]) {
    pos = ridge_gap_base * (pow(ridge_ratio, i) - 1) / (ridge_ratio - 1);
    if (pos < L) {
      v       = face_len - ridge_y_start - pos;
      t       = (n_rows_est > 1) ? min(i / (n_rows_est - 1), 1) : 0;
      amp     = wave_amp_bot + (wave_amp_top - wave_amp_bot) * t;
      z_level = H_front - v * cos(front_lean);
      tw_norm = v / v_max;
      tw_sym  = abs(2 * tw_norm - 1);
      max_y   = y_shallow + (y_deep - y_shallow) * tw_sym;
      wavy_wrap_ring(z_level, amp=amp, phase=i * wave_phase_step, max_y=max_y);
    }
  }
}

module screen_window_cut() {
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

module wordmark_rib_clear() {
  w_clear = 50;
  h_clear = 16;
  v_pos   = face_len - wordmark_offset_from_bottom;
  on_front_face(v_pos) {
    translate([-w_clear/2, -h_clear/2, 0])
      cube([w_clear, h_clear, ridge_dia + 0.5]);
  }
}

module mount_bosses() {
  v_top   = pcb_top_face_offset + pcb_hole_inset_v;
  v_bot   = pcb_top_face_offset + pcb_h - pcb_hole_inset_v;
  u_left  = -pcb_w/2 + pcb_hole_inset_h;
  u_right =  pcb_w/2 - pcb_hole_inset_h;
  pin_d   = 3.4;
  pin_h   = pcb_stack_z - wall;
  for (u = [u_left, u_right])
    for (v = [v_top, v_bot])
      on_front_face(v, u)
        translate([0, 0, -wall - pin_h])
          cylinder(d=pin_d, h=pin_h, $fn=20);
}

module usb_pocket_cut() {
  translate([-usb_w/2,
             D - wall - usb_pocket_d,
             usb_z_center - usb_h/2])
    cube([usb_w, wall + usb_pocket_d + 1, usb_h]);
}

module cover_stop_ledge() {
  ledge_in  = 2.0;
  ledge_y   = 2.5;
  y_face    = D - r_back;
  x_inner   = half_w(y_face) - wall;

  for (side = [-1, 1]) {
    x0 = (side > 0) ? x_inner - ledge_in : -x_inner;
    translate([x0, y_face - ledge_y, 0])
      cube([ledge_in, ledge_y, H_back]);
  }
}

module snap_catches() {
  notch_d = 2.2;
  notch_h = 5.4;
  notch_w = 3.2;
  notch_y  = D - clip_inset_back;
  x_inner  = half_w(notch_y) - wall;
  z_levels = [25, H_back - 25];
  for (side = [-1, 1])
    for (z = z_levels) {
      x0 = (side > 0) ? x_inner : -(x_inner + notch_d);
      translate([x0, notch_y - notch_h/2, z - notch_w/2])
        cube([notch_d, notch_h, notch_w]);
    }
}

// Top engagement ledge — cover top edge slides under this shelf first.
// Z : H_back-(wall+0.6) → H_back
module top_cover_ledge() {
  cw_inner = W_back - 2*wall - 0.6;
  ledge_d  = 3.0;
  ledge_h  = wall + 0.6;
  y_face   = D - r_back;
  z_bot    = H_back - ledge_h;
  translate([-cw_inner/2, y_face - ledge_d, z_bot])
    cube([cw_inner, ledge_d, ledge_h]);
}


// =============================================================
// FRONT SHELL
// =============================================================
module front_shell() {
  union() {
    difference() {
      union() {
        difference() {
          outer_solid();
          inner_solid();
        }
        wave_ridges();
        mount_bosses();
        cover_stop_ledge();
      }
      screen_window_cut();
      wordmark_emboss();
      wordmark_rib_clear();
      usb_pocket_cut();
      snap_catches();
      translate([-W_front/2 - 5, D - r_back, -1])
        cube([W_front + 10, r_back + 2, H_back + 2]);
    }
    top_cover_ledge();
  }
}


// =============================================================
// BACK COVER — top-pivot + 2 bottom snaps
// Cover is now taller (ch ≈ 117.4 mm) because H_back = H_front = 124 mm.
// =============================================================
module back_cover() {
  cw = W_back - 2*wall - 0.6;   // 61.4 mm
  ch = H_back - 2*wall - 0.6;   // ≈ 117.4 mm

  arm_t    = 1.2;
  arm_w    = 7.0;
  arm_z    = clip_inset_back;
  bump_h   = 3.0;
  bump_l   = 3.0;
  flex_gap = 3.5;

  zy_bot = -ch/2 + 25;   // maps to shell Z = 25 mm (lower notch pair)

  difference() {
    union() {
      // Main plate
      translate([-cw/2, -ch/2, 0])
        cube([cw, ch, cover_t]);

      // 2 bottom snap arms
      for (side = [-1, 1]) {
        arm_x  = (side > 0) ?  cw/2 - arm_t : -cw/2;
        bump_x = (side > 0) ?  cw/2          : -cw/2 - bump_h;

        translate([arm_x, zy_bot - arm_w/2, 0])
          cube([arm_t, arm_w, arm_z]);

        hull() {
          translate([(side > 0) ? cw/2 : -cw/2 - 0.01,
                     zy_bot - arm_w/2, arm_z - 0.2])
            cube([0.01, arm_w, 0.2]);
          translate([bump_x, zy_bot - arm_w/2, arm_z - bump_l])
            cube([bump_h, arm_w, bump_l - 0.2]);
        }
      }

      // Finger-pull ridge at bottom
      translate([-cw/4, -ch/2, 0])
        cube([cw/2, 4, cover_t + 1.2]);

      // Top-edge insert guide chamfer
      hull() {
        translate([-cw/2, ch/2,       0]) cube([cw, 0.01, cover_t]);
        translate([-cw/2, ch/2 + 1.0, 0]) cube([cw, 0.01, cover_t - 1.0]);
      }
    }

    // Vent grid
    for (col = [-2:1:2])
      for (row = [-2:1:2])
        translate([col * 7, row * 7, -0.5])
          cylinder(d=2, h=cover_t+1, $fn=16);

    // Flex slots
    for (side = [-1, 1]) {
      sx = (side > 0) ? cw/2 - arm_t - flex_gap : -cw/2 + arm_t;
      translate([sx, zy_bot - arm_w/2 - 0.1, -0.1])
        cube([flex_gap, arm_w + 0.2, arm_z + 0.2]);
    }

    // USB-C cable exit hole
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
  color("#D0C8C0") front_shell();
  color("#D0C8C0") translate([W_front + 25, 0, 0]) back_cover();
}
