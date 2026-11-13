"""Assembly drawing: bearing bracket (A3, 2:1, section A-A plus plan view).

Shows what a single-part drawing cannot: two views that line up, a cutting-plane indication,
a section in which the shaft is deliberately NOT cut (ISO 128-44), different hatch angles for
neighbouring parts, fits written as pairs (H7/s6) with an ISO 286 fit table, item numbers,
a parts list and an interference check before drawing.

The assembly is the flanged bush of example 1 pressed into a bracket, carrying a shaft.

Run:  python examples/bearing_bracket.py [output folder]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build123d import Cylinder, Polyline, Pos, Rot, extrude, make_face  # noqa: E402

import drawlib as D  # noqa: E402
from flanged_bush import bush  # noqa: E402

# --- assembly parameters --------------------------------------------------------------
PLATE_L, PLATE_W, PLATE_T = 70.0, 40.0, 8.0     # base plate: length, width, thickness
WALL_T, WALL_H = 20.0, 52.0                     # upright wall: thickness (x), height (z)
AXIS_Z = 34.0                                   # height of the bearing axis above the base
D_SEAT, D_SHAFT = 20.0, 10.0                    # bush seat in the wall, shaft in the bush
HOLE_X, HOLE_Y, D_HOLE = 26.0, 12.0, 5.5        # 4 mounting holes, Ø5,5 for M5, clear of the shaft
SHAFT_L = 50.0
RHO_AL, RHO_STEEL = 2.70, 7.85
BUSH_X = -15.0                                  # x of the bush flange face (flange is 5 long)


def bracket():
    """L-shaped bracket, extruded from one profile in the x-z plane so no fused seams appear."""
    a, b, w = PLATE_L / 2, WALL_T / 2, PLATE_W / 2
    prof = [(-a, 0, 0), (a, 0, 0), (a, 0, PLATE_T), (b, 0, PLATE_T), (b, 0, WALL_H),
            (-b, 0, WALL_H), (-b, 0, PLATE_T), (-a, 0, PLATE_T)]
    body = extrude(make_face(Polyline(*prof, close=True)), amount=w, both=True)
    body -= Pos(0, 0, AXIS_Z) * Rot(0, 90, 0) * Cylinder(D_SEAT / 2, 2 * PLATE_L)
    for sx in (-1, 1):
        for sy in (-1, 1):
            body -= Pos(sx * HOLE_X, sy * HOLE_Y, 0) * Cylinder(D_HOLE / 2, 4 * PLATE_T)
    return body


def shaft():
    return Pos(0, 0, AXIS_Z) * Rot(0, 90, 0) * Cylinder(D_SHAFT / 2, SHAFT_L)


def parts():
    return bracket(), Pos(BUSH_X, 0, AXIS_Z) * bush(), shaft()


def check_fit(p1, p2, p3):
    """Workflow step 3: every overlap must be zero or a deliberate press fit."""
    named = (("bracket", p1), ("bush", p2), ("shaft", p3))
    for i, (na, a) in enumerate(named):
        for nb, b in named[i + 1:]:
            print(f"   {na:<8}& {nb:<8}{(a & b).volume:9.3f} mm3")


def sheet():
    S = D.Sheet("A3")
    bra, bus, sha = parts()

    # --- section A-A: front view, viewer at -y, cutting plane y = 0 --------------------
    V = D.View(S, (140.0, 165.0), 2.0, *D.VIEWS["front"])
    p = V.p
    V.section([(V.cut(bra), 45, 2.5), (V.cut(bus), 135, 2.0)], background=[sha])
    S.view_label(140.0, 280.0, "A-A")
    S.centerline(p(-PLATE_L / 2 - 5, AXIS_Z), p(PLATE_L / 2 + 5, AXIS_Z))

    # only functional and mounting dimensions belong on an assembly drawing
    S.vdim(p(-PLATE_L / 2, 0), p(-PLATE_L / 2, AXIS_Z), 52.0, "34")
    S.leader_text(p(5, AXIS_Z + D_SEAT / 2), (230.0, 268.0), "Ø20 H7/s6")
    S.leader_text(p(12, AXIS_Z + D_SHAFT / 2), (230.0, 252.0), "Ø10 H7/h6")
    S.fit_pair_table(262.0, 214.0, ["Ø20 H7/s6", "Ø10 H7/h6"])

    # item numbers, all on one row
    S.posnum(p(-2.5, WALL_H - 4), (130.0, 270.0), 1)
    S.posnum(p(-12.5, AXIS_Z + 14), (108.0, 270.0), 2)
    S.posnum(p(22, AXIS_Z), (184.0, 270.0), 3)

    # --- plan view, 90 mm below: same x positions, so the views line up ----------------
    T = D.View(S, (140.0, 75.0), 2.0, *D.VIEWS["top"])
    q = T.p
    T.draw([bra, bus, sha])
    for sx in (-1, 1):
        for sy in (-1, 1):
            S.centre_cross(q(sx * HOLE_X, sy * HOLE_Y), D_HOLE + 2.0)
    # the cutting plane runs through the axis, so it doubles as the centre line of the view
    S.cutting_plane(q(-PLATE_L / 2 - 6, 0), q(PLATE_L / 2 + 6, 0), "A", (0, 1))
    S.hdim(q(-HOLE_X, HOLE_Y), q(HOLE_X, HOLE_Y), 28.0, "52")
    S.hdim(q(-PLATE_L / 2, -PLATE_W / 2), q(PLATE_L / 2, -PLATE_W / 2), 18.0, f"({PLATE_L:.0f})")
    S.vdim(q(-HOLE_X, -HOLE_Y), q(-HOLE_X, HOLE_Y), 48.0, "24")
    S.vdim(q(-PLATE_L / 2, -PLATE_W / 2), q(-PLATE_L / 2, PLATE_W / 2), 36.0, "40")
    S.leader_text(q(HOLE_X + D_HOLE / 2 * 0.7, HOLE_Y + D_HOLE / 2 * 0.7), (228.0, 120.0),
                  "4× Ø5,5", under="für ISO 4762 M5")

    S.notes(25.0, 155.0, [
        "1  Buchse Pos. 2 in Pos. 1 einpressen, Bund plan anliegend.",
        "2  Welle Pos. 3 nach dem Einpressen auf Leichtgängigkeit prüfen,",
        "    Lagerstelle vor der Montage ölen.",
        "3  Nicht bemaßte Maße siehe Einzelteilzeichnungen.",
    ])
    S.bom([("1", "1", "Lagerbock", "BSP-100-01", "EN AW-6082 T651"),
           ("2", "1", "Bundbuchse", "BSP-001", "11SMn30+C (1.0715)"),
           ("3", "1", "Welle Ø10 h6 × 50", "BSP-100-03", "C45E")])

    mass = (bra.volume * RHO_AL + (bus.volume + sha.volume) * RHO_STEEL) / 1000.0
    S.title_block(dict(title="Lagerbock", subtitle="Baugruppe, Beispiel der Zeichnungsbibliothek",
                       number="BSP-100", material="siehe Stückliste", mass=f"{mass:.0f} g",
                       scale="2:1", doctype="Zusammenbauzeichnung", project="Beispiel"))
    return S


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "output"
    print("interference check:")
    check_fit(*parts())
    sheet().save(out / "BSP-100.pdf", png=out / "BSP-100.png")
