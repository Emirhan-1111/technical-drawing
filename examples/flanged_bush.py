"""Part drawing: flanged bush (A4, 2:1) - the template to copy for a single part.

Shows the whole route: model the part -> derive a section from the model -> centre lines,
dimensions, datum, geometrical tolerance, surface texture, notes, ISO 286 limits table,
title block -> vector PDF plus a PNG preview, with the automatic sheet check.

Run:  python examples/flanged_bush.py [output folder] [--lang en]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build123d import Axis, Polyline, make_face, revolve  # noqa: E402

import drawlib as D  # noqa: E402

# --- part parameters (the single source of every dimension) ---------------------------
D_FLANGE, D_SHAFT, D_BORE = 32.0, 20.0, 10.0    # flange, seat Ø20 g6, bore Ø10 H7
LENGTH, W_FLANGE, CHAMFER = 25.0, 5.0, 0.5
RHO = 7.85                                      # g/cm³, steel


def bush():
    """Turned part, revolved about the x axis from the half profile (x, r)."""
    ra, rb, ri, f = D_SHAFT / 2, D_FLANGE / 2, D_BORE / 2, CHAMFER
    prof = [(0, ri + f), (0, rb - f), (f, rb), (W_FLANGE, rb), (W_FLANGE, ra), (LENGTH - f, ra),
            (LENGTH, ra - f), (LENGTH, ri + f), (LENGTH - f, ri), (f, ri)]
    return revolve(make_face(Polyline(*[(x, 0, r) for x, r in prof], close=True)), Axis.X, 360)


TXT = {
    "de": dict(notes=["1  Bohrung A und Sitz Ø20 g6 in einer Aufspannung fertigen.",
                      "2  Anlagefläche des Bunds (Ra 1,6) plan zu A, gratfrei.",
                      "3  Nicht bemaßte Fasen 0,5 × 45°."],
               title="Bundbuchse", subtitle="Beispielteil der Zeichnungsbibliothek",
               project="Beispiel"),
    "en": dict(notes=["1  Machine bore A and seat Ø20 g6 in one setting.",
                      "2  Flange face (Ra 1.6) flat to A, free of burrs.",
                      "3  Chamfers not dimensioned 0.5 × 45°."],
               title="Flanged bush", subtitle="Example part of the drawing library",
               project="Example"),
}


def sheet(lang="de"):
    t = TXT[lang]
    S = D.Sheet("A4", lang=lang)
    V = D.View(S, (72.0, 190.0), 2.0, *D.VIEWS["front"])    # origin, scale 2:1, looking along +y
    p = V.p                                           # (x, r) in model mm -> sheet coordinates
    part = bush()
    V.section([(V.cut(part), 45, 2.5)])               # solid, hatch angle, hatch spacing
    ra, rb, ri = D_SHAFT / 2, D_FLANGE / 2, D_BORE / 2

    S.centerline(p(-3, 0), p(LENGTH + 3, 0))
    # lengths are dimensioned from the seating face of the flange (the functional datum)
    S.hdim(p(0, -rb), p(LENGTH, -ra), p(0, -rb)[1] - 16.0, "25")
    S.hdim(p(0, rb), p(W_FLANGE, rb), p(0, rb)[1] + 8.0, "5")
    # diameters: the fits on the right, the flange on the left
    S.vdim(p(LENGTH, -ri), p(LENGTH, ri), p(LENGTH + 5, 0)[0], "Ø10 H7")
    S.vdim(p(LENGTH, -ra), p(LENGTH, ra), p(LENGTH + 10, 0)[0], "Ø20 g6")
    S.vdim(p(0, -rb), p(0, rb), p(-6, 0)[0], "Ø32")
    # datum A = axis of the bore; the datum triangle extends the Ø10 H7 dimension line
    S.datum("A", p(LENGTH + 5, -ri), (0, -1), length=14.0)
    # circular run-out of the Ø20 g6 seat to A, leader perpendicular to the cylindrical face
    bx = S.fcf(p(14, 0)[0] - D.H, p(0, rb)[1] + 16.0, "runout", "0.02", ["A"])
    S.fcf_leader(bx, p(14, ra), "bottom")
    # surface texture: the symbol sits on the surface, pointing at the material from outside
    S.rough(p(20, ra), "Ra 0.8")
    S.rough(p(9, -ri), "Ra 0.8")
    S.rough_leader(p(W_FLANGE, -13.0), (p(W_FLANGE, 0)[0] + 8.0, p(0, -13.0)[1] - 12.0), "Ra 1.6")

    S.notes(25.0, 118.0, t["notes"])
    S.fit_table(25.0, 96.0, ["Ø10 H7", "Ø20 g6"])     # limits straight from ISO 286
    S.general_surface(140.0, 61.0, "Ra 3.2")          # general note: all remaining surfaces
    mass = part.volume * RHO / 1000.0
    S.title_block(dict(title=t["title"], subtitle=t["subtitle"], number="BSP-001",
                       material="11SMn30+C (1.0715)", mass=f"{mass:.0f} g", scale="2:1",
                       project=t["project"]))
    return S


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=Path(__file__).parent / "output", type=Path)
    ap.add_argument("--lang", default="de", choices=sorted(D.TEXTS))
    a = ap.parse_args()
    name = "BSP-001" + ("" if a.lang == "de" else f"-{a.lang}")
    sheet(a.lang).save(a.out / f"{name}.pdf", png=a.out / f"{name}.png")
