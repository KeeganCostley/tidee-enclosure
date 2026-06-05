# Tidee Enclosure — Design Checklist
*Reference for every update. Check all items before calling a build done.*

---

## Design Intent (Non-Negotiable Aesthetics)

- [ ] **Wave ribs pack densely at the base** — tactile grip zone, tightest at z=10mm
- [ ] **Ribs spread outward geometrically toward the top** — elegant logarithmic fan, not uniform spacing
- [ ] **Ribs AND wordmark coexist** — a flat panel around the text with ribs above and below it, matching the OpenSCAD original
- [ ] **Wordmark "tidee" is readable** — debossed text, not a slot or invisible
- [ ] **Ribs are visually prominent** — 1.6mm proud beads, should be clearly visible at oblique view and tactile when printed
- [ ] **Wave amplitude increases toward top** — subtle undulation at base (0.8mm), more expressive higher up (2.4mm)

---

## Body & Shell

- [ ] W_front=88mm, W_back=68mm, D=50mm, H_front=124mm
- [ ] front_lean=9° (face leans backward), top_slope=10° (top drops front-to-back)
- [ ] wall=3mm shell thickness throughout
- [ ] r_front=14mm, r_back=7mm (top-view corner radii)
- [ ] r_side=10mm (side-view corner radii — affects rib/wordmark Y positioning)
- [ ] Base chamfer ~2.5mm on bottom perimeter edges
- [ ] Top edge fillet ~3mm

---

## Wave Rib System

- [ ] **15 ribs generated** (ribs 0–13 + top rib) — check terminal output
- [ ] **All ribs fused to outer solid BEFORE hollowing** — not to the hollow shell
- [ ] Rib positions use `_front_face_outer_y(wz)` — NOT `on_front_face()` raw Y (this was the root bug; raw Y is ~3.3mm behind the actual surface)
- [ ] Rib tip is 1.6mm proud of actual outer surface
- [ ] 0.5mm of each rib box is embedded into the wall for OCC fuse contact
- [ ] Geometric spacing: gap_base=3.0mm, gap_ratio=1.15 (each gap 15% wider than previous)
- [ ] wave_amp goes from 0.8mm (bottom) → 2.4mm (top)
- [ ] wave_wavelen=70mm, wave_phase_step=35° between successive ribs
- [ ] wave_segments=48 (horizontal resolution per rib)
- [ ] Side-strip ribs survive in screen zone (screen window removes only the centre)
- [ ] Rib 0 (z=10mm) survives BELOW the wordmark clear zone

---

## Wordmark

- [ ] Text: "tidee", font: Liberation Sans, size: 11pt, Bold
- [ ] Deboss depth: 0.6mm into the outer face
- [ ] Position: wordmark_offset_from_bottom=20mm from base
- [ ] Plane origin uses `_front_face_outer_y(wz)` — NOT raw `on_front_face()` Y
- [ ] Extrude uses **inward-offset plane + positive (outward) extrude** technique — negative extrude on tilted custom plane is unreliable outside BuildPart in build123d
- [ ] Rib-clear zone: 50mm wide × 14mm tall, centred on wordmark, clears z≈12.75–26.75mm
- [ ] Rib-clear only removes proud rib bumps (extends outward from face) — must NOT carve into the shell wall
- [ ] "tidee" is legible in final print — verify by zooming in on OCP viewer after run

---

## Screen Window

- [ ] 51×71mm rectangular cut through slanted front face
- [ ] Centred at v_c=51.5mm down from top of face
- [ ] Uses Box+Rotation(-front_lean)+Location approach (NOT sketch+extrude on tilted plane)
- [ ] Passes cleanly through full wall thickness (box is 20mm deep)

---

## USB-C Pocket

- [ ] 14×8mm opening, 12mm deep, at base of back wall (Y=D=50mm)
- [ ] Flush with outer back face, cutting inward

---

## Back Opening

- [ ] Full-height rectangular opening (preserves USB pocket at base)
- [ ] Width = inner cavity width (~65mm)
- [ ] Back top ledge present (cw wide, ledge_h=2.5mm, ledge_d=3.5mm) for cover tongue

---

## PCB Boss Pins

- [ ] 4× bosses: at v=12mm (near top) and v=90mm (near bottom), u=±20.5mm
- [ ] Boss pad: Ø5.6mm × 3.5mm tall from inner face
- [ ] Boss pin: Ø2.6mm × 7.6mm from inner face (pcb_stack_z - wall)
- [ ] Uses `Solid.make_cylinder()` + `Rotation` (NOT BuildSketch+extrude — unreliable for angled cylinders)
- [ ] All 4 bosses appear as "fused ✓" in terminal

---

## Back Cover

- [ ] Panel: cw≈64.2mm wide × ch≈101.75mm tall, cover_t=2.5mm thick
- [ ] USB arch cutout at base (18mm wide, 9mm tall) with chamfer
- [ ] Two snap tabs with flex slots and bump latches (tab_len=8mm, bump_h=1.4mm)
- [ ] Vent holes: 5×3 grid, Ø2.2mm, 8mm spacing
- [ ] Fingernail notch at bottom centre
- [ ] Two wave ribs on outer face (matching front style)

---

## Build / Export

- [ ] Script runs without Python errors: `py -3.12 tidee.py`
- [ ] Terminal shows no unexpected "Failed:" lines (chamfer/fillet skip is acceptable)
- [ ] front_shell.stl exported
- [ ] back_cover.stl exported
- [ ] OCP CAD Viewer shows both parts side by side via `show()`

---

## Verification Steps After Every Build

1. **Terminal scan** — read all output, flag any unexpected "Failed:" messages
2. **Rib count** — should print exactly 15 ribs ✓
3. **Wordmark** — terminal says "Text rendered (style=FontStyle.BOLD) ✓" not "using slot"
4. **Oblique view** — orbit ~30° from front in OCP viewer to confirm ribs are proud beads, not flat
5. **Zebra tab** — switch to Zebra shading in OCP to confirm all surface features (ribs, wordmark) break the stripe pattern
6. **Boss count** — terminal shows 4 × "boss N fused ✓"

---

## Known Build123d Quirks (Don't Repeat These Mistakes)

| What breaks | Why | Correct approach |
|---|---|---|
| Ribs/wordmark Y position | `on_front_face()` returns raw polygon Y, ~3.3mm behind actual hull surface | Always use `_front_face_outer_y(wz)` for anything on the outer face |
| Text/geometry deboss going wrong direction | `extrude(face, amount=negative)` on tilted custom plane is unreliable outside BuildPart | Offset plane inward by depth, extrude OUTWARD (positive) |
| Boss pin cylinders | `Cylinder()` outside BuildPart can return ShapeList | Use `Solid.make_cylinder()` + `Rotation` + `Location` |
| Screen cut direction | `extrude()` on a rotated face sketch can go either direction | Use `Box` + `Rotation(-front_lean)` + `Location` |
| Fusing many shapes | Sequential `.fuse()` is O(n²) | Use `_binary_fuse(list)` helper |
| Fuse returns ShapeList | Non-touching solids produce Compound, not Solid | Use `_as_solid()` helper to normalise |
| Ribs must fuse to outer_solid | Fusing to hollow shell is unreliable in OCC | Always fuse ribs to outer_solid BEFORE `outer - inner` hollowing |

---

*Last updated: 2026-06-05*
