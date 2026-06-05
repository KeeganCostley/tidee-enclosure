# Tidee Enclosure

3D-printable enclosure for the **LCDwiki ES3C28P** (2.8″ CYD ESP32-S3 dev board), designed in Python with [build123d](https://github.com/gumyr/build123d).

![Front face render](https://raw.githubusercontent.com/KeeganCostley/tidee-enclosure/master/docs/preview.png)

---

## Hardware

| Part | Spec |
|------|------|
| Board | LCDwiki ES3C28P (ESP32-S3, 2.8″ ILI9341 TFT) |
| Screen | 2.8″ 320×240, glass-to-PCB stack ≈ 8 mm |
| PCB | 50 × 86 mm |
| USB | USB-C, bottom edge |

---

## Design

Trapezoidal shell (88 mm wide front, 68 mm back, 50 mm deep, 124 mm tall) with:

- **Wave ribs** — sinusoidal wrapping ribs with geometric Z-spacing: dense near the base, spacing grows 15 % per step toward the top.  Ribs below the screen wrap the full front face; ribs in the screen zone become side-strips flanking the display; full-width ribs reappear above the screen.
- **Wordmark deboss** — "tidee" text pressed 1.5 mm into the front face below the screen.
- **Screen window** — tight bezel cutout for the display glass.
- **PCB bosses** — 4 × M2.6 boss pins, 5.6 mm pads.
- **USB slot** — clearance cutout at the base for USB-C housing.
- **Snap-fit back cover** — separate piece with ledge clip and two decorative cover ribs.

### Geometry construction

```
outer_solid = hull_of_4_circles(XY) extruded tall
              INTERSECT hull_of_4_circles(YZ) extruded wide
inner_solid = same with wall = 3 mm inset
shell       = outer_solid − inner_solid  (then features added/subtracted)
wave_rib    = box array placed proud of front face, fused to shell
```

---

## Files

| File | Purpose |
|------|---------|
| `tidee.py` | Main build script — run this to generate the model |
| `_probe_diag.py` | Geometry diagnostic: probes front-face Y at various heights to verify rib placement |
| `TIDEE_DESIGN_CHECKLIST.md` | Outstanding tasks and design decisions |
| `tideee_handoff.md` | Session handoff notes |
| `tideee OG.scad` … `tideee (6).scad` | Legacy OpenSCAD iterations (reference only) |

---

## Requirements

```
python >= 3.12
build123d
ocp_vscode        # for live preview in VS Code / OCP CAD Viewer
```

Install:
```bash
pip install build123d ocp-vscode
```

---

## Usage

```bash
py -3.12 tidee.py
```

Opens the front shell and back cover in OCP CAD Viewer.  
STL export is handled separately (see `make_front_shell()` / `make_back_cover()`).

### Tunable parameters (top of `tidee.py`)

```python
# Enclosure dimensions
W_front    = 88.0   # front face width (mm)
W_back     = 68.0   # back face width
D          = 50.0   # depth
H_front    = 124.0  # front face height
front_lean = 9.0    # degrees – front face leans back
wall       = 3.0    # shell wall thickness

# Wave ribs
ridge_dia       = 2.2    # rib bead diameter
gap_base        = 3.0    # gap between first two ribs (mm)
gap_ratio       = 1.15   # geometric growth per rib (15 % wider each step)
wave_amp_bot    = 0.8    # wave amplitude at base (mm)
wave_amp_top    = 2.4    # wave amplitude at top
wave_wavelen    = 70.0   # wavelength (mm)

# Wordmark
wordmark_text               = "tidee"
wordmark_size               = 11.0   # font size (mm)
wordmark_depth              = 1.5    # deboss depth
wordmark_offset_from_bottom = 32.0   # mm from bottom along face
```

---

## License

MIT
