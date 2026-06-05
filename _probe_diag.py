"""
Probe the side_prism and outer solid with a THIN slab and also a Y-axis needle
to distinguish:
  (a) the vertical FRONT FACE (faces toward viewer, normal ~= -Y)
  (b) the bottom-corner CURVE (faces downward, normal ~= -Z) which is more
      forward in Y but NOT the surface we want to put ribs on.
"""
import sys, types, math

ocp_stub = types.ModuleType("ocp_vscode")
ocp_stub.show = lambda *a, **kw: None
sys.modules["ocp_vscode"] = ocp_stub

with open("tidee.py", encoding="utf-8") as fh:
    src = fh.read()
if '__name__ == "__main__"' in src:
    src = src[:src.index('if __name__ == "__main__"')]
exec(compile(src, "tidee.py", "exec"), globals())

from build123d import Box, Align, Location, Vector

outer = make_outer_solid()

print("Probe A: thin Z-slab (0.1 mm) -- front face only, no bottom-curve bleed-in")
print(f"  {'z':>6}  {'thin-slab minY':>15}  {'formula':>9}")
for pz in [6.0, 8.0, 10.0, 15.0, 20.0, 30.0, 60.0, 90.0, 118.0]:
    formula_y = _front_face_outer_y(pz)
    try:
        slab = Box(2.0, 200.0, 0.1, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        slab = slab.moved(Location(Vector(0.0, 0.0, pz)))
        y_thin = outer.intersect(slab).bounding_box().min.Y
    except Exception as ex:
        y_thin = f"ERR({ex})"
    print(f"  z={pz:5.1f}  thin={y_thin if isinstance(y_thin,str) else f'{y_thin:+8.3f}'}  formula={formula_y:+8.3f}")

print()
print("Probe B: Y-axis needle (X=0, front-half only Y=-50..0) at multiple Z")
print("  This gives front-face Y of the visible front surface only")
print(f"  {'z':>6}  {'needle minY':>12}  {'formula':>9}")
for pz in [6.0, 8.0, 10.0, 15.0, 20.0, 30.0, 60.0, 90.0, 118.0]:
    formula_y = _front_face_outer_y(pz)
    try:
        # Needle: 2mm wide in X, front half only (Y = -50 to 0), very thin in Z
        needle = Box(2.0, 50.0, 0.5, align=(Align.CENTER, Align.MIN, Align.CENTER))
        needle = needle.moved(Location(Vector(0.0, -50.0, pz)))
        result = outer.intersect(needle)
        y_needle = result.bounding_box().min.Y
    except Exception as ex:
        y_needle = f"ERR({ex})"
    print(f"  z={pz:5.1f}  needle={y_needle if isinstance(y_needle,str) else f'{y_needle:+8.3f}'}  formula={formula_y:+8.3f}")

print()
print("Probe C: sweep Z from 0..30 with thin slab (0.1mm) to trace bottom corner")
print(f"  {'z':>5}  {'min_Y':>8}")
for pz in [1,2,3,4,5,6,7,8,9,10,12,15,18,21,25,30]:
    try:
        slab = Box(2.0, 200.0, 0.1, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        slab = slab.moved(Location(Vector(0.0, 0.0, float(pz))))
        y = outer.intersect(slab).bounding_box().min.Y
    except:
        y = float("nan")
    print(f"  z={pz:4d}  {y:+8.3f}")
