"""Part drawing in English, third-angle projection, company title block (A3, 2:1).

The same library, set up for North American / international customers: lang="en" (title
block, notes heading, decimal point), projection="third" (top view above, right view to the
right, matching symbol), and a title block read from a JSON file with a company logo -
no change to the library code.

Run:  python examples/milled_block.py [output folder]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build123d import Box, Cylinder, Pos  # noqa: E402

import drawlib as D  # noqa: E402

HERE = Path(__file__).parent
L, W, Hh = 80.0, 50.0, 30.0                    # block
PL, PW, PD = 40.0, 24.0, 10.0                  # pocket from the top
D_HOLE = 12.0                                  # Ø12 H7 through the pocket floor
TAP_X, TAP_Y, D_CORE, TAP_DEPTH = 30.0, 17.0, 5.0, 15.0   # 4 × M6, core Ø5, drilled 15
RHO = 2.70


def block():
    b = Pos(0, 0, Hh / 2) * Box(L, W, Hh)
    b -= Pos(0, 0, Hh - PD / 2 + 0.01) * Box(PL, PW, PD + 0.02)
    b -= Pos(0, 0, Hh / 2) * Cylinder(D_HOLE / 2, 2 * Hh)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b -= Pos(sx * TAP_X, sy * TAP_Y, Hh - TAP_DEPTH / 2) * Cylinder(D_CORE / 2, TAP_DEPTH)
    return b


def logo(path):
    """A neutral placeholder logo, drawn once."""
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(2.4, 1.2), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(plt.Circle((0.45, 0.5), 0.36, color="#1f4e79"))
    ax.add_patch(plt.Rectangle((0.3, 0.42), 0.3, 0.16, color="white"))
    ax.text(0.95, 0.5, "YOUR\nLOGO", va="center", fontsize=15, color="#1f4e79", linespacing=0.9)
    fig.savefig(path, transparent=True)
    plt.close(fig)


def sheet():
    S = D.Sheet("A3", lang="en", projection="third")
    part = block()
    k = 2.0
    # third angle: top view ABOVE the front view, right-side view to the RIGHT
    sizes = {"front": (k * L, k * Hh), "top": (k * L, k * W), "right": (k * W, k * Hh)}
    c = D.views_layout((130.0, 95.0), 26.0, sizes, "third")
    F = D.View(S, c["front"] - (0, k * Hh / 2), k, *D.VIEWS["front"])
    T = D.View(S, c["top"], k, *D.VIEWS["top"])
    R = D.View(S, c["right"] - (0, k * Hh / 2), k, *D.VIEWS["right"])
    F.section([(F.cut(part), 45, 3.0)])
    T.draw([part])
    R.draw([part], hidden=True)
    p, q = F.p, T.p
    # ASME habit: the section title goes under the section
    S.view_label(c["front"][0], c["front"][1] - k * Hh / 2 - 26, "SECTION A-A")
    S.cutting_plane(q(-L / 2 - 4.5, 0), q(L / 2 + 4.5, 0), "A", (0, 1))

    # front view (section): height, pocket depth, bore with its fit, pocket floor texture
    S.vdim(p(-L / 2, 0), p(-L / 2, Hh), p(-L / 2, 0)[0] - 10, "30")
    S.vdim(p(PL / 2, Hh - PD), p(PL / 2, Hh), p(L / 2, 0)[0] + 10, "10")
    S.hdim(p(-D_HOLE / 2, 0), p(D_HOLE / 2, 0), p(0, 0)[1] - 10, "Ø12 H7", tshift=16)
    S.rough(p(-PL / 2 + 3, Hh - PD), "Ra 1.6")
    # top view: overall size, hole pattern, pocket
    S.hdim(q(-L / 2, W / 2), q(L / 2, W / 2), q(0, W / 2)[1] + 22, "80")
    S.hdim(q(-TAP_X, W / 2), q(TAP_X, W / 2), q(0, W / 2)[1] + 12, "60")
    # vertical dimensions outside the ends of the cutting plane
    S.vdim(q(-L / 2, -W / 2), q(-L / 2, W / 2), q(-L / 2, 0)[0] - 22, "50")
    S.vdim(q(-TAP_X, -TAP_Y), q(-TAP_X, TAP_Y), q(-L / 2, 0)[0] - 12, "34")
    for sx in (-1, 1):
        for sy in (-1, 1):
            c3 = q(sx * TAP_X, sy * TAP_Y)
            S.centre_cross(c3, 3.0 * k)
            S.thread_end(c3, 3.0 * k)                    # M6 seen from the end, ISO 6410
    S.centre_cross(q(0, 0), D_HOLE / 2 * k)
    S.leader_text(q(TAP_X, TAP_Y) + D._rot((1, 0), 45) * 3.0 * k,
                  (q(L / 2, 0)[0] + 18, q(0, W / 2)[1] + 6),
                  "4× M6 - 12 deep", under="drill Ø5 - 15 deep")
    S.leader_text(q(-10, -PW / 2), (215.0, q(0, -W / 2)[1] - 10), "pocket 40 × 24")

    S.notes(250.0, 225.0, ["1  Break all sharp edges 0.2 × 45°.",
                           "2  Tapped holes ISO 965-1, tolerance class 6H.",
                           "3  Anodize after machining."])
    S.fit_table(250.0, 198.0, ["Ø12 H7"])
    S.general_surface(345.0, 61.0, "Ra 3.2")
    S.title_block(dict(title="Clamp block", subtitle="Example part, third-angle projection",
                       number="EX-700", material="EN AW-6082 T651", rev="B",
                       mass=f"{part.volume * RHO / 1000:.0f} g", scale="2:1",
                       finish="Anodized, black", customer="Example Ltd.", author="",
                       approved=""), layout=HERE / "data" / "title_block_company.json",
                  logo=HERE / "data" / "logo.png")
    return S


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "output"
    if not (HERE / "data" / "logo.png").exists():
        logo(HERE / "data" / "logo.png")
    sheet().save(out / "EX-700.pdf", png=out / "EX-700.png")
