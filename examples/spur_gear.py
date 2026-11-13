"""Part drawing: spur gear (A4, 1:1) - gears are drawn simplified (ISO 2203) plus a data table.

The teeth are not modelled: the gear blank goes up to the tip circle, the section shows the
root line thick and the pitch line as a thin long-dash dot line, the end view shows the
tip circle and the pitch circle. Everything the gear cutter needs is in the data table.
Also: keyway in the bore (DIN 6885), section A-A marked in the end view.

Run:  python examples/spur_gear.py [output folder]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build123d import Axis, Box, Polyline, Pos, make_face, revolve  # noqa: E402

import drawlib as D  # noqa: E402

M, Z, ALPHA, K_SPAN = 2.0, 40, 20.0, 5          # module, teeth, pressure angle, span k
D_P = M * Z                                       # pitch circle 80
D_A, D_F = D_P + 2 * M, D_P - 2.5 * M             # tip 84, root 75
B = 20.0                                          # face width
D_HUB, L_HUB, D_WEB_IN, T_WEB = 45.0, 30.0, 65.0, 8.0
D_BORE, KEY_B, KEY_T2 = 25.0, 8.0, 3.3            # bore Ø25 H7, keyway 8 JS9, t2 = 3,3
RHO = 7.85


def span_measurement():
    """Base tangent length W_k (span over k teeth), spur gear without profile shift."""
    a = math.radians(ALPHA)
    inv = math.tan(a) - a
    return M * math.cos(a) * (math.pi * (K_SPAN - 0.5) + Z * inv)


def gear():
    rb, rh, rw, ra = D_BORE / 2, D_HUB / 2, D_WEB_IN / 2, D_A / 2
    c = 1.0
    prof = [(-L_HUB / 2, rb), (-L_HUB / 2, rh), (-T_WEB / 2, rh), (-T_WEB / 2, rw), (-B / 2, rw),
            (-B / 2, ra - c), (-B / 2 + c, ra), (B / 2 - c, ra), (B / 2, ra - c), (B / 2, rw),
            (T_WEB / 2, rw), (T_WEB / 2, rh), (L_HUB / 2, rh), (L_HUB / 2, rb)]
    g = revolve(make_face(Polyline(*[(x, 0, r) for x, r in prof], close=True)), Axis.X, 360)
    return g - Pos(0, 0, rb + KEY_T2 / 2 - 1) * Box(3 * L_HUB, KEY_B, KEY_T2 + 2)


def sheet():
    S = D.Sheet("A4")
    part = gear()
    ra, rp, rf, rb = D_A / 2, D_P / 2, D_F / 2, D_BORE / 2

    # --- section A-A through the axis and the keyway --------------------------------------
    V = D.View(S, (62.0, 200.0), 1.0, *D.VIEWS["front"])
    p = V.p
    V.section([(V.cut(part), 45, 2.0)])
    S.view_label(62.0, 268.0, "A-A")
    S.centerline(p(-L_HUB / 2 - 4, 0), p(L_HUB / 2 + 4, 0))
    for sg in (1, -1):                                  # ISO 2203 simplified teeth
        S.line([p(-B / 2 - 3, sg * rp), p(B / 2 + 3, sg * rp)], "center")
        S.seg(p(-B / 2, sg * rf), p(B / 2, sg * rf), "thick")
    S.hdim(p(-B / 2, ra), p(B / 2, ra), p(0, ra)[1] + 7, "20")
    S.hdim(p(-L_HUB / 2, rb + KEY_T2), p(L_HUB / 2, rb + KEY_T2), p(0, ra)[1] + 15, "30")
    S.hdim(p(-T_WEB / 2, -D_WEB_IN / 2), p(T_WEB / 2, -D_WEB_IN / 2), p(0, -ra)[1] - 7, "8")
    S.vdim(p(-L_HUB / 2, -rb), p(-L_HUB / 2, rb), 39.0, "Ø25 H7")
    S.vdim(p(-L_HUB / 2, -D_HUB / 2), p(-L_HUB / 2, D_HUB / 2), 30.0, "Ø45")
    S.vdim(p(B / 2, -D_WEB_IN / 2), p(B / 2, D_WEB_IN / 2), 85.0, "Ø65")
    S.vdim(p(B / 2, -ra), p(B / 2, ra), 94.0, "Ø84 h11")
    S.datum("A", (39.0, p(0, -rb)[1]), (0, -1), length=10.0)
    # runout of the tip cylinder to the bore axis; the leader meets the surface square on
    tip = p(-7.0, -ra)
    bx = S.fcf(tip[0] - D.H, tip[1] - 30, "total_runout", "0.03", ["A"])
    S.fcf_leader(bx, tip, "top")
    S.rough_leader(p(-13.0, -rb), (p(-13.0, 0)[0] + 1, p(0, -rb)[1] + 14), "Ra 1.6")

    # --- end view from the left, first-angle: to the right ----------------------------------
    E = D.View(S, (145.0, 200.0), 1.0, *D.VIEWS["left"])
    E.draw([part])
    c = E.p(0, 0)
    S.centre_cross(c, ra)
    S.circle(c, rp, "center")                          # pitch circle; root circle omitted
    S.cutting_plane((c[0], c[1] + ra + 10), (c[0], c[1] - ra - 10), "A", (-1, 0))
    S.hdim(E.p(-KEY_B / 2, rb + KEY_T2), E.p(KEY_B / 2, rb + KEY_T2), c[1] + rb + 12, "8 JS9",
           outside=True)
    S.vdim(E.p(0, -rb), E.p(0, rb + KEY_T2), c[0] + ra + 6, "28.3", tol=("+0.2", "0"))

    w = span_measurement()
    S.table(108.0, 142.0, [
        ("Verzahnungsdaten", "", ""),
        ("Modul", "m", S.num(M)),
        ("Zähnezahl", "z", str(Z)),
        ("Bezugsprofil", "", "DIN 867"),
        ("Eingriffswinkel", "α", f"{ALPHA:g}°"),
        ("Profilverschiebungsfaktor", "x", "0"),
        ("Teilkreisdurchmesser", "d", S.num(D_P)),
        ("Verzahnungsqualität", "", "8 DIN 3962"),
        (f"Zahnweite über k = {K_SPAN}", "W", S.num(w, 3)),
        ("Abmaße der Zahnweite", "", S._dec("-0.05 / -0.10")),
    ], widths=(46, 10, 34), h=2.5)
    S.fit_table(25.0, 120.0, ["Ø25 H7", "8 JS9", "Ø84 h11"], widths=(18, 26, 18, 18))
    S.notes(25.0, 90.0, ["1  Nicht bemaßte Fasen 1 × 45°.",
                         "2  Zahnflanken einsatzgehärtet und geschliffen."])
    S.general_surface(140.0, 61.0, "Ra 3.2")
    S.title_block(dict(title="Stirnrad", subtitle="m = 2, z = 40 - Beispiel der Zeichnungsbibliothek",
                       number="BSP-500", material="16MnCr5 (1.7131)",
                       mass=f"{part.volume * RHO / 1000:.0f} g", scale="1:1", project="Beispiel"))
    return S


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "output"
    sheet().save(out / "BSP-500.pdf", png=out / "BSP-500.png")
