"""Part drawing: stepped shaft (A3, 2:1) - the elements a long turned part needs.

Broken (interrupted) view so a 175 mm shaft fits at 2:1, external thread to ISO 6410,
detail view Z at 5:1 of a retaining-ring groove and a shoulder fillet, removed section B-B
through the keyway, bearing seats with ISO 286 fits and a limits table.

Run:  python examples/stepped_shaft.py [output folder]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build123d import Axis, Box, Cylinder, Polyline, Pos, make_face, revolve  # noqa: E402

import drawlib as D  # noqa: E402

# --- part parameters (x along the axis, all mm) ---------------------------------------
L_THREAD, D_THREAD, D_CORE = 20.0, 16.0, 13.546          # M16, core Ø d3 = 13,546
X_SEAT1, D_SEAT = 60.0, 25.0                              # bearing seat Ø25 k6, x 20..60
X_MID, D_MID = 140.0, 32.0                                # collar Ø32, x 60..140
LENGTH, D_END = 175.0, 20.0                               # coupling end Ø20 h6, x 140..175
GROOVE_X, GROOVE_W, GROOVE_D = 54.0, 1.3, 23.9            # retaining ring DIN 471 - 25×1,2
KEY_X0, KEY_L, KEY_W, KEY_T1 = 144.0, 28.0, 6.0, 3.5      # feather key DIN 6885 A 6×6×28
FILLET, CH = 1.0, 1.0
RHO = 7.85


def shaft():
    r1, r2, r3, r4, g = D_THREAD / 2, D_SEAT / 2, D_MID / 2, D_END / 2, GROOVE_D / 2
    prof = [(0, 0), (0, r1 - 1.5), (1.5, r1), (L_THREAD, r1), (L_THREAD, r2 - CH),
            (L_THREAD + CH, r2), (GROOVE_X, r2), (GROOVE_X, g), (GROOVE_X + GROOVE_W, g),
            (GROOVE_X + GROOVE_W, r2), (X_SEAT1, r2), (X_SEAT1, r3 - CH), (X_SEAT1 + CH, r3),
            (X_MID - CH, r3), (X_MID, r3 - CH), (X_MID, r4), (LENGTH - CH, r4),
            (LENGTH, r4 - CH), (LENGTH, 0)]
    s = revolve(make_face(Polyline(*[(x, 0, r) for x, r in prof], close=True)), Axis.X, 360)
    shoulder = [e for e in s.edges() if e.geom_type.name == "CIRCLE"
                and abs(e.center().X - X_SEAT1) < 1e-6 and abs(e.radius - r2) < 1e-6]
    s = s.fillet(FILLET, shoulder)
    # keyway, milled with an end mill: rounded ends
    xm = KEY_X0 + KEY_L / 2
    z = r4 - KEY_T1
    slot = Pos(xm, 0, z + 5) * Box(KEY_L - KEY_W, KEY_W, 10)
    for sx in (-1, 1):
        slot += Pos(xm + sx * (KEY_L - KEY_W) / 2, 0, z + 5) * Cylinder(KEY_W / 2, 10)
    return s - slot


def sheet():
    S = D.Sheet("A3")
    part = shaft()
    n, x = D.VIEWS["front"]
    # 175 mm at 2:1 is too long for the view space: leave out x = 75..125
    bv = D.BrokenView(S, (60.0, 200.0), 2.0, n, x, breaks=[(75.0, 125.0)], gap=8.0)
    bv.draw([part])
    p = bv.p
    r2, r3, r4 = D_SEAT / 2, D_MID / 2, D_END / 2
    S.centerline(p(-4, 0), p(LENGTH + 4, 0))
    left = bv.views[0]
    left.thread((0, 0), (L_THREAD - 4, 0), D_THREAD, D_CORE)      # usable thread length 16

    # lengths from the shoulder at x = 60 (bearing seat stop) and overall length
    S.hdim(p(0, -D_THREAD / 2), p(LENGTH, -r4), 150.0, "175")
    S.hdim(p(0, -D_THREAD / 2), p(L_THREAD - 4, -D_THREAD / 2), 172.0, "16")
    S.hdim(p(L_THREAD, -r2), p(X_SEAT1, -r2), 162.0, "40")
    S.hdim(p(X_MID, -r4), p(LENGTH, -r4), 162.0, "35")
    S.hdim(p(KEY_X0, r4), p(KEY_X0 + KEY_L, r4), 236.0, "28")
    S.hdim(p(X_MID, r3), p(KEY_X0, r4), 246.0, "4")
    # diameters: dimension line across the cylinder, value in the upper half
    # (the Ø20 value goes into the lower half: the keyway floor runs through the upper one)
    for u, dia, txt, side in ((8, D_THREAD, "M16", 1), (38, D_SEAT, "Ø25 k6", 1),
                              (68, D_MID, "Ø32", 1), (152, D_END, "Ø20 h6", -1)):
        S.vdim(p(u, -dia / 2), p(u, dia / 2), p(u, 0)[0], txt, ext1=False, ext2=False,
               tshift=side * dia / 2)
    S.leader_text(p(GROOVE_X + GROOVE_W / 2, GROOVE_D / 2), (150.0, 248.0), "Ø23.9 h11")
    S.rough(p(30, r2), "Ra 0.8")
    S.rough_leader(p(173, r4), (p(173, 0)[0] + 8, p(0, r4)[1] + 8), "Ra 0.8")

    # detail Z: groove and shoulder fillet at 5:1
    dv = left.detail((56.0, r2 + 1.5), 6.5, (125.0, 105.0), 5.0, "Z")
    dv.draw([part])
    q = dv.p
    # short dimension: arrows outside, value beside them
    S.hdim(q(GROOVE_X, r2), q(GROOVE_X + GROOVE_W, r2), q(0, r2)[1] + 18.0, "1.3 H13",
           outside=True, tshift=17.25)
    S.rdim(q(X_SEAT1 - FILLET, r2 + FILLET), FILLET * 5.0, -45, "R1", concave=True)

    # removed section B-B through the keyway, seen from the left
    xb = KEY_X0 + KEY_L / 2
    nB, xB = D.VIEWS["left"]
    cB = (p(xb, 0)[0], 105.0)
    B = D.View(S, cB, 2.0, nB, xB)
    B.removed_section(part, d=-xb, angle=45, spacing=2.5)
    S.centre_cross(cB, r4 * 2.0)
    S.view_label(cB[0], cB[1] + r4 * 2 + 9, "B-B")
    S.cutting_plane((p(xb, 0)[0], p(0, r4)[1] + 12), (p(xb, 0)[0], p(0, -r4)[1] - 12), "B", (1, 0))
    S.hdim(B.p(-KEY_W / 2, r4), B.p(KEY_W / 2, r4), cB[1] + r4 * 2 + 3.0, "6 P9", outside=True)
    S.vdim(B.p(0, -r4), B.p(0, r4 - KEY_T1), cB[0] + r4 * 2 + 9, "16.5", tol=("0", "-0.1"))

    S.fit_table(25.0, 62.0, ["Ø25 k6", "Ø20 h6", "6 P9", "1.3 H13", "Ø23.9 h11"])
    S.notes(25.0, 282.0, ["1  Zentrierbohrungen ISO 6411-A2,5/5,3 an beiden Enden zulässig.",
                          "2  Lagersitze Ø25 k6 und Ø20 h6 geschliffen.",
                          "3  Nicht bemaßte Fasen 1 × 45°."])
    S.general_surface(330.0, 61.0, "Ra 3.2")
    S.title_block(dict(title="Welle", subtitle="Beispielteil der Zeichnungsbibliothek",
                       number="BSP-200", material="C45E (1.1191)",
                       mass=f"{part.volume * RHO / 1000:.0f} g", scale="2:1 (5:1)",
                       project="Beispiel"))
    return S


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "output"
    sheet().save(out / "BSP-200.pdf", png=out / "BSP-200.png")
