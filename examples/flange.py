"""Part drawing: flange (A3, 1:1) - half section and a hole pattern on a pitch circle.

Half section of a rotationally symmetric part (ISO 128-44) with a half dimension for the
bore, end view with six holes on a pitch circle (theoretically exact Ø80, position
tolerance to datums A and B), spigot Ø60 h7 as datum B, flatness of the mounting face A,
surface texture on an extension line.

Run:  python examples/flange.py [output folder]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build123d import Axis, Cylinder, Polyline, Pos, Rot, make_face, revolve  # noqa: E402

import drawlib as D  # noqa: E402

D_OUT, T_FLANGE = 100.0, 14.0          # flange Ø and thickness, x = 0..14
D_SPIGOT, H_SPIGOT = 60.0, 4.0         # spigot Ø60 h7, x = -4..0
D_BORE = 40.0                          # bore Ø40 H7
D_PCD, D_HOLE, N_HOLES = 80.0, 9.0, 6  # 6 × Ø9 on Ø80 (for M8)
HOLE_ANGLES = [90 + 360 / N_HOLES * i for i in range(N_HOLES)]   # one hole in the cutting plane
CH = 1.0
RHO = 7.2                              # cast iron EN-GJL-250


def flange():
    rs, ro, rb = D_SPIGOT / 2, D_OUT / 2, D_BORE / 2
    prof = [(-H_SPIGOT, rb + CH), (-H_SPIGOT, rs - 0.5), (-H_SPIGOT + 0.5, rs), (0, rs), (0, ro - CH),
            (CH, ro), (T_FLANGE, ro), (T_FLANGE, rb + CH), (T_FLANGE - CH, rb), (-H_SPIGOT + CH, rb)]
    body = revolve(make_face(Polyline(*[(x, 0, r) for x, r in prof], close=True)), Axis.X, 360)
    for a in HOLE_ANGLES:
        # the end view (from the left) shows u = -y, v = z: place the holes at those view angles
        u, v = D_PCD / 2 * math.cos(math.radians(a)), D_PCD / 2 * math.sin(math.radians(a))
        body -= Pos(T_FLANGE / 2, -u, v) * Rot(0, 90, 0) * Cylinder(D_HOLE / 2, 3 * T_FLANGE)
    return body


def sheet():
    S = D.Sheet("A3")
    part = flange()
    ro, rs, rb = D_OUT / 2, D_SPIGOT / 2, D_BORE / 2

    # --- front view as half section: upper half cut in the plane y = 0 ---------------------
    V = D.View(S, (90.0, 175.0), 1.0, *D.VIEWS["front"])
    p = V.p
    V.half_section([(part, 45, 2.0)], side="upper")
    S.centerline(p(-H_SPIGOT - 6, 0), p(T_FLANGE + 6, 0))
    S.centerline(p(T_FLANGE / 2, D_PCD / 2 - 7), p(T_FLANGE / 2, D_PCD / 2 + 7))   # hole axis

    # diameters on the left, nested: the smaller one closer to the part
    S.vdim(p(-H_SPIGOT, -rs), p(-H_SPIGOT, rs), 74.0, "Ø60 h7")
    S.vdim(p(CH, -ro), p(CH, ro), 62.0, "Ø100")
    S.datum("B", (74.0, p(0, rs)[1]), (0, 1), length=20.0)            # axis of the spigot
    # bore: half dimension, surface texture standing on its extension line
    S.vdim(p(T_FLANGE, -rb), p(T_FLANGE, rb), 114.0, "Ø40 H7", half=True)
    S.rough((108.0, p(0, rb)[1]), "Ra 1.6")
    S.hdim(p(0, ro), p(T_FLANGE, ro), p(0, ro)[1] + 8, "14")
    S.hdim(p(-H_SPIGOT, rs), p(0, rs), p(0, ro)[1] + 16, "4", outside=True)
    # datum A = mounting face x = 0, flatness on the same extension line
    S.seg(p(0, -ro), p(0, -ro - 11), "thin")
    S.datum("A", p(0, -ro - 3), (0, -1), length=8.0)
    bf = S.fcf(55.0, p(0, -ro)[1] - 12.5, "flatness", "0.05")
    S.fcf_leader(bf, p(0, -ro - 9), "right")

    # --- end view from the left; first-angle method: right of the front view -------------
    E = D.View(S, (240.0, 175.0), 1.0, *D.VIEWS["left"])
    E.draw([part])
    c = E.p(0, 0)
    S.centre_cross(c, ro)
    S.pitch_circle(c, D_PCD / 2, HOLE_ANGLES)
    # pitch circle between two holes, its value outside the flange (Ø100 = 1,25 × Ø80)
    S.ddim(c, D_PCD / 2, 120, "Ø80", box=True, tpos=1.45)
    a = math.radians(30)
    hole = E.p(D_PCD / 2 * math.cos(a), D_PCD / 2 * math.sin(a))
    knee = (300.0, 245.0)
    S.leader_text(hole + D._rot((1, 0), 45) * (D_HOLE / 2), knee, "6× Ø9")
    S.fcf(knee[0], knee[1] - 2 * D.H, "position", "Ø0.2", ["A", "B"])   # hangs under the callout

    S.notes(25.0, 95.0, ["1  Nicht bemaßte Fasen 1 × 45°.",
                         "2  Unbearbeitete Gussflächen ISO 8062-3 DCTG 9."])
    S.fit_table(25.0, 76.0, ["Ø60 h7", "Ø40 H7"])
    S.general_surface(330.0, 61.0, "Ra 6.3")
    S.title_block(dict(title="Flansch", subtitle="Beispielteil der Zeichnungsbibliothek",
                       number="BSP-400", material="EN-GJL-250 (EN-JL1040)",
                       mass=f"{part.volume * RHO / 1000:.0f} g", scale="1:1", project="Beispiel"))
    return S


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "output"
    sheet().save(out / "BSP-400.pdf", png=out / "BSP-400.png")
