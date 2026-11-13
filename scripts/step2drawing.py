"""STEP file -> drawing sheet, without writing any code.

    step2drawing part.step                      # A4..A0 and scale chosen automatically
    step2drawing part.step --lang en --projection third --units in
    step2drawing part.step --section --material "EN AW-6082" --density 2.7 --dxf

Produces three orthographic views (first- or third-angle placement), an isometric view
where there is room, hidden lines, centre lines and centre crosses for every cylindrical
feature, overall dimensions, the title block, and runs the sheet check. The result is a
correct starting sheet: functional dimensions, fits, geometrical tolerances and surface
texture still have to be added - by hand in the PDF/DXF, or in Python on top of
auto_drawing() which returns the Sheet and its views.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Surface
from build123d import Pos, Rot

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drawlib as D  # noqa: E402

GAP = 22.0          # space between views and for their dimensions, sheet mm
MARGIN = 12.0


def _bbox(shape):
    bb = shape.bounding_box()
    return np.array(tuple(bb.min)), np.array(tuple(bb.max))


def _cylinders(shape):
    """(location, unit direction, radius, (tmin, tmax) along the axis) of each cylinder."""
    out = []
    for f in shape.faces():
        if f.geom_type.name != "CYLINDER":
            continue
        cyl = BRepAdaptor_Surface(f.wrapped).Cylinder()
        ax = cyl.Axis()
        loc = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
        d = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        pts = np.array([tuple(e.position_at(t)) for e in f.edges() for t in (0, 0.5, 1)])
        ts = (pts - loc) @ d
        out.append((loc, d, cyl.Radius(), (ts.min(), ts.max())))
    return out


def _iso_size(shape, k):
    n, x = D.VIEWS["iso"]
    N, X = D._unit(n), D._unit(x)
    Y = np.cross(N, X)
    lo, hi = _bbox(shape)
    cs = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
    u, v = cs @ X, cs @ Y
    return k * (u.max() - u.min()), k * (v.max() - v.min()), (u.max() + u.min()) / 2, (v.max() + v.min()) / 2


def _choose(dx, dy, dz, fmt, scale, landscape):
    fmts = [fmt] if fmt != "auto" else ["A4", "A3", "A2", "A1", "A0"]
    best = None
    for f in fmts:
        short, long_ = D.Sheet.FORMATS[f]
        land = (f != "A4") if landscape is None else landscape
        W, H = (long_, short) if land else (short, long_)
        wav, hav = W - 30 - 2 * MARGIN, H - 20 - 45 - 2 * MARGIN
        ks = [scale] if scale != "auto" else D.SCALES
        for k in ks:
            if k * (dx + dy) + 3 * GAP <= wav and k * (dz + dy) + 3 * GAP <= hav:
                best = (f, k, land)
                break
        if best and best[0] == f and (best[1] * max(dx, dy, dz) >= 40 or f == fmts[-1]):
            return best
    if best:
        return best
    raise ValueError("the part does not fit on the chosen sheet at any ISO 5455 scale")


def auto_drawing(shape, out=None, fmt="auto", scale="auto", lang="de", projection="first",
                 title="Part", number="DRW-001", material="", density=None, author="",
                 up="z", section=False, hidden=True, iso=True, dims=True, units="mm",
                 dxf=False, png=True, landscape=None, check=True):
    """Three-view drawing of a build123d shape. Returns (sheet, views dict, issues);
    with out=None nothing is written and you can keep annotating the sheet."""
    if up == "y":
        shape = Rot(90, 0, 0) * shape
    lo, hi = _bbox(shape)
    c = (lo + hi) / 2
    shape = Pos(-c[0], -c[1], -lo[2]) * shape
    lo, hi = _bbox(shape)
    dx, dy, dz = hi - lo
    fmt, k, land = _choose(dx, dy, dz, fmt, scale if scale == "auto" else float(scale), landscape)
    S = D.Sheet(fmt, lang=lang, projection=projection, landscape=land)
    side = "left" if projection == "first" else "right"
    sizes = {"front": (k * dx, k * dz), "top": (k * dx, k * dy), side: (k * dy, k * dz)}
    # block of the three views (plus the isometric view if it fits beside it), centred in the
    # drawing area above the title block band
    ax0, ay0, ax1, ay1 = S.fl + MARGIN, S.fb + 45 + MARGIN, S.fr - MARGIN, S.ft - MARGIN
    blk_w = k * (dx + dy) + 2 * GAP
    blk_h = k * (dz + dy) + 2 * GAP
    iw, ih, iuc, ivc = _iso_size(shape, k)
    use_iso = iso and blk_w + GAP + iw <= ax1 - ax0 and ih <= ay1 - ay0
    tot_w = blk_w + (GAP + iw if use_iso else 0)
    x0 = ax0 + max(0.0, (ax1 - ax0 - tot_w) / 2) + GAP          # left edge of the front view
    y_top = ay1 - max(0.0, (ay1 - ay0 - blk_h) / 2)
    front_x = x0 + k * dx / 2
    if projection == "third":                      # top view above the front view
        front_y = y_top - k * dy - GAP - k * dz / 2
    else:                                          # room above the front view for its width
        front_y = y_top - GAP - k * dz / 2
    centres = D.views_layout((front_x, front_y), GAP, sizes, projection)
    views = {}
    for name, cc in centres.items():
        n, x = D.VIEWS[name]
        v_center = {"front": (0, dz / 2), "top": (0, 0), "left": (0, dz / 2), "right": (0, dz / 2)}[name]
        views[name] = D.View(S, np.asarray(cc) - k * np.asarray(v_center), k, n, x)
    F = views["front"]
    if section:
        F.section([(F.cut(shape, 0.0), 45, 2.5)], d=0.0)
    else:
        F.draw([shape], hidden=hidden)
    for name in ("top", side):
        views[name].draw([shape], hidden=hidden)
    if section:
        T = views["top"]
        S.cutting_plane(T.p(-dx / 2 - 8, 0), T.p(dx / 2 + 8, 0), "A", (0, 1))
        fc = centres["front"]
        above = 19 if (dims and projection == "first") else 8      # clear of the width dimension
        S.view_label(fc[0], fc[1] + k * dz / 2 + above, "A-A")
    # centre lines of all cylindrical features
    seen = set()
    for name, V in views.items():
        for loc, d, r, (t0, t1) in _cylinders(shape):
            a = abs(d @ V.N)
            if a > 0.999:
                p = V.P(loc)
                key = (name, "x", round(p[0], 1), round(p[1], 1))
                if key not in seen:
                    seen.add(key)
                    S.centre_cross(p, r * k)
            elif a < 1e-3:
                pa, pb = V.P(loc + d * t0), V.P(loc + d * t1)
                u = D._unit(pb - pa) if np.linalg.norm(pb - pa) > 1e-6 else np.array([1.0, 0])
                key = (name, "l", round(pa[0], 1), round(pa[1], 1), round(pb[0], 1), round(pb[1], 1))
                key2 = (name, "l", round(pb[0], 1), round(pb[1], 1), round(pa[0], 1), round(pa[1], 1))
                if key not in seen and key2 not in seen and np.linalg.norm(pb - pa) > 1.0:
                    seen.add(key)
                    S.centerline(pa - u * 3, pb + u * 3)
    # overall dimensions, each only once
    if dims:
        f = 1 / 25.4 if units == "in" else 1.0
        nd = 3 if units == "in" else 2
        txt = lambda v: f"{round(v * f, nd):g}"  # noqa: E731
        fr, tp = views["front"], views["top"]
        V3 = np.array([tuple(v) for v in shape.vertices()])

        def ext(axis, side_, pref, sgn):
            """Vertex on the extreme `side_` (min/max) along `axis`, preferring the one
            furthest along `pref` in direction sgn - extension lines start on real edges."""
            target = V3[:, axis].min() if side_ == "min" else V3[:, axis].max()
            cand = V3[np.abs(V3[:, axis] - target) < 1e-3]
            return cand[np.argmax(sgn * cand[:, pref])]

        up = 1 if projection == "first" else -1           # width dimension above or below
        a, b = ext(0, "min", 2, up), ext(0, "max", 2, up)
        y_dim = (fr.P((0, 0, hi[2]))[1] + 10) if up > 0 else (fr.P((0, 0, lo[2]))[1] - 10)
        S.hdim(fr.P(a), fr.P(b), y_dim, txt(dx))
        a, b = ext(2, "min", 0, -1), ext(2, "max", 0, -1)
        S.vdim(fr.P(a), fr.P(b), fr.P((lo[0], 0, 0))[0] - 10, txt(dz))
        a, b = ext(1, "min", 0, -1), ext(1, "max", 0, -1)
        S.vdim(tp.P(a), tp.P(b), tp.P((lo[0], 0, 0))[0] - 10, txt(dy))
    # isometric view to the right of the block, where there is room
    if use_iso:
        ctr = (x0 - GAP + blk_w + GAP + iw / 2, y_top - ih / 2)
        n, x = D.VIEWS["iso"]
        Vi = D.View(S, (ctr[0] - k * iuc, ctr[1] - k * ivc), k, n, x)
        Vi.draw([shape])
        views["iso"] = Vi
    mass = ""
    if density:
        mass = f"{shape.volume * density / 1000:.{0 if shape.volume * density > 10000 else 1}f} g"
    S.title_block(dict(title=title, number=number, material=material, mass=mass,
                       scale=D.scale_text(k), author=author))
    issues = []
    if out:
        out = Path(out)
        issues = S.save(out, png=out.with_suffix(".png") if png else None,
                        dxf=out.with_suffix(".dxf") if dxf else None, check=check)
    return S, views, issues


def main(argv=None):
    ap = argparse.ArgumentParser(prog="step2drawing", description=__doc__.split("\n\n")[0])
    ap.add_argument("step", type=Path, help="STEP file (.step / .stp)")
    ap.add_argument("-o", "--out", type=Path, help="output PDF (default: next to the STEP file)")
    ap.add_argument("--format", default="auto", choices=["auto", "A4", "A3", "A2", "A1", "A0"])
    ap.add_argument("--scale", default="auto", help="e.g. 2:1 or 1:5 (default: largest that fits)")
    ap.add_argument("--lang", default="de", choices=sorted(D.TEXTS))
    ap.add_argument("--projection", default="first", choices=["first", "third"])
    ap.add_argument("--units", default="mm", choices=["mm", "in"], help="units of the dimension values")
    ap.add_argument("--up", default="z", choices=["z", "y"], help="model axis that points up (Y-up CAD exports)")
    ap.add_argument("--section", action="store_true", help="front view as full section A-A")
    ap.add_argument("--no-hidden", action="store_true", help="leave out hidden lines")
    ap.add_argument("--no-iso", action="store_true", help="no isometric view")
    ap.add_argument("--title")
    ap.add_argument("--number")
    ap.add_argument("--material", default="")
    ap.add_argument("--density", type=float, help="g/cm³, fills in the mass")
    ap.add_argument("--author", default="")
    ap.add_argument("--dxf", action="store_true", help="also write a DXF (needs ezdxf)")
    ap.add_argument("--landscape", action="store_true", help="A4 in landscape")
    a = ap.parse_args(argv)
    scale = "auto"
    if a.scale != "auto":
        num, den = (float(v.replace(",", ".")) for v in a.scale.split(":"))
        scale = num / den
    shape = D.load_step(a.step)
    out = a.out or a.step.with_suffix(".pdf")
    _, views, issues = auto_drawing(
        shape, out, fmt=a.format, scale=scale, lang=a.lang, projection=a.projection,
        title=a.title or a.step.stem, number=a.number or a.step.stem.upper(),
        material=a.material, density=a.density, author=a.author, up=a.up, section=a.section,
        hidden=not a.no_hidden, iso=not a.no_iso, units=a.units, dxf=a.dxf,
        landscape=True if a.landscape else None)
    print(f"written: {out}  ({', '.join(views)})")
    print("next: add functional dimensions, fits, geometrical tolerances and surface texture")
    return 1 if any(i.level == "error" for i in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
