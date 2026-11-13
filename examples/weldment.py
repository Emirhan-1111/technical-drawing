"""Weldment drawing: welded bracket (A3, 1:1) - weld symbols to ISO 2553.

Three plates welded together: double fillet welds a5 between upright and base plate, fillet
welds a4 on both sides of the rib, welding process 135 in the tail, item numbers, parts list,
general tolerances for welded constructions ISO 13920.

Run:  python examples/weldment.py [output folder]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build123d import Box, Cylinder, Polyline, Pos, Rot, extrude, make_face  # noqa: E402

import drawlib as D  # noqa: E402

BASE_L, BASE_W, BASE_T = 160.0, 100.0, 12.0
UP_T, UP_H = 12.0, 100.0                      # upright plate, x = -6..6, z = 12..112
RIB_T, RIB_L = 10.0, 60.0                     # triangular rib on the +x side
HOLE_X, HOLE_Y, D_HOLE = 60.0, 35.0, 11.0     # 4 × Ø11 for M10
D_BORE, BORE_Z = 20.0, 80.0
RHO = 7.85


def plates():
    base = Pos(0, 0, BASE_T / 2) * Box(BASE_L, BASE_W, BASE_T)
    for sx in (-1, 1):
        for sy in (-1, 1):
            base -= Pos(sx * HOLE_X, sy * HOLE_Y, 0) * Cylinder(D_HOLE / 2, 4 * BASE_T)
    up = Pos(0, 0, BASE_T + UP_H / 2) * Box(UP_T, BASE_W, UP_H)
    up -= Pos(0, 0, BASE_T + BORE_Z) * Rot(0, 90, 0) * Cylinder(D_BORE / 2, 3 * UP_T)
    tri = [(UP_T / 2, 0, BASE_T), (UP_T / 2 + RIB_L, 0, BASE_T), (UP_T / 2, 0, BASE_T + RIB_L)]
    rib = extrude(make_face(Polyline(*tri, close=True)), amount=RIB_T / 2, both=True)
    return base, up, rib


def sheet():
    S = D.Sheet("A3")
    base, up, rib = plates()
    parts = [base, up, rib]

    F = D.View(S, (120.0, 160.0), 1.0, *D.VIEWS["front"])
    F.draw(parts, hidden=True)
    p = F.p
    T = D.View(S, (120.0, 82.0), 1.0, *D.VIEWS["top"])
    T.draw(parts)
    q = T.p
    L = D.View(S, (300.0, 160.0), 1.0, *D.VIEWS["left"])
    L.draw(parts)
    r = L.p
    for sx in (-1, 1):
        for sy in (-1, 1):
            S.centre_cross(q(sx * HOLE_X, sy * HOLE_Y), D_HOLE / 2)
    S.centre_cross(r(0, BASE_T + BORE_Z), D_BORE / 2)
    S.centerline(p(-UP_T / 2 - 3, BASE_T + BORE_Z), p(UP_T / 2 + 3, BASE_T + BORE_Z))

    # welds: upright to base on both sides, rib to base and to upright on both sides
    S.weld(p(-UP_T / 2, BASE_T), (90.0, 215.0), "fillet", size="a5", side="both", process="135")
    S.weld(p(UP_T / 2, BASE_T + RIB_L), (150.0, 248.0), "fillet", size="a4", length="",
           side="both")
    S.weld(p(UP_T / 2 + RIB_L, BASE_T), (205.0, 200.0), "fillet", size="a4", side="both")

    # dimensions: overall, hole pattern, bore position
    S.vdim(p(-BASE_L / 2, 0), p(-BASE_L / 2, BASE_T), 30.0, "12")
    S.vdim(p(-UP_T / 2, 0), p(-UP_T / 2, BASE_T + UP_H), 44.0, "112")
    S.vdim(r(-BASE_W / 2, 0), r(-BASE_W / 2, BASE_T + BORE_Z), r(-BASE_W / 2, 0)[0] - 10, "92")
    S.leader_text(r(0, BASE_T + BORE_Z) + D._rot((1, 0), 45) * D_BORE / 2, (345.0, 278.0), "Ø20")
    S.hdim(q(-BASE_L / 2, -BASE_W / 2), q(BASE_L / 2, -BASE_W / 2), 14.0, "160")
    S.hdim(q(-HOLE_X, -HOLE_Y), q(HOLE_X, -HOLE_Y), 24.0, "120")
    S.vdim(q(-BASE_L / 2, -BASE_W / 2), q(-BASE_L / 2, BASE_W / 2), 28.0, "100")
    S.vdim(q(-HOLE_X, -HOLE_Y), q(-HOLE_X, HOLE_Y), 52.0, "70")
    S.hdim(q(UP_T / 2, RIB_T / 2), q(UP_T / 2 + RIB_L, RIB_T / 2), q(0, BASE_W / 2)[1] + 8, "60")
    S.leader_text(q(HOLE_X, HOLE_Y) + D._rot((1, 0), 45) * D_HOLE / 2, (215.0, 140.0), "4× Ø11")

    S.posnum(p(-60, 6), (40.0, 185.0), 1)
    S.posnum(p(0, 100), (95.0, 275.0), 2)
    S.posnum(p(20, 25), (230.0, 175.0), 3)
    S.notes(250.0, 128.0, ["1  Schweißverfahren ISO 4063-135 (MAG).",
                           "2  Bewertungsgruppe ISO 5817-C.",
                           "3  Kanten gebrochen, Schweißspritzer entfernen."])
    S.bom([("1", "1", "Grundplatte", "Bl 12 × 100 × 160", "S235JR"),
           ("2", "1", "Stirnplatte", "Bl 12 × 100 × 100", "S235JR"),
           ("3", "1", "Rippe", "Bl 10 × 60 × 60", "S235JR")])
    mass = sum(x.volume for x in parts) * RHO / 1000
    S.title_block(dict(title="Konsole", subtitle="Schweißbaugruppe, Beispiel der Zeichnungsbibliothek",
                       number="BSP-600", material="siehe Stückliste", mass=f"{mass:.0f} g",
                       scale="1:1", doctype="Schweißzeichnung", gentol="ISO 13920-BF",
                       project="Beispiel"))
    return S


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "output"
    sheet().save(out / "BSP-600.pdf", png=out / "BSP-600.png")
