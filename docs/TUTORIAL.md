# From an empty file to a finished drawing

This walks through one part — a flanged bush — in six steps. Each step adds one layer and
ends with something you can look at. Total time: about ten minutes. You need Python 3.10+
and `pip install -r requirements.txt` (or `pip install technische-zeichnung`).

Work in a file `bush.py` next to the repository's `scripts/` folder, or anywhere after
installing the package.

## 1 Model the part

A drawing is derived from a 3D model, so the model comes first. Turned parts are easiest as
a half profile `(x, r)` revolved about the x axis. Every dimension is a named parameter —
those names are what you will dimension later.

```python
import sys
sys.path.insert(0, "scripts")            # not needed after pip install
from build123d import Axis, Polyline, make_face, revolve
import drawlib as D

D_FLANGE, D_SEAT, D_BORE = 32.0, 20.0, 10.0
LENGTH, W_FLANGE, CH = 25.0, 5.0, 0.5

def bush():
    ra, rb, ri, f = D_SEAT / 2, D_FLANGE / 2, D_BORE / 2, CH
    prof = [(0, ri + f), (0, rb - f), (f, rb), (W_FLANGE, rb), (W_FLANGE, ra),
            (LENGTH - f, ra), (LENGTH, ra - f), (LENGTH, ri + f), (LENGTH - f, ri), (f, ri)]
    return revolve(make_face(Polyline(*[(x, 0, r) for x, r in prof], close=True)), Axis.X, 360)
```

## 2 A sheet and one view

```python
S = D.Sheet("A4")                                   # frame, grid, centring marks
V = D.View(S, (72, 190), 2.0, *D.VIEWS["front"])    # model origin at sheet (72, 190), 2:1
part = bush()
V.section([(V.cut(part), 45, 2.5)])                 # cut at y = 0, hatch 45°, 2,5 mm
S.title_block(dict(title="Bundbuchse", number="BSP-001", material="11SMn30+C",
                   scale="2:1"))
S.save("bush.pdf", png="bush.png")
```

`D.VIEWS["front"]` is `(n, xdir)`: `n` points from the part to the viewer, `xdir` is the
model direction that goes to the right on the sheet. `V.cut()` removes the half between
you and the cutting plane. Open `bush.png`: the bush in full section and a title block.
The terminal shows `drawing check bush.pdf: 0 error(s), 0 warning(s)` — every save runs
the check, and from now on you will see when an annotation lands somewhere it should not.

From here on, every annotation is placed with `V.p(u, v)`, which turns model millimetres
in the view plane into sheet millimetres. Change the scale or the origin and everything
moves along.

## 3 Centre line and dimensions

```python
p = V.p
ra, rb, ri = D_SEAT / 2, D_FLANGE / 2, D_BORE / 2
S.centerline(p(-3, 0), p(LENGTH + 3, 0))
S.hdim(p(0, -rb), p(LENGTH, -ra), p(0, -rb)[1] - 16, "25")        # dimension line at y
S.hdim(p(0, rb), p(W_FLANGE, rb), p(0, rb)[1] + 8, "5")
S.vdim(p(LENGTH, -ri), p(LENGTH, ri), p(LENGTH + 5, 0)[0], "Ø10 H7")  # line at x
S.vdim(p(LENGTH, -ra), p(LENGTH, ra), p(LENGTH + 10, 0)[0], "Ø20 g6")
S.vdim(p(0, -rb), p(0, rb), p(-6, 0)[0], "Ø32")
```

Dimension from the functional face (here the flange face at x = 0), never twice, smaller
dimensions closer to the part. `H7` and `g6` are verified against ISO 286 by the check — a
typo like `H17` becomes an error.

## 4 Datum, geometrical tolerance, surface texture

```python
S.datum("A", p(LENGTH + 5, -ri), (0, -1), length=14)       # axis of the bore
bx = S.fcf(p(14, 0)[0] - D.H, p(0, rb)[1] + 16, "runout", "0,02", ["A"])
S.fcf_leader(bx, p(14, ra), "bottom")                       # square onto the surface
S.rough(p(20, ra), "Ra 0,8")
S.rough(p(9, -ri), "Ra 0,8")
S.general_surface(140, 61, "Ra 3,2")                        # all other surfaces
```

A datum on an axis sits in line with the dimension line of that diameter. The leader of a
tolerance frame meets the surface at a right angle. Remove the `S.datum` line and run
again: the check reports *a tolerance frame refers to datum A, which is not indicated*.

## 5 Notes, limits table, title block

```python
S.notes(25, 118, ["1  Bohrung A und Sitz Ø20 g6 in einer Aufspannung fertigen.",
                  "2  Nicht bemaßte Fasen 0,5 × 45°."])
S.fit_table(25, 100, ["Ø10 H7", "Ø20 g6"])
S.title_block(dict(title="Bundbuchse", number="BSP-001", material="11SMn30+C (1.0715)",
                   mass=f"{part.volume * 7.85 / 1000:.0f} g", scale="2:1"))
```

(Replace the title block call from step 2 with this one — a sheet has one title block.)

## 6 Save, read the check, look at the sheet

```python
S.save("bush.pdf", png="bush.png", dxf="bush.dxf")    # dxf needs: pip install ezdxf
```

Read the check report, open `bush_check.png` if there is one, and look at `bush.png`
yourself — the check catches collisions and inconsistencies, not a badly chosen
dimension. Then:

- English drawing: `D.Sheet("A4", lang="en")`. Third-angle: `projection="third"`.
- Your company title block: `S.title_block(values, layout="my_block.json", logo="logo.png")`,
  see `examples/data/title_block_company.json`.
- More views, sections, details, threads, welds, gears: the scripts in `examples/`.
- Every call and its options: `references/drawlib_api.md`.

## Without writing code

If the part already exists as a STEP file:

```bash
step2drawing bush.step --section --material "11SMn30+C" --density 7.85
```

gives views, centre lines, overall dimensions and the title block; you add the rest.
