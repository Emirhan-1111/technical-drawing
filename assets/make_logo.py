"""Logo of the technical-drawing skill: the ISO projection-method symbol with its centre
lines and a dimension line, on blueprint blue, with an orange check badge for the automatic
sheet check. Writes logo.svg, logo.png (1024 px) and logo-256.png next to this script.

Run:  python assets/make_logo.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Polygon  # noqa: E402

HERE = Path(__file__).parent
S = 512                                   # design grid, px
WHITE, ORANGE = "#ffffff", "#f39c12"
PX = 72 / 100                             # 1 design px in points at 100 dpi (5,12 in figure)


def draw(ax):
    ax.set_xlim(0, S)
    ax.set_ylim(0, S)
    ax.set_aspect("equal")
    ax.axis("off")
    # rounded square with a vertical blueprint gradient
    box = FancyBboxPatch((8, 8), S - 16, S - 16, boxstyle="round,pad=0,rounding_size=104",
                         lw=0, fc="none")
    ax.add_patch(box)
    g = np.linspace(0, 1, 256)[:, None]
    top, bottom = np.array([0x1d, 0x5f, 0xa3]) / 255, np.array([0x0b, 0x2e, 0x55]) / 255
    img = bottom + (top - bottom) * g
    im = ax.imshow(np.repeat(img[:, None, :], 2, axis=1), extent=(8, S - 8, 8, S - 8),
                   origin="lower", aspect="auto", zorder=0)
    im.set_clip_path(box)
    # faint drawing grid
    for v in range(40, S, 40):
        for xs, ys in (([v, v], [8, S - 8]), ([8, S - 8], [v, v])):
            ln, = ax.plot(xs, ys, color=WHITE, lw=1.2 * PX, alpha=0.07, zorder=1)
            ln.set_clip_path(box)

    cy = 290
    line = dict(color=WHITE, solid_capstyle="round", solid_joinstyle="round", zorder=3)
    # truncated cone, narrow end left (projection method 1)
    xl, xr = 96, 246
    ax.add_patch(Polygon([(xl, cy - 36), (xl, cy + 36), (xr, cy + 72), (xr, cy - 72)],
                         closed=True, fill=False, ec=WHITE, lw=15 * PX, joinstyle="round",
                         zorder=3))
    # end view: two circles
    cx = 362
    for r in (72, 36):
        ax.add_patch(Circle((cx, cy), r, fill=False, ec=WHITE, lw=15 * PX, zorder=3))
    # centre lines (long dash - dot)
    dash = dict(color=WHITE, lw=5 * PX, alpha=0.9, zorder=2,
                dashes=[d * PX for d in (30, 9, 5, 9)], dash_capstyle="round")
    ax.plot([70, 462], [cy, cy], **dash)
    ax.plot([cx, cx], [cy - 100, cy + 100], **dash)
    # dimension line with extension lines and filled arrows
    yd = 168
    for x in (xl, cx + 72):
        ax.plot([x, x], [cy - 82 if x == cx + 72 else cy - 52, yd - 16], lw=5 * PX, **line)
    ax.plot([xl + 22, cx + 72 - 22], [yd, yd], lw=6 * PX, **line)
    for x, d in ((xl, 1), (cx + 72, -1)):
        ax.add_patch(Polygon([(x, yd), (x + d * 34, yd + 12), (x + d * 34, yd - 12)],
                             closed=True, fc=WHITE, ec=WHITE, lw=2 * PX, joinstyle="round",
                             zorder=3))
    # check badge: the sheet check
    bx, by, br = 424, 82, 46
    ax.add_patch(Circle((bx, by), br + 9, fc="#0b2e55", ec="none", zorder=4))
    ax.add_patch(Circle((bx, by), br, fc=ORANGE, ec="none", zorder=5))
    ax.plot([bx - 20, bx - 5, bx + 22], [by + 2, by - 15, by + 17], lw=11 * PX,
            zorder=6, **{k: v for k, v in line.items() if k != "zorder"})


def save(path, px, fmt):
    fig = plt.figure(figsize=(5.12, 5.12), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    draw(ax)
    fig.savefig(path, format=fmt, dpi=px / 5.12, transparent=True)
    plt.close(fig)


if __name__ == "__main__":
    save(HERE / "logo.svg", 512, "svg")
    save(HERE / "logo.png", 1024, "png")
    save(HERE / "logo-256.png", 256, "png")
    print("written:", *(p.name for p in sorted(HERE.glob("logo*"))))
