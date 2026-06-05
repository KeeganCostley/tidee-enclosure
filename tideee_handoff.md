# TIDEEE Enclosure — Design Handoff Package
**File:** `tideee (5).scad`  
**Board:** LCDwiki ES3C28P — 2.8" CYD ESP32-S3  
**Last updated:** 2026-06-02

---

## 1. Construction Method

The body is built by **intersecting two extruded 2D profiles** — no polyhedron, no minkowski.

- **Top-view prism** — trapezoidal footprint extruded vertically
- **Side-view prism** — leaning/sloping silhouette extruded horizontally

`outer_solid() = intersection(top_view_prism, side_view_prism)`  
`inner_solid()` = same profiles offset inward by `wall = 3.0 mm`  
Shell = `outer_solid - inner_solid`

The r_side = 10 mm rounding is applied via `offset(r=10) offset(r=-10)` on the side profile polygon — this rounds all four side-profile corners (base-front, base-back, top-back, top-front) smoothly.

---

## 2. Outer Body Dimensions

| Parameter | Value | Notes |
|---|---|---|
| `W_front` | 88 mm | Width at front edge (base) |
| `W_back` | 68 mm | Width at back edge (base) |
| `D` | 50 mm | Depth front-to-back |
| `H_front` | 124 mm | Height at front edge |
| `H_back` | ≈ 118.65 mm | Height at back edge (derived) |
| `front_lean` | 9° | Front face leans rearward |
| `top_slope` | 10° | Top surface drops front-to-back |
| `wall` | 3.0 mm | Uniform wall thickness |
| `r_front` | 14 mm | Top-view corner radius, front |
| `r_back` | 7 mm | Top-view corner radius, back |
| `r_side` | 10 mm | Side-profile edge rounding |

**Derived values (computed by OpenSCAD):**

| Variable | Formula | Value |
|---|---|---|
| `top_front_y` | `H_front * tan(front_lean)` | ≈ 19.64 mm |
| `top_depth` | `D - top_front_y` | ≈ 30.36 mm |
| `H_back` | `H_front - top_depth * tan(top_slope)` | ≈ 118.65 mm |
| `face_len` | `sqrt(top_front_y² + H_front²)` | ≈ 125.5 mm |

**Half-width helper:** `half_w(y) = W_front/2 - ((W_front - W_back)/2) * (y / D)`  
→ At the back opening plane (y = 43 mm): `half_w(43) = 35.4 mm`

---

## 3. Back Opening

The back face is cut open at `Y = D - r_back = 43 mm`.

| Dimension | Value |
|---|---|
| Opening plane | Y = 43 mm |
| Outer opening width | 2 × half_w(43) = 70.8 mm |
| Inner opening width | 2 × (half_w(43) − wall) = **64.8 mm** |
| Inner opening height | H_back − 2 × wall ≈ **112.65 mm** |
| Shell inner back wall at Y | 43 − 3 = **40 mm** |

---

## 4. PCB / Board Specs

| Parameter | Value |
|---|---|
| PCB width | 50 mm |
| PCB height | 86 mm |
| PCB stack height (PCB + screen + connector) | 10.6 mm |
| Mounting hole diameter (on board) | 3.5 mm |
| Hole inset from PCB top/bottom edges | 4.0 mm |
| Hole inset from PCB left/right edges | 3.5 mm |
| Printed boss pin diameter | **2.6 mm** (FDM undersized) |
| Boss pin height | 7.6 mm (= pcb_stack_z − wall) |
| PCB top edge from face top (`pcb_top_face_offset`) | 8 mm |
| Screen glass top from PCB top edge | 8 mm |

**Boss pin positions** (measured along face from top, horizontal offset from centre):

| Boss | v (down face) | u (horizontal) |
|---|---|---|
| Top-left | 12 mm | −21.5 mm |
| Top-right | 12 mm | +21.5 mm |
| Bottom-left | 90 mm | −21.5 mm |
| Bottom-right | 90 mm | +21.5 mm |

---

## 5. Screen Window Cutout

Cut through the front face (wall + clearance):

| Parameter | Value |
|---|---|
| Width | **51.0 mm** (50 mm glass + 0.5 mm each side) |
| Height | **71.0 mm** (70 mm glass + 0.5 mm each side) |
| Centre distance from face top | 51.5 mm along face |
| Cut depth | wall + 4 mm = 7 mm |
| Horizontal offset from centre | 0 (centred) |

---

## 6. USB-C Pocket (Back Face, Near Base)

| Parameter | Value |
|---|---|
| Pocket width | 14 mm |
| Pocket height | 7 mm |
| Pocket depth into wall | 4 mm + clearance |
| Centre height from base (Z) | **20 mm** |
| Position | Centred on back face |

---

## 7. Wave Rib System

Ribs are **full-wrap sine-modulated rings** (`wavy_wrap_ring`) — each rib is one continuous object spanning the front face, rounded front corners, and side walls.

| Parameter | Value | Notes |
|---|---|---|
| `ridge_dia` | 1.2 mm | Rib cross-section diameter |
| `ridge_gap_base` | 4.5 mm | Min gap at densest point (bottom) |
| `ridge_ratio` | 1.22 | Golden-ratio spacing multiplier |
| `ridge_y_start` | 2 mm | Series starts 2 mm from face base |
| `wave_amp_top` | 1.6 mm | Amplitude at topmost (sparse) ribs |
| `wave_amp_bot` | 0.4 mm | Amplitude at bottommost (dense) ribs |
| `wave_wavelen` | 70 mm | Sine wavelength along rib |
| `wave_phase_step` | 35° | Phase shift per row |
| `wave_segments` | 48 | Capsule segments per rib |

**Dedicated top rib:** hardcoded at **6 mm from face top** (independent of `ridge_y_start`).

**Side-wall reach taper:** V-shape — ribs wrap fully around base AND top corners (`max_y = 43 mm`), taper to minimum at screen bezel zone (`max_y = 5 mm`).

---

## 8. Wordmark

| Parameter | Value |
|---|---|
| Text | `"tidee"` |
| Font | Liberation Sans Bold |
| Size | 11 mm |
| Depth (deboss) | 0.6 mm |
| Centre from face bottom (along face) | **20 mm** |
| Rib-clear zone around text | 50 mm wide × 16 mm tall |

---

## 9. Back Cover — TV Remote Snap Closure

No screws. Hook top in, press bottom to click shut. Fingernail at bottom to release.

### Cover panel
| Parameter | Value | Formula |
|---|---|---|
| `cw` (width) | ≈ 64.2 mm | `2 × (half_w(43) − wall) − 0.6` |
| `ch` (height) | ≈ 109.75 mm | `H_back − 2×wall − ledge_h − 0.4` |
| `cover_t` (thickness) | 2.5 mm | — |
| Entry chamfer | 0.8 mm × 45° | Guides panel into opening |

### Top tongue (hooks under shell ledge)
| Parameter | Value |
|---|---|
| `tongue_h` | 2.2 mm tall |
| Width | = `cw` (full panel width) |
| Thickness | = `cover_t` (2.5 mm) |

### Shell ledge (`back_top_ledge`)
| Parameter | Value |
|---|---|
| Ledge width | ≈ 64.2 mm |
| `ledge_h` | 2.5 mm (Z height) |
| `ledge_d` | 3.5 mm (Y depth into shell) |
| Z position | H_back − wall − ledge_h = ≈ 113.15 mm from base |
| Y position | 39.5 mm → 43 mm (inside wall, never protrudes) |

### Bottom snap tab (U-slot cantilever)
| Parameter | Value | Notes |
|---|---|---|
| `tab_w` | 14 mm | Centred on X |
| `tab_len` | 9 mm | Arm free length (root 9 mm above bottom) |
| `tab_thick` | 1.0 mm | Inner face layer — thin for flex |
| `bump_h` | 1.4 mm | Protrusion into shell |
| Slot gap | 0.6 mm | Clearance around tab in slot |
| Catch point | Shell inner back wall at Y ≈ 40 mm | Bump reaches Y ≈ 38.6 mm — 1.4 mm past wall |

**How it works:**
1. Insert: angle cover, slide top tongue under ledge first
2. Press bottom in — bump flexes past shell inner back wall, clicks
3. Remove: fingernail in bottom notch, tilt bottom outward → bump disengages → slide tongue out

### Vent grid
5 × 3 grid of Ø2.2 mm holes, spaced 8 mm apart (centred in panel body, above USB hole).

### USB exit hole
16 mm wide × 10 mm tall, centred horizontally, positioned to align with shell USB pocket at Z = 20 mm.

---

## 10. Print Settings (Bambu Studio)

| Setting | Value |
|---|---|
| Layer height | 0.2 mm |
| Perimeters | 3 |
| Infill | 20% Gyroid |
| Supports | Tree (for front_shell) |
| Material | Matte PETG or PLA |
| Avoid crossing walls | Process tab → Quality → uncheck "Avoid crossing walls" |
| Seam | Rear / Aligned |

**Print orientation:**
- `front_shell` — screen face DOWN on bed, tree supports for overhanging top
- `back_cover` — outer face DOWN on bed, no supports needed

---

## 11. OpenSCAD Module Summary

| Module | Purpose |
|---|---|
| `footprint_top_2d()` | Trapezoidal top-view 2D profile |
| `footprint_side_2d()` | Leaning/sloping side-view 2D profile (r_side rounded) |
| `outer_solid()` | Full outer body (intersection of 2 prisms) |
| `inner_solid()` | Inner cavity (same, inset by wall) |
| `on_front_face(v, u)` | Places children on the slanted front face |
| `wavy_rib(v, amp, phase)` | Single rib on front face only (legacy) |
| `wavy_wrap_ring(z, amp, phase, max_y)` | Full-wrap rib spanning front + corners + sides |
| `wave_ridges()` | All ribs — golden-ratio loop + dedicated top rib |
| `screen_window_cut()` | Screen aperture subtraction |
| `wordmark_emboss()` | "tidee" deboss on front face |
| `wordmark_rib_clear()` | Clears ribs in wordmark zone |
| `mount_bosses()` | 4× PCB mount pins on inner front face |
| `usb_pocket_cut()` | USB-C slot through back wall |
| `back_top_ledge()` | Horizontal shelf inside top of back opening |
| `front_shell()` | Complete front body with all features |
| `back_cover()` | Snap-fit back panel |

**Render control:** `PART = "front_shell"` / `"back_cover"` / `"all"`

---

## 12. Known Tuning Notes

- `boss_pin_d = 2.6 mm` — may need further reduction depending on printer tolerance (started at 3.4 → 2.8 → 2.6)
- `ridge_y_start = 2` — lowered from 6 to eliminate stringing at the base; top rib is now hardcoded separately at 6 mm from face top
- `wordmark_offset_from_bottom = 20` — raised from 14 to keep text above the stringing zone
- Back snap tab is a **first print** — bump engagement (1.4 mm) and tab thickness (1.0 mm) may need tuning after test print

---

*Source file: `C:\Users\Khygan\Documents\Openscan +claude\tideee (5).scad`*
