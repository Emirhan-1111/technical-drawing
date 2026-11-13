"""drawlib - ISO technical drawings from build123d models.

Sheet, title block, line types, views derived from the 3D model (hidden-line removal,
sections, hatching, detail / half / broken views), dimensioning, fits, geometrical
tolerancing, surface texture, threads, weld symbols, tables, parts list - and an automatic
check of the finished sheet.

Standards: sheet sizes and frame ISO 5457, title block ISO 7200, lines ISO 128-20/-24,
lettering ISO 3098, views ISO 128-30/-34/-44 and ISO 5456-2, dimensioning ISO 129-1,
limits and fits ISO 286, general tolerances ISO 2768-1, threads ISO 6410, surface texture
ISO 21920-1, geometrical tolerancing ISO 1101, datums ISO 5459, edges ISO 13715,
welds ISO 2553, item references ISO 6433, parts list ISO 7573.

All sheet coordinates are in mm, origin at the lower left corner of the trimmed sheet.
"""
__version__ = "1.0.0"

import datetime
import functools
import json
import logging
import math
import os
import re
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402
from OCP.BRep import BRep_Tool  # noqa: E402
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt  # noqa: E402
from OCP.HLRAlgo import HLRAlgo_Projector  # noqa: E402
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape  # noqa: E402
from build123d import Box, Compound, Plane  # noqa: E402

import iso_tolerances as tol  # noqa: E402

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


class DrawingWarning(UserWarning):
    """Raised for things that still produce a sheet but are probably not what you meant."""


# =====================================================================================
# lettering font
# =====================================================================================
FONT_FILE = "osifont-lgpl3fe.ttf"
FONT = None
_FAMILY = "DejaVu Sans"
FP = FontProperties(family=_FAMILY)
_CAP = 1.0
_INK = {}


def _locate_font():
    cands = []
    if os.environ.get("DRAWLIB_FONT"):
        cands.append(Path(os.environ["DRAWLIB_FONT"]))
    cands += [Path(__file__).with_name("fonts") / FONT_FILE,
              Path.home() / ".drawlib" / "fonts" / FONT_FILE]
    for c in cands:
        if c.is_file():
            return c
    for f in font_manager.fontManager.ttflist:                 # installed system-wide
        if f.name.lower() == "osifont":
            return Path(f.fname)
    return None


def set_font(path=None):
    """Choose the lettering font. Without an argument the ISO 3098 font osifont is looked up in
    $DRAWLIB_FONT, scripts/fonts/, ~/.drawlib/fonts/ and the system fonts; if it is missing,
    DejaVu Sans is used. Call it before creating a Sheet. Returns the font file or None."""
    global FONT, _FAMILY, FP, _CAP
    p = Path(path) if path else _locate_font()
    if p is not None and p.is_file():
        font_manager.fontManager.addfont(str(p))
        _FAMILY, FONT = FontProperties(fname=str(p)).get_name(), p
    else:
        if path:
            warnings.warn(f"font file {path} not found, using DejaVu Sans", DrawingWarning)
        _FAMILY, FONT = "DejaVu Sans", None
    plt.rcParams.update({"font.family": [_FAMILY, "DejaVu Sans"], "pdf.fonttype": 42,
                         "svg.fonttype": "none", "lines.scale_dashes": False,
                         "mathtext.default": "regular"})
    FP = FontProperties(family=_FAMILY)
    _CAP = TextPath((0, 0), "H", size=1, prop=FP).get_extents().height
    _INK.clear()
    return FONT


set_font()

PT = 72 / 25.4                       # points per mm
W_THICK, W_THIN, W_XTHICK = 0.5, 0.25, 0.7          # line group 0,5 (ISO 128-20)
H = 3.5                              # cap height of dimension lettering, mm
DASH = {"hidden": (3.0, 1.5), "center": (14.0, 2.0, 0.5, 2.0),
        "phantom": (14.0, 2.0, 0.5, 2.0, 0.5, 2.0)}
SCALES = (50, 20, 10, 5, 2, 1, 1 / 2, 1 / 5, 1 / 10, 1 / 20, 1 / 50, 1 / 100, 1 / 200)

# standard view directions: (n towards the viewer, xdir to the right); x right, y back, z up
VIEWS = {"front": ((0, -1, 0), (1, 0, 0)), "top": ((0, 0, 1), (1, 0, 0)),
         "bottom": ((0, 0, -1), (1, 0, 0)), "left": ((-1, 0, 0), (0, -1, 0)),
         "right": ((1, 0, 0), (0, 1, 0)), "rear": ((0, 1, 0), (-1, 0, 0)),
         "iso": ((1, -1, 1), (1, 1, 0))}
# where a view goes relative to the front view (sheet direction), ISO 5456-2
PLACEMENT = {"first": {"top": (0, -1), "bottom": (0, 1), "left": (1, 0), "right": (-1, 0)},
             "third": {"top": (0, 1), "bottom": (0, -1), "left": (-1, 0), "right": (1, 0)}}


def fsize(h):
    """Font size in pt for a cap height h in mm."""
    return h * PT / _CAP


def text_width(s, h=H):
    if not s:
        return 0.0
    return TextPath((0, 0), s, size=1, prop=FP).get_extents().width * fsize(h) / PT


def scale_text(k):
    """2.0 -> '2:1', 0.5 -> '1:2'."""
    f = Fraction(k).limit_denominator(1000)
    return f"{f.numerator}:{f.denominator}" if f >= 1 else f"1:{round(1 / float(f))}"


def load_step(path):
    """Read a STEP file into a build123d shape."""
    from build123d import import_step
    return import_step(str(path))


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _rot(v, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


# =====================================================================================
# languages
# =====================================================================================
TEXTS = {
    "de": dict(
        title="Titel, zusätzlicher Titel", number="Sachnummer", dept="Verantw. Abt.",
        ref="Technische Referenz", author="Erstellt durch", approved="Genehmigt von",
        doctype="Dokumentenart", status="Dokumentenstatus", material="Werkstoff",
        mass="Masse", gentol="Allgemeintoleranzen", tolprinciple="Tolerierung", rev="Änd.",
        lang="Spr.", scale="Maßstab", projection="Projektion", format="Format",
        project="Projekt", edges="Werkstückkanten ISO 13715", date="Ausgabedatum",
        sheet="Blatt", logo="", protection="Schutzvermerk ISO 16016 beachten",
        notes="Hinweise", doctype_default="Einzelteilzeichnung", status_default="Entwurf",
        bom=("Pos.", "Menge", "Benennung", "Sachnummer/Norm", "Werkstoff/Bemerkung"),
        fit_table=("Passmaß", "Abmaße", "Höchstmaß", "Mindestmaß"),
        pair_table=("Passung", "Höchstspiel", "Mindestspiel", "Art"),
        kinds={"clearance": "Spielpassung", "transition": "Übergangspassung",
               "interference": "Übermaßpassung"}),
    "en": dict(
        title="Title, supplementary title", number="Identification number",
        dept="Responsible dept.", ref="Technical reference", author="Created by",
        approved="Approved by", doctype="Document type", status="Document status",
        material="Material", mass="Mass", gentol="General tolerances",
        tolprinciple="Tolerancing", rev="Rev.", lang="Lang.", scale="Scale",
        projection="Projection", format="Size", project="Project", edges="Edges ISO 13715",
        date="Date of issue", sheet="Sheet", logo="",
        protection="Refer to protection notice ISO 16016", notes="Notes",
        doctype_default="Part drawing", status_default="Draft",
        bom=("Item", "Qty", "Description", "Part no./Standard", "Material/Remark"),
        fit_table=("Fit", "Deviations", "Max.", "Min."),
        pair_table=("Fit", "Max. clearance", "Min. clearance", "Type"),
        kinds={"clearance": "Clearance fit", "transition": "Transition fit",
               "interference": "Interference fit"}),
}
DECIMAL = {"de": ",", "en": "."}

# title block ISO 7200 as data: row edges from the bottom, cells with x range and row span
ISO7200 = {
    "width": 180.0, "rows": [0, 9, 18, 27, 45], "label_h": 1.6, "value_h": 2.5,
    "cells": [
        {"row": 3, "x": [0, 118], "label": "title", "type": "title"},
        {"row": 3, "x": [118, 180], "label": "number", "type": "number"},
        {"row": 2, "x": [0, 30], "label": "dept"},
        {"row": 2, "x": [30, 60], "label": "ref"},
        {"row": 2, "x": [60, 88], "label": "author"},
        {"row": 2, "x": [88, 118], "label": "approved"},
        {"row": 2, "x": [118, 152], "label": "doctype"},
        {"row": 2, "x": [152, 180], "label": "status"},
        {"row": 1, "x": [0, 70], "label": "material"},
        {"row": 1, "x": [70, 88], "label": "mass"},
        {"row": 1, "x": [88, 118], "label": "gentol"},
        {"row": 1, "x": [118, 152], "label": "tolprinciple"},
        {"row": 1, "x": [152, 166], "label": "rev"},
        {"row": 1, "x": [166, 180], "label": "lang"},
        {"row": 0, "x": [0, 18], "label": "scale"},
        {"row": 0, "x": [18, 36], "label": "projection", "type": "projection"},
        {"row": 0, "x": [36, 50], "label": "format"},
        {"row": 0, "x": [50, 88], "label": "project"},
        {"row": 0, "x": [88, 118], "label": "edges", "type": "edges"},
        {"row": 0, "x": [118, 152], "label": "date"},
        {"row": 0, "x": [152, 180], "label": "sheet"},
    ],
}


# =====================================================================================
# geometry helpers: clipping, hatching
# =====================================================================================
def _seg_rect(a, b, r):
    """Parameter interval (t0, t1) of segment a-b inside rectangle r=(x0, y0, x1, y1)."""
    d = b - a
    t0, t1 = 0.0, 1.0
    for p, q in ((-d[0], a[0] - r[0]), (d[0], r[2] - a[0]), (-d[1], a[1] - r[1]), (d[1], r[3] - a[1])):
        if abs(p) < 1e-15:
            if q < 0:
                return None
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return None
    return (t0, t1)


def _seg_circle(a, b, c, r):
    d, f = b - a, a - c
    A, B, C = d @ d, 2 * (f @ d), f @ f - r * r
    if A < 1e-18:
        return (0.0, 1.0) if C <= 0 else None
    disc = B * B - 4 * A * C
    if disc <= 0:
        return None
    s = math.sqrt(disc)
    t0, t1 = max((-B - s) / (2 * A), 0.0), min((-B + s) / (2 * A), 1.0)
    return (t0, t1) if t0 < t1 else None


def _clip_polyline(pts, clip):
    """Parts of a polyline inside clip = ('rect', (x0, y0, x1, y1)) or ('circle', c, r)."""
    out, cur = [], None
    c = np.asarray(clip[1], float) if clip[0] == "circle" else None
    for a, b in zip(pts[:-1], pts[1:]):
        iv = _seg_rect(a, b, clip[1]) if clip[0] == "rect" else _seg_circle(a, b, c, clip[2])
        if iv is None or iv[1] - iv[0] < 1e-12:
            if cur:
                out.append(cur)
            cur = None
            continue
        p, q = a + (b - a) * iv[0], a + (b - a) * iv[1]
        if cur is not None and iv[0] <= 1e-9:
            cur.append(q)
        else:
            if cur:
                out.append(cur)
            cur = [p, q]
        if iv[1] < 1 - 1e-9:
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return [np.array(c_) for c_ in out if len(c_) >= 2]


def _complement(ivs):
    ivs = sorted(ivs)
    out, t = [], 0.0
    for a, b in ivs:
        if a > t:
            out.append((t, a))
        t = max(t, b)
    if t < 1.0:
        out.append((t, 1.0))
    return out


def hatch(sheet, segs, angle=45.0, spacing=2.0, offset=0.0, emit=None):
    """Hatching by the even-odd rule inside closed segment loops (sheet mm)."""
    if not segs:
        return
    emit = emit or (lambda pts: sheet.line(pts, "thin", z=2, role="hatch"))
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    R = np.array([[c, s], [-s, c]])           # rotates the hatch direction onto the x axis
    S = np.array([[R @ np.asarray(p) for p in sg] for sg in segs])
    ymin, ymax = S[:, :, 1].min(), S[:, :, 1].max()
    y = math.floor((ymin - offset) / spacing) * spacing + offset + spacing * 0.5
    Ri = R.T
    while y < ymax:
        xs = []
        for (x1, y1), (x2, y2) in S:
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            emit(np.array([Ri @ np.array([xs[i], y]), Ri @ np.array([xs[i + 1], y])]))
        y += spacing


# =====================================================================================
# text boxes (ink extents), used by the sheet check and by hatch interruption
# =====================================================================================
def _ink(s):
    if s not in _INK:
        if not s.strip():
            _INK[s] = None
        else:
            e = TextPath((0, 0), s, size=1, prop=FP).get_extents()
            _INK[s] = (e.x0, e.y0, e.x1, e.y1)
    return _INK[s]


def text_box(x, y, s, h=H, ha="left", va="baseline", rot=0.0):
    """Axis-aligned box (x0, y0, x1, y1) around the ink of a text, sheet mm."""
    ink = _ink(s)
    if ink is None:
        return None
    k = fsize(h) / PT
    lp = _ink("lp")
    A, Dd = lp[3] * k, -lp[1] * k
    adv = ink[2] * k
    dx = {"left": 0.0, "center": -adv / 2, "right": -adv}.get(ha, 0.0)
    dy = {"baseline": 0.0, "center_baseline": 0.0, "bottom": Dd, "top": -A,
          "center": -(A - Dd) / 2}.get(va, 0.0)
    cs = np.array([[ink[i] * k + dx, ink[j] * k + dy] for i in (0, 2) for j in (1, 3)])
    if rot:
        cs = np.array([_rot(c, rot) for c in cs])
    cs += (x, y)
    return (*cs.min(0), *cs.max(0))


@dataclass
class Issue:
    level: str          # "error", "warning" or "info"
    msg: str
    box: tuple = None   # sheet mm (x0, y0, x1, y1)
    grid: str = ""

    def __str__(self):
        where = f"  [{self.grid}]" if self.grid else ""
        return f"{self.level:<7} {self.msg}{where}"


def _annotation(role="annot"):
    """Groups everything one annotation call draws, so the check can tell its parts apart."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(self, *a, **k):
            with self._ann(role):
                return fn(self, *a, **k)
        return wrapper
    return deco


# =====================================================================================
class Sheet:
    """A drawing sheet with frame, grid references and centring marks (ISO 5457).

    fmt: "A4" (portrait by default), "A3", "A2", "A1", "A0" (landscape by default)
    lang: "de" or "en" (or any key you add to drawlib.TEXTS) - title block, parts list, notes
    projection: "first" (ISO method 1, Europe) or "third" (ISO method 3, North America)
    decimal: decimal marker for numbers the library writes; default from the language."""
    FORMATS = {"A4": (210.0, 297.0), "A3": (297.0, 420.0), "A2": (420.0, 594.0),
               "A1": (594.0, 841.0), "A0": (841.0, 1189.0)}

    def __init__(self, fmt="A4", lang="de", projection="first", landscape=None, decimal=None):
        if fmt not in self.FORMATS:
            raise ValueError(f"unknown sheet size '{fmt}', use one of {', '.join(self.FORMATS)}")
        if lang not in TEXTS:
            raise ValueError(f"unknown language '{lang}'; available: {', '.join(TEXTS)} "
                             f"(add your own with drawlib.TEXTS['xx'] = {{...}})")
        if projection not in ("first", "third"):
            raise ValueError("projection is 'first' (ISO method 1) or 'third' (ISO method 3)")
        self.fmt, self.lang, self.projection = fmt, lang, projection
        self.T = TEXTS[lang]
        self.dec = decimal or DECIMAL.get(lang, ".")
        short, long_ = self.FORMATS[fmt]
        landscape = (fmt != "A4") if landscape is None else landscape
        self.W, self.H = (long_, short) if landscape else (short, long_)
        self.fig = plt.figure(figsize=(self.W / 25.4, self.H / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, self.W)
        self.ax.set_ylim(0, self.H)
        self.ax.set_aspect("equal")
        self.ax.axis("off")
        self._texts, self._regions, self._views = [], [], []
        self._datums, self._datum_refs = [], []
        self._tb, self._tb_rect = None, None
        self._group, self._gcount, self._role = 0, 0, None
        self._finalized = False
        self.frame()

    # --- bookkeeping -----------------------------------------------------------------
    @contextmanager
    def _ann(self, role="annot"):
        if self._role is not None:          # nested call: stay in the outer group
            yield
            return
        self._gcount += 1
        self._group, self._role = self._gcount, role
        try:
            yield
        finally:
            self._group, self._role = 0, None

    def num(self, x, nd=None):
        """Number with the sheet's decimal marker; nd = fixed decimals (None: shortest)."""
        s = f"{x:.{nd}f}" if nd is not None else f"{x:g}"
        return s.replace(".", self.dec)

    def _dec(self, s):
        """Decimal markers between digits follow the sheet: '0.02' -> '0,02' on a German sheet."""
        return re.sub(r"(?<=\d)[.,](?=\d)", self.dec, s) if isinstance(s, str) else s

    # --- primitives --------------------------------------------------------------
    def line(self, pts, style="thick", z=3, color="k", role=None):
        pts = np.asarray(pts, float)
        if len(pts) < 2:
            return
        role = role or self._role or "annot"
        gid = f"{style}|{role}|{self._group}"
        if style in ("thick", "thin", "xthick"):
            w = {"thick": W_THICK, "thin": W_THIN, "xthick": W_XTHICK}[style]
            self.ax.plot(pts[:, 0], pts[:, 1], color=color, lw=w * PT, solid_capstyle="round",
                         solid_joinstyle="round", zorder=z, gid=gid)
        else:
            w = W_THICK if style == "hidden_thick" else W_THIN
            d = DASH[style.replace("_thick", "")]
            self.ax.plot(pts[:, 0], pts[:, 1], color=color, lw=w * PT, dashes=[x * PT for x in d],
                         dash_capstyle="butt", zorder=z, gid=gid)

    def seg(self, a, b, style="thick", z=3, role=None):
        self.line([a, b], style, z, role=role)

    def text(self, x, y, s, h=H, ha="center", va="baseline", rot=0.0, z=6, role=None, **kw):
        kw.pop("weight", None)                    # ISO 3098 lettering has no bold
        role = role or self._role or "annot"
        s = str(s)
        art = self.ax.text(x, y, s, fontsize=fsize(h), ha=ha, va=va, rotation=rot,
                           rotation_mode="anchor", zorder=z, **kw)
        art.set_gid(f"text|{role}|{self._group}")
        self._texts.append(dict(x=float(x), y=float(y), s=s, h=h, ha=ha, va=va, rot=rot,
                                role=role, group=self._group))
        return art

    def poly(self, pts, fill="k", z=5, closed=True, lw=0.0):
        p = Polygon(np.asarray(pts, float), closed=closed, facecolor=fill, edgecolor="k",
                    lw=lw * PT, zorder=z)
        p.set_gid(f"poly|{self._role or 'annot'}|{self._group}")
        self.ax.add_patch(p)

    def dot(self, c, r=0.55):
        p = Circle(tuple(c), r, color="k", zorder=6)
        p.set_gid(f"dot|{self._role or 'annot'}|{self._group}")
        self.ax.add_patch(p)

    def image(self, path, rect):
        """Raster image (logo) fitted into rect=(x0, y0, x1, y1), aspect ratio kept."""
        img = mpimg.imread(str(path))
        x0, y0, x1, y1 = rect
        ih, iw = img.shape[:2]
        s = min((x1 - x0) / iw, (y1 - y0) / ih)
        w, h = iw * s, ih * s
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.ax.imshow(img, extent=(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2), zorder=5,
                       interpolation="lanczos")
        self.ax.set_xlim(0, self.W)
        self.ax.set_ylim(0, self.H)

    def arc(self, c, r, a0, a1, style="thin", n=None):
        n = n or max(8, int(abs(a1 - a0) / 3))
        t = np.radians(np.linspace(a0, a1, n))
        self.line(np.c_[c[0] + r * np.cos(t), c[1] + r * np.sin(t)], style)

    def circle(self, c, r, style="thick"):
        self.arc(c, r, 0, 360, style, n=max(24, int(r * 8)))

    @_annotation("annot")
    def centerline(self, a, b):
        """Centre line; starts and ends with a long dash (ISO 128-24)."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        m = (a + b) / 2
        self.line([m, a], "center", z=2)
        self.line([m, b], "center", z=2)

    @_annotation("annot")
    def centre_cross(self, c, r, over=2.5, angle=0.0):
        c = np.asarray(c, float)
        for d in (_rot((1, 0), angle), _rot((0, 1), angle)):
            if r * 2 + over * 2 < 12:          # small circles: thin continuous line
                self.seg(c - d * (r + over), c + d * (r + over), "thin", z=2)
            else:
                self.centerline(c - d * (r + over), c + d * (r + over))

    @_annotation("annot")
    def pitch_circle(self, c, r, holes=(), over=2.5):
        """Pitch circle of a hole pattern (thin long-dash dot) with radial centre lines
        through the holes; holes = angles in degrees."""
        c = np.asarray(c, float)
        n = max(48, int(r * 6))
        t = np.radians(np.linspace(0, 360, n))
        self.line(np.c_[c[0] + r * np.cos(t), c[1] + r * np.sin(t)], "center", z=2)
        for a in holes:
            e = _rot((1, 0), a)
            self.seg(c + e * (r - over - 3), c + e * (r + over + 3), "thin", z=2)

    @_annotation("annot")
    def thread_end(self, c, r_nom):
        """Internal thread seen from the end (ISO 6410): nominal Ø as a thin three-quarter circle."""
        self.arc(c, r_nom, 95, 355, "thin")

    def arrow(self, tip, direction, length=3.0, half=0.6):
        """Filled dimension arrow; its tip is at `tip` and it points along `direction`."""
        d = _unit(direction)
        n = np.array([-d[1], d[0]])
        tip = np.asarray(tip, float)
        base = tip - d * length
        self.poly([tip, base + n * half, base - n * half])

    @_annotation("annot")
    def break_line(self, a, b, amp=2.5):
        """Break line (ISO 128-20, thin continuous line with a zigzag) from a to b."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        d = _unit(b - a)
        n = np.array([-d[1], d[0]])
        m = (a + b) / 2
        z = 1.6
        self.line([a - d * 2, m - d * z, m - d * z / 3 + n * amp, m + d * z / 3 - n * amp,
                   m + d * z, b + d * 2], "thin")

    # --- frame and title block -------------------------------------------------------
    def frame(self):
        with self._ann("frame"):
            W, Hh = self.W, self.H
            self.fl, self.fb, self.fr, self.ft = 20.0, 10.0, W - 10.0, Hh - 10.0
            self.line([(0, 0), (W, 0), (W, Hh), (0, Hh), (0, 0)], "thin", z=1)    # trimmed edge
            self.line([(self.fl, self.fb), (self.fr, self.fb), (self.fr, self.ft),
                       (self.fl, self.ft), (self.fl, self.fb)], "xthick")
            cx, cy = W / 2, Hh / 2                                                  # centring marks
            for a, b in (((cx, 0), (cx, self.fb + 5)), ((cx, Hh), (cx, self.ft - 5)),
                         ((5, cy), (self.fl + 5, cy)), ((W, cy), (self.fr - 5, cy))):
                self.seg(a, b, "xthick")
            # grid reference squares, 50 mm pitch measured from the centring marks
            xs = sorted(set([self.fl, self.fr] + [x for x in np.arange(cx % 50, W, 50)
                                                   if self.fl + 5 < x < self.fr - 5]))
            ys = sorted(set([self.fb, self.ft] + [y for y in np.arange(cy % 50, Hh, 50)
                                                   if self.fb + 5 < y < self.ft - 5]))
            self._grid = (xs, ys)
            for x in xs[1:-1]:
                for y0, y1 in ((self.fb - 5, self.fb), (self.ft, self.ft + 5)):
                    self.seg((x, y0), (x, y1), "thin")
            for y in ys[1:-1]:
                for x0, x1 in ((self.fl - 5, self.fl), (self.fr, self.fr + 5)):
                    self.seg((x0, y), (x1, y), "thin")
            self.line([(self.fl - 5, 5), (self.fr + 5, 5), (self.fr + 5, Hh - 5),
                       (self.fl - 5, Hh - 5), (self.fl - 5, 5)], "thin", z=1)
            for i in range(len(xs) - 1):
                for y in (self.fb - 3.6, self.ft + 1.4):
                    self.text((xs[i] + xs[i + 1]) / 2, y, str(i + 1), h=2.5)
            for j in range(len(ys) - 1):
                for x in (self.fl - 2.5, self.fr + 2.5):
                    self.text(x, (ys[j] + ys[j + 1]) / 2, self._row_letter(len(ys) - 2 - j),
                              h=2.5, va="center")

    @staticmethod
    def _row_letter(i):
        return "ABCDEFGHJKLMNPQRSTUVWXYZ"[i]

    def grid_ref(self, x, y):
        """Grid reference such as 'C3' for a sheet point."""
        xs, ys = self._grid
        col = min(max(int(np.searchsorted(xs, x)) , 1), len(xs) - 1)
        row = min(max(int(np.searchsorted(ys, y)), 1), len(ys) - 1)
        return f"{self._row_letter(len(ys) - 1 - row)}{col}"

    def title_block(self, t, layout=None, logo=None):
        """Title block in the lower right corner of the frame.

        t: dict of values; keys are the cell keys of the layout. For the default ISO 7200
           layout: title, subtitle, number, material, mass, scale, author, dept, ref,
           approved, doctype, status, rev, lang, project, date, sheet, gentol, tolprinciple,
           edges=(outer, inner). Required: title, number.
        layout: None (ISO 7200), a dict like drawlib.ISO7200 or a path to a JSON file with
           that structure - your company's own title block without touching the code.
        logo: image file for a cell of type "image" with key "logo"."""
        if isinstance(layout, (str, Path)):
            layout = json.loads(Path(layout).read_text(encoding="utf-8"))
        L = layout or ISO7200
        for k in ("title", "number"):
            if not t.get(k):
                raise ValueError(f"title_block needs '{k}'")
        T = self.T
        vals = dict(doctype=T["doctype_default"], status=T["status_default"], rev="A",
                    lang=self.lang, format=self.fmt, gentol="ISO 2768-mK",
                    tolprinciple="ISO 8015", date=datetime.date.today().isoformat(),
                    sheet="1/1", edges=(self._dec("-0.3"), self._dec("+0.1")))
        vals.update({k: v for k, v in t.items() if v is not None})
        if logo:
            vals["logo"] = logo
        self._tb = vals
        width, rows = float(L.get("width", 180.0)), [float(r) for r in L["rows"]]
        lh, vh = float(L.get("label_h", 1.6)), float(L.get("value_h", 2.5))
        x0, y0 = self.fr - width, self.fb
        self._tb_rect = (x0, y0, self.fr, y0 + rows[-1])
        with self._ann("tb"):
            tb_group = self._group
            for cell in L["cells"]:
                r0, r1 = cell["rows"] if "rows" in cell else (cell["row"], cell["row"] + 1)
                xa, xb = x0 + cell["x"][0], x0 + cell["x"][1]
                ya, yb = y0 + rows[r0], y0 + rows[r1]
                self.line([(xa, ya), (xb, ya), (xb, yb), (xa, yb), (xa, ya)], "thick", z=4)
                key = cell.get("key", cell.get("label"))
                label = T.get(cell.get("label"), cell.get("label", "")) if cell.get("label") else ""
                if label:
                    self.text(xa + 1.0, yb - lh - 0.8, label, h=lh, ha="left")
                kind = cell.get("type", "text")
                v = vals.get(key, cell.get("default", ""))
                if kind == "title":
                    hh = min(5.0, 0.9 * (xb - xa - 3) / max(text_width(str(v), 1.0), 1e-6))
                    self.text(xa + 1.5, ya + (yb - ya) * 0.47, v, h=hh, ha="left")
                    sub = vals.get("subtitle", "")
                    if sub:
                        hs = min(2.5, 0.9 * (xb - xa - 3) / max(text_width(sub, 1.0), 1e-6))
                        self.text(xa + 1.5, ya + 2.6, sub, h=hs, ha="left")
                elif kind == "number":
                    hh = min(5.0, 0.9 * (xb - xa - 3) / max(text_width(str(v), 1.0), 1e-6))
                    self.text((xa + xb) / 2, ya + (yb - ya) * 0.3, v, h=hh)
                elif kind == "projection":
                    self.projection_symbol((xa + xb) / 2 - 4.9, ya + 0.9, s=0.8)
                elif kind == "edges":
                    self.edge_symbol(xa + 3.0, ya + 1.0, vals.get("edges"))
                elif kind == "image":
                    if v:
                        self.image(v, (xa + 1, ya + 1, xb - 1, yb - lh - 1.6 if label else yb - 1))
                elif v:
                    v = str(v)
                    h = min(float(cell.get("h", vh)), 0.9 * (xb - xa - 2.4) / max(text_width(v, 1.0), 1e-6))
                    if cell.get("align") == "center":
                        self.text((xa + xb) / 2, ya + 1.6, v, h=h)
                    else:
                        self.text(xa + 1.2, ya + 1.6, v, h=h, ha="left")
            self._regions.append((self._tb_rect, "title block", tb_group))
        if L.get("protection", True):
            with self._ann("frame"):
                self.text(12.5, self.fb + 2.0, T["protection"], h=1.8, rot=90, ha="left")

    def projection_symbol(self, x, y, s=1.0):
        """Projection method symbol (ISO 5456-2). The end view always shows the small end of
        the truncated cone; the cone points away from it for method 1 and towards it for 3."""
        h1, h2, ln = 2.6 * s, 5.2 * s, 5.2 * s
        cy = y + h2 / 2 + 0.3
        left_h, right_h = (h1, h2) if self.projection == "first" else (h2, h1)
        self.line([(x, cy - left_h / 2), (x, cy + left_h / 2), (x + ln, cy + right_h / 2),
                   (x + ln, cy - right_h / 2), (x, cy - left_h / 2)], "thin")
        cx = x + ln + 4.5 * s
        self.circle((cx, cy), h2 / 2, "thin")
        self.circle((cx, cy), h1 / 2, "thin")
        self.seg((x - 0.8, cy), (cx + h2 / 2 + 0.8, cy), "thin")
        self.seg((cx, cy - h2 / 2 - 0.8), (cx, cy + h2 / 2 + 0.8), "thin")

    def edge_symbol(self, x, y, vals):
        """Edge symbol to ISO 13715 with the values for the outer and inner edge."""
        self.line([(x, y + 1.0), (x + 4.0, y + 1.0), (x + 4.0, y + 5.0)], "thin")
        self.seg((x + 0.6, y + 1.6), (x + 3.4, y + 4.4), "thin")
        self.text(x + 5.0, y + 1.3, f"({vals[0]}  {vals[1]})", h=2.5, ha="left")

    @_annotation("tb")
    def bom(self, rows, x0=None, y0=None, rh=6.0, cols=(0, 11, 25, 85, 120, 180), heads=None):
        """Parts list (ISO 7573) above the title block; the header row is at the bottom and
        item 1 sits directly above it. rows: one tuple per row, one string per column."""
        heads = heads or self.T["bom"]
        x0 = self.fr - 180.0 if x0 is None else x0
        y0 = (self._tb_rect[3] if self._tb_rect else self.fb + 45.0) if y0 is None else y0
        w = cols[-1]
        top = y0 + rh * (len(rows) + 1)
        self.line([(x0, y0), (x0, top), (x0 + w, top), (x0 + w, y0)], "thick", z=4)
        self.seg((x0, y0 + rh), (x0 + w, y0 + rh), "thick", z=4)
        for c in cols[1:-1]:
            self.seg((x0 + c, y0), (x0 + c, top), "thin")
        for i, hd in enumerate(heads):
            self.text(x0 + cols[i] + 1.2, y0 + 1.8, hd, h=2.5, ha="left")
        for j, row in enumerate(rows):
            y = y0 + rh * (j + 1)
            self.seg((x0, y + rh), (x0 + w, y + rh), "thin")
            for i, v in enumerate(row):
                width = cols[i + 1] - cols[i] - 2.4
                h = min(2.5, 0.9 * width / max(text_width(str(v), 1.0), 1e-6))
                self.text(x0 + cols[i] + 1.2, y + 1.8, v, h=h, ha="left")
        self._regions.append(((x0, y0, x0 + w, top), "parts list", self._group))
        return (x0, y0, x0 + w, top)

    @_annotation("table")
    def table(self, x, y, rows, widths, h=2.5, row_h=None, head_rows=1, align=None):
        """Table with its upper left corner at (x, y), e.g. gear data or a fit table.
        rows: list of tuples of strings; the first head_rows rows are headings.
        align: per column 'left' or 'center'. Returns (x0, y0, x1, y1)."""
        rh = row_h or h * 2.4
        W, Ht = float(sum(widths)), rh * len(rows)
        xs = np.cumsum([x] + list(widths))
        self.line([(x, y), (x + W, y), (x + W, y - Ht), (x, y - Ht), (x, y)], "thick", z=4)
        for xv in xs[1:-1]:
            self.seg((xv, y), (xv, y - Ht), "thin")
        for j in range(1, len(rows)):
            self.seg((x, y - rh * j), (x + W, y - rh * j), "thick" if j == head_rows else "thin")
        align = align or ["left"] + ["center"] * (len(widths) - 1)
        for j, row in enumerate(rows):
            yb = y - rh * (j + 1) + (rh - h) / 2
            for i, v in enumerate(row):
                v = str(v)
                w = xs[i + 1] - xs[i] - 2.4
                hh = min(h, 0.95 * w / max(text_width(v, 1.0), 1e-6))
                if align[i] == "center":
                    self.text((xs[i] + xs[i + 1]) / 2, yb, v, h=hh)
                else:
                    self.text(xs[i] + 1.2, yb, v, h=hh, ha="left")
        rect = (x, y - Ht, x + W, y)
        self._regions.append((rect, "table", self._group))
        return rect

    def fit_table(self, x, y, items, widths=(26, 30, 22, 22), h=2.5):
        """Limits table for toleranced sizes, values from ISO 286.
        items: dimension texts such as "Ø10 H7" or "25 g6" (or tuples (label, size, class))."""
        rows = [self.T["fit_table"]]
        for it in items:
            label, size, code = it if isinstance(it, tuple) else (it, *tol.parse_fits(it)[0][:2])
            up, lo = tol.deviations(size, code)
            mx, mn = tol.limits(size, code)
            rows.append((self._dec(label), f"{tol.fmt_dev(up, self.dec)} / {tol.fmt_dev(lo, self.dec)}",
                         self.num(mx, 3), self.num(mn, 3)))
        return self.table(x, y, rows, widths, h=h)

    def fit_pair_table(self, x, y, items, widths=(28, 24, 24, 30), h=2.5):
        """Fit table for assemblies: items such as "Ø20 H7/s6". Clearances in mm,
        negative values are interference."""
        rows = [self.T["pair_table"]]
        for it in items:
            size, hole, shaft = tol.parse_fits(it)[0]
            f = tol.fit(size, hole, shaft)
            rows.append((self._dec(it), tol.fmt_dev(f["max_clearance"], self.dec),
                         tol.fmt_dev(f["min_clearance"], self.dec), self.T["kinds"][f["kind"]]))
        return self.table(x, y, rows, widths, h=h)

    # --- saving ------------------------------------------------------------------------
    def _finalize(self):
        if not self._finalized:
            self._interrupt_hatching()
            self._finalized = True

    def save(self, path, png=None, dpi=150, check=True, dxf=None, quiet=False):
        """Write the sheet. The format follows the suffix: .pdf, .svg, .png or .dxf (needs
        ezdxf). png=<path> also writes a raster preview, dxf=<path> also writes a DXF.
        check=True runs Sheet.check(), prints what it finds and, if there is a preview,
        writes <preview>_check.png with the problems marked. Returns the list of issues."""
        self._finalize()
        issues = self.check(verbose=False) if check else []
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".dxf":
            import dxf_export
            dxf_export.save_dxf(self, path)
        else:
            self.fig.savefig(path, format=path.suffix[1:].lower(), dpi=dpi)
        if dxf:
            import dxf_export
            dxf_export.save_dxf(self, dxf)
        if png:
            Path(png).parent.mkdir(parents=True, exist_ok=True)
            self.fig.savefig(png, format="png", dpi=dpi)
        marked = [i for i in issues if i.level in ("error", "warning") and i.box]
        if check and png and marked:
            for i in marked:
                x0, y0, x1, y1 = i.box
                self.ax.add_patch(Rectangle((x0 - 1, y0 - 1), x1 - x0 + 2, y1 - y0 + 2, fill=False,
                                            ec="red" if i.level == "error" else "orange",
                                            lw=1.2, zorder=20))
            cp = Path(png).with_name(Path(png).stem + "_check.png")
            self.fig.savefig(cp, format="png", dpi=dpi)
        if check and not quiet:
            self.report(issues, path.name)
        plt.close(self.fig)
        return issues

    @staticmethod
    def report(issues, name=""):
        ne = sum(i.level == "error" for i in issues)
        nw = sum(i.level == "warning" for i in issues)
        print(f"drawing check {name}: {ne} error(s), {nw} warning(s)")
        for i in issues:
            if i.level != "info":
                print("  " + str(i))

    # --- texts and leader notes -----------------------------------------------------------
    @_annotation("annot")
    def notes(self, x, y, lines, h=2.5, lead=1.6, head=None):
        """Numbered notes; write the numbers yourself. head=None uses the language's heading
        ('Hinweise' / 'Notes'), head='' leaves it out. Returns the y below the block."""
        head = self.T["notes"] if head is None else head
        if head:
            self.text(x, y, head, h=3.5, ha="left")
            y -= 3.5 * lead
        for ln in lines:
            self.text(x, y, ln, h=h, ha="left")
            y -= h * lead
        return y

    @_annotation("annot")
    def view_label(self, x, y, s, h=5.0):
        self.text(x, y, s, h=h)

    # --- surface texture symbol ISO 21920-1 ------------------------------------------------
    @_annotation("annot")
    def rough(self, tip, value="", rot=0.0, mrr=True, h=H, extra=""):
        """Surface texture symbol placed directly on the surface; tip on the surface,
        symbol above it (rot=0). rot=90: symbol left of the surface, read from the right."""
        tip = np.asarray(tip, float)
        value, extra = self._dec(value), self._dec(extra)
        H1, H2 = 1.4 * h, 2.8 * h + 0.7
        k = 1 / math.tan(math.radians(60))
        R = lambda p: tip + _rot(p, rot)  # noqa: E731
        a, b = R((-H1 * k, H1)), R((H2 * k, H2))
        self.line([a, tip, b], "thin")
        if mrr:
            self.seg(a, R((H1 * k, H1)), "thin")
        if value:
            xs = (H1 + 0.6 + h) * k + 0.7
            xe = max(H2 * k + 1.0, xs + text_width(value, h) + 1.0)
            self.seg(b, R((xe, H2)), "thin")
            p = R((xs, H1 + 0.6))
            self.text(p[0], p[1], value, h=h, ha="left", rot=rot)
        if extra:
            p = R((H2 * k + 0.8, H2 + 0.8))
            self.text(p[0], p[1], extra, h=h * 0.8, ha="left", rot=rot)

    @_annotation("annot")
    def rough_leader(self, target, knee, value, length=None, mrr=True):
        """Surface texture requirement on a leader line with an arrow onto the surface."""
        target, knee = np.asarray(target, float), np.asarray(knee, float)
        self.seg(target, knee, "thin")
        self.arrow(target, target - knee)
        H1 = 1.4 * H
        k = 1 / math.tan(math.radians(60))
        right = knee[0] >= target[0]
        L = length or max(12.0, text_width(self._dec(value), H) + 9.0)
        end = knee + np.array([L if right else -L, 0])
        self.seg(knee, end, "thin")
        tip = knee + np.array([H1 * k + 1.0 if right else -(L - H1 * k - 1.0), 0])
        self.rough(tip, value, mrr=mrr)

    @_annotation("annot")
    def general_surface(self, x, y, value, others=True):
        """General surface texture note beside the title block: value plus ( v ) for deviating surfaces."""
        h = 5.0
        self.rough((x, y), value, h=h)
        xo = x + 2.8 * h * 0.577 + text_width(self._dec(value), h) + 8
        if others:
            self.text(xo, y + 2.5, "(", h=9, ha="left")
            self.rough((xo + 6.0, y + 1.5), "", h=3.5)
            self.text(xo + 12.0, y + 2.5, ")", h=9, ha="left")
        self._regions.append(((x - 5.0, y - 0.5, xo + (17.0 if others else -6.0), y + 16.0),
                              "general surface texture note", self._group))

    # --- geometrical tolerancing ISO 1101, datums ISO 5459 ------------------------------
    def gsym(self, kind, c, s=H):
        """Tolerance symbol centred on c, size s (roughly the cap height)."""
        c = np.asarray(c, float)
        L = lambda pts: self.line([c + np.array(p) * s for p in pts], "thin")  # noqa: E731
        r = 0.5
        if kind == "straightness":
            L([(-0.6, 0), (0.6, 0)])
        elif kind == "flatness":
            L([(-0.65, -0.3), (0.35, -0.3), (0.65, 0.3), (-0.35, 0.3), (-0.65, -0.3)])
        elif kind == "circularity":
            self.circle(c, r * s, "thin")
        elif kind == "cylindricity":
            self.circle(c, 0.38 * s, "thin")
            L([(-0.55, -0.55), (0.1, 0.6)])
            L([(-0.1, -0.6), (0.55, 0.55)])
        elif kind == "profile_line":
            t = np.radians(np.linspace(0, 180, 30))
            L([(0.55 * math.cos(a), -0.3 + 0.55 * math.sin(a)) for a in t])
        elif kind == "profile_surface":
            t = np.radians(np.linspace(0, 180, 30))
            L([(0.55 * math.cos(a), -0.3 + 0.55 * math.sin(a)) for a in t] + [(0.55, -0.3)])
        elif kind == "parallelism":
            L([(-0.55, -0.5), (-0.05, 0.5)])
            L([(0.05, -0.5), (0.55, 0.5)])
        elif kind == "perpendicularity":
            L([(-0.6, -0.45), (0.6, -0.45)])
            L([(0, -0.45), (0, 0.6)])
        elif kind == "angularity":
            L([(0.6, -0.45), (-0.6, -0.45), (0.45, 0.5)])
        elif kind == "position":
            self.circle(c, 0.35 * s, "thin")
            L([(-0.6, 0), (0.6, 0)])
            L([(0, -0.6), (0, 0.6)])
        elif kind == "coaxiality":
            self.circle(c, 0.25 * s, "thin")
            self.circle(c, 0.5 * s, "thin")
        elif kind == "symmetry":
            L([(-0.4, 0.35), (0.4, 0.35)])
            L([(-0.65, 0), (0.65, 0)])
            L([(-0.4, -0.35), (0.4, -0.35)])
        elif kind in ("runout", "total_runout"):
            if kind == "runout":
                a, b = c + np.array([-0.4, -0.5]) * s, c + np.array([0.4, 0.5]) * s
                self.seg(a, b, "thin")
                self.arrow(b, b - a, length=0.45 * s, half=0.18 * s)
            else:
                for dx in (-0.35, 0.25):
                    a, b = c + np.array([dx - 0.25, -0.45]) * s, c + np.array([dx + 0.25, 0.5]) * s
                    self.seg(a, b, "thin")
                    self.arrow(b, b - a, length=0.4 * s, half=0.16 * s)
                L([(-0.6, -0.45), (0.5, -0.45)])
        else:
            raise ValueError(f"unknown tolerance '{kind}'; use one of straightness, flatness, "
                             "circularity, cylindricity, profile_line, profile_surface, "
                             "parallelism, perpendicularity, angularity, position, coaxiality, "
                             "symmetry, runout, total_runout")

    @_annotation("dim")
    def fcf(self, x, y, kind, tol_value, datums=(), h=H):
        """Feature control frame, lower left corner at (x, y). Returns the box (x0, y0, x1, y1)."""
        tol_value = self._dec(tol_value)
        hh = 2 * h
        cells = [hh, text_width(tol_value, h) + 2.4] + [max(hh, text_width(d, h) + 2.4) for d in datums]
        xs = np.cumsum([x] + cells)
        self.line([(x, y), (xs[-1], y), (xs[-1], y + hh), (x, y + hh), (x, y)], "thin")
        for xv in xs[1:-1]:
            self.seg((xv, y), (xv, y + hh), "thin")
        self.gsym(kind, (x + hh / 2, y + hh / 2), s=h)
        self.text(xs[1] + 1.2, y + (hh - h) / 2, tol_value, h=h, ha="left")
        for i, d in enumerate(datums):
            self.text((xs[2 + i] + xs[3 + i]) / 2, y + (hh - h) / 2, d, h=h)
            self._datum_refs += [(L_, (x, y, xs[-1], y + hh)) for L_ in re.findall(r"[A-Z]", d)]
        return (x, y, xs[-1], y + hh)

    @_annotation("dim")
    def fcf_leader(self, box, target, side="left", via=None, arrow=True):
        """Leader from the feature control frame to the toleranced feature (arrow on surface or dimension line)."""
        x0, y0, x1, y1 = box
        hh = y1 - y0
        start = {"left": (x0, (y0 + y1) / 2), "right": (x1, (y0 + y1) / 2),
                 "bottom": (x0 + hh / 2, y0), "top": (x0 + hh / 2, y1)}[side]
        pts = [start] + ([via] if via is not None else []) + [target]
        self.line(pts, "thin")
        if arrow:
            self.arrow(target, np.asarray(target) - np.asarray(pts[-2]))

    @_annotation("dim")
    def datum(self, letter, foot, direction, length=7.0, h=H):
        """Datum triangle on the feature (foot), connecting line, datum letter in a square frame."""
        d = _unit(direction)
        n = np.array([-d[1], d[0]])
        foot = np.asarray(foot, float)
        a = 1.6
        self.poly([foot + n * a, foot - n * a, foot + d * a * 1.7])
        box_c = foot + d * (a * 1.7 + length + h)
        self.seg(foot + d * a * 1.7, box_c - d * h, "thin")
        s = h
        self.line([box_c + (-s, -s), box_c + (s, -s), box_c + (s, s), box_c + (-s, s), box_c + (-s, -s)],
                  "thin")
        self.text(box_c[0], box_c[1] - h / 2, letter, h=h)
        self._datums.append((letter, (box_c[0] - s, box_c[1] - s, box_c[0] + s, box_c[1] + s)))

    # --- dimensioning ISO 129-1 ---------------------------------------------------------------
    def _dim_text(self, q1, q2, text, h, tshift=0.0, tside=None, tol_=None, box=False):
        u = _unit(q2 - q1) if np.linalg.norm(q2 - q1) > 1e-9 else np.array([1.0, 0.0])
        ang = math.degrees(math.atan2(u[1], u[0]))
        if ang > 90.01 or ang <= -89.99:                 # readable from below or from the right
            ang -= 180 if ang > 0 else -180
        tu = _rot((1, 0), ang)
        tn = np.array([-tu[1], tu[0]])
        mid = (q1 + q2) / 2 + tu * tshift
        if tside == "below":
            tn = -tn
        tw = text_width(text, h)
        pos = mid + tn * (1.0 if tside != "below" else 1.0 + h)
        self.text(pos[0], pos[1], text, h=h, rot=ang, ha="center")
        if box:
            c = pos + tn * h / 2
            hw, hh = tw / 2 + 0.9, h / 2 + 0.9
            self.line([c + tu * sx * hw + tn * sy * hh for sx, sy in
                       ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))], "thin")
        if tol_ is not None:
            up, lo = (self._dec(v) for v in tol_)
            st = pos + tu * (tw / 2 + 0.6)
            self.text(*(st + tn * (h * 0.78)), up, h=h * 0.68, rot=ang, ha="left")
            self.text(*st, lo, h=h * 0.68, rot=ang, ha="left")

    @_annotation("dim")
    def dim(self, p1, p2, off, text, orient="h", outside=False, tshift=0.0, tol=None, box=False,
            ext1=True, ext2=True, h=H, tside=None, half=False):
        """Linear dimension between p1 and p2 (sheet coordinates). off: offset of the dimension
        line in mm (positive = left of the direction p1->p2, i.e. above/left).
        orient: 'h', 'v' or 'a' (parallel to the measured length). tol=("+0,05", "0").
        half=True: half dimension for a half section or half view of a symmetric part - only
        the p2 end is drawn, the dimension line ends just past the axis (ISO 129-1)."""
        p1, p2 = np.asarray(p1, float), np.asarray(p2, float)
        if orient == "h":
            d = np.array([1.0, 0.0]) if p2[0] >= p1[0] else np.array([-1.0, 0.0])
        elif orient == "v":
            d = np.array([0.0, 1.0]) if p2[1] >= p1[1] else np.array([0.0, -1.0])
        else:
            d = _unit(p2 - p1)
        n = np.array([-d[1], d[0]])
        q1 = p1 + n * off
        q2 = q1 + d * np.dot(p2 - p1, d)
        if half:
            mid = (q1 + q2) / 2 - d * 4.0
            self.seg(p2, q2 + n * (1 if off >= 0 else -1) * 2.0, "thin")
            self.seg(mid, q2, "thin")
            self.arrow(q2, d)
            self._dim_text(mid, q2, self._dec(text), h, tshift, tside, tol, box)
            return mid, q2
        for p, q, e in ((p1, p1 + n * off, ext1), (p2, q2, ext2)):
            if e and np.linalg.norm(q - p) > 0.3:
                self.seg(p, q + n * (1 if off >= 0 else -1) * 2.0, "thin")
        L = np.linalg.norm(q2 - q1)
        u = _unit(q2 - q1) if L > 1e-9 else d
        if outside:
            self.seg(q1 - u * 7, q2 + u * 7, "thin")
            self.arrow(q1, u)
            self.arrow(q2, -u)
        else:
            self.seg(q1, q2, "thin")
            self.arrow(q1, -u)
            self.arrow(q2, u)
        self._dim_text(q1, q2, self._dec(text), h, tshift, tside, tol, box)
        return q1, q2

    def hdim(self, p1, p2, y, text, **kw):
        """Horizontal dimension; the dimension line sits at sheet height y."""
        p1, p2 = sorted([np.asarray(p1, float), np.asarray(p2, float)], key=lambda q: q[0])
        return self.dim(p1, p2, y - p1[1], text, "h", **kw)

    def vdim(self, p1, p2, x, text, **kw):
        """Vertical dimension; dimension line at sheet position x, text left of it, read from the right."""
        p1, p2 = sorted([np.asarray(p1, float), np.asarray(p2, float)], key=lambda q: q[1])
        return self.dim(p1, p2, p1[0] - x, text, "v", **kw)

    @_annotation("dim")
    def dim_angle(self, c, r, a0, a1, text, h=H, box=False, ext=None):
        """Angular dimension about vertex c (sheet), radius r, from a0 to a1 in degrees, counter-clockwise."""
        c = np.asarray(c, float)
        self.arc(c, r, a0, a1, "thin")
        for a, sgn in ((a0, -1), (a1, 1)):
            t = math.radians(a)
            p = c + r * np.array([math.cos(t), math.sin(t)])
            self.arrow(p, np.array([-math.sin(t), math.cos(t)]) * sgn)
        if ext:
            for a, (r0, r1) in zip((a0, a1), ext):
                t = math.radians(a)
                e = np.array([math.cos(t), math.sin(t)])
                self.seg(c + e * r0, c + e * (r1 + 2), "thin")
        am = math.radians((a0 + a1) / 2)
        e = np.array([math.cos(am), math.sin(am)])
        tw = text_width(text, h)
        cc = c + e * (r + 2.0) + np.array([e[0] * (tw / 2 + 0.5), e[1] * (h / 2 + 0.5)])
        self.text(cc[0], cc[1] - h / 2, text, h=h)
        if box:
            hw, hh = tw / 2 + 0.9, h / 2 + 0.9
            self.line([cc + (sx * hw, sy * hh) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))],
                      "thin")

    @_annotation("dim")
    def rdim(self, c, r, angle, text, h=H, outside=None, to_centre=False, concave=False):
        """Radius dimension (ISO 129-1): dimension line along `angle` (degrees) from the
        centre c towards the arc of sheet radius r, one arrow on the arc. Text e.g. "R5".
        outside=True (automatic for small radii): arrow outside, pointing at the arc.
        concave=True for fillets whose centre lies in free space: the line comes from beyond
        the centre, the text sits there, the arrow touches the arc from inside."""
        c = np.asarray(c, float)
        e = _rot((1, 0), angle)
        p = c + e * r
        text = self._dec(text)
        tw = text_width(text, h)
        if concave:
            start = c - e * (tw + 7)
            self.seg(start, p, "thin")
            self.arrow(p, e)
            self._dim_text(start, c - e * 2, text, h)
            return
        if outside is None:
            outside = r < tw + 7
        if not outside:
            start = c if to_centre else c + e * max(0.0, r - tw - 8)
            self.seg(start, p, "thin")
            self.arrow(p, e)
            self._dim_text(start, p, text, h)
        else:
            q = p + e * (tw + 7)
            self.seg(p, q, "thin")
            self.arrow(p, -e)
            self._dim_text(p + e * 4, q, text, h)

    @_annotation("dim")
    def ddim(self, c, r, angle, text, h=H, outside=None, box=False, tpos=0.5):
        """Diameter dimension across a circle seen as a circle: line through the centre at
        `angle` (degrees), arrows on both sides. r is the sheet radius. Text e.g. "Ø20 H7".
        box=True frames the value (theoretically exact, e.g. a pitch circle).
        tpos: where the value sits between centre (0) and circle (1), e.g. to keep it clear
        of a bore."""
        c = np.asarray(c, float)
        e = _rot((1, 0), angle)
        p1, p2 = c - e * r, c + e * r
        text = self._dec(text)
        tw = text_width(text, h)
        if outside is None:
            outside = 2 * r < tw + 8
        if not outside:
            # tpos > 1 puts the value outside the part; the dimension line runs on to it
            end = c + e * max(r, r * tpos + tw / 2 + 1.0)
            self.seg(p1, end, "thin")
            self.arrow(p1, -e)
            self.arrow(p2, e)
            self._dim_text(c + e * (r * tpos - 1), c + e * (r * tpos + 1), text, h, box=box)
        else:
            q = p2 + e * (tw + 7)
            self.seg(p1 - e * 6, q, "thin")
            self.arrow(p1, e)
            self.arrow(p2, -e)
            self._dim_text(p2 + e * 4, q, text, h, box=box)

    @_annotation("dim")
    def leader_text(self, target, knee, text, h=H, arrow=True, dot=False, under=None):
        """Leader line with the text on a horizontal reference line."""
        target, knee = np.asarray(target, float), np.asarray(knee, float)
        text, under = self._dec(text), self._dec(under)
        self.seg(target, knee, "thin")
        if arrow:
            self.arrow(target, target - knee)
        if dot:
            self.dot(target, 0.5)
        right = knee[0] >= target[0]
        w = max(text_width(text, h), text_width(under, h) if under else 0) + 1.5
        end = knee + np.array([w if right else -w, 0])
        self.seg(knee, end, "thin")
        x = knee[0] + 0.8 if right else end[0] + 0.8
        self.text(x, knee[1] + 0.9, text, h=h, ha="left")
        if under:
            self.text(x, knee[1] - h - 0.9, under, h=h, ha="left")

    @_annotation("annot")
    def posnum(self, target, at, num, h=5.0):
        """Item number (ISO 6433): dot inside the part, leader line, number."""
        target, at = np.asarray(target, float), np.asarray(at, float)
        self.seg(target, at, "thin")
        self.dot(target, 0.55)
        d = _unit(at - target)
        p = at + d * 1.0
        ha = "left" if d[0] > 0.3 else ("right" if d[0] < -0.3 else "center")
        va = "bottom" if d[1] > 0.3 else ("top" if d[1] < -0.3 else "center")
        self.text(p[0], p[1], str(num), h=h, ha=ha, va=va)

    @_annotation("annot")
    def cutting_plane(self, a, b, letter, look):
        """Cutting plane: thick ends on a long-dash-dot line, arrows in the viewing direction, letters."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        d = _unit(b - a)
        self.line([a, b], "center")
        look = _unit(look)
        for p, s in ((a, 1), (b, -1)):
            self.seg(p, p + d * s * 7, "xthick")
            q = p + d * s * 3.5
            self.seg(q, q + look * 6, "thin")
            self.arrow(q + look * 9, look, length=3.0, half=0.7)
            t = q + look * 12.5
            self.text(t[0], t[1], letter, h=5.0, va="center")

    @_annotation("annot")
    def detail_mark(self, c, r, letter):
        """Thin circle around the region shown enlarged, with its letter (ISO 128-34)."""
        c = np.asarray(c, float)
        self.circle(c, r, "thin")
        p = c + _rot((1, 0), 45) * (r + 1.5)
        self.text(p[0], p[1], letter, h=5.0, ha="left", va="bottom")

    # --- welds ISO 2553 ------------------------------------------------------------------
    @_annotation("dim")
    def weld(self, target, knee, kind="fillet", size="", length="", side="arrow",
             all_around=False, field=False, process=None, h=H, ref_len=None):
        """Weld symbol to ISO 2553 (system A, dashed identification line below).
        kind: 'fillet', 'I' (square butt), 'V' (single-V butt), 'HV' (single-bevel butt).
        side: 'arrow' (weld on the arrow side), 'other' or 'both' (symmetric weld).
        size e.g. "a4", length e.g. "100" or "3×50 (100)", process e.g. "135"."""
        target, knee = np.asarray(target, float), np.asarray(knee, float)
        size, length = self._dec(size), self._dec(length)
        self.seg(target, knee, "thin")
        self.arrow(target, target - knee)
        right = knee[0] >= target[0]
        s = 1.1 * h
        tl, tr = text_width(size, h), text_width(length, h)
        L = ref_len or max(22.0, tl + tr + s + 14)
        end = knee + np.array([L if right else -L, 0])
        self.seg(knee, end, "thin")
        y0 = knee[1]
        if side != "both":
            gap = 1.2
            xa, xb = sorted((knee[0], end[0]))
            self.line([(xa, y0 - gap), (xb, y0 - gap)], "hidden")
        # size - symbol - length, read from the left, placed next to the arrow line;
        # the tail (process) goes to the far end of the reference line
        gw = (tl + 1.0 if size else 0.0) + s + (1.0 + tr if length else 0.0)
        xl = knee[0] + 3.0 if right else knee[0] - 3.0 - gw
        xs = xl + (tl + 1.0 if size else 0.0)
        sides = {"arrow": [(y0, 1)], "other": [(y0 - 1.2, -1)], "both": [(y0, 1), (y0, -1)]}[side]
        for yb, sg in sides:
            if kind == "fillet":
                self.line([(xs, yb), (xs, yb + sg * s), (xs + s, yb), (xs, yb)], "thin")
            elif kind == "I":
                self.seg((xs, yb), (xs, yb + sg * s), "thin")
                self.seg((xs + 0.6 * s, yb), (xs + 0.6 * s, yb + sg * s), "thin")
            elif kind == "V":
                self.line([(xs, yb + sg * s), (xs + s / 2, yb), (xs + s, yb + sg * s)], "thin")
            elif kind == "HV":
                self.line([(xs, yb + sg * s), (xs, yb), (xs + s * 0.8, yb + sg * s)], "thin")
            else:
                raise ValueError("weld kind is 'fillet', 'I', 'V' or 'HV'")
            ty = yb + 0.7 if sg > 0 else yb - 0.7 - h
            if size:
                self.text(xl, ty, size, h=h, ha="left")
            if length:
                self.text(xs + s + 1.0, ty, length, h=h, ha="left")
        if all_around:
            self.circle(knee, 1.6, "thin")
        if field:
            sx = 1 if right else -1
            top = knee + np.array([0, 6.0])
            self.seg(knee, top, "thin")
            self.poly([top, top + np.array([sx * 3.5, -1.2]), top + np.array([0, -2.4])])
        if process:
            sx = 1 if right else -1
            self.seg(end, end + np.array([sx * 2.5, 2.5]), "thin")
            self.seg(end, end + np.array([sx * 2.5, -2.5]), "thin")
            self.text(end[0] + sx * 3.5, y0 - h / 2, process, h=h, ha="left" if right else "right")


# =====================================================================================
class View:
    """View of the 3D model: n points from the part towards the viewer, xdir is the model
    direction shown to the right, sheet-up is n x xdir.
    origin: sheet point of the model origin, scale: drawing scale (2.0 = 2:1).
    clip: None, ('rect', (x0, y0, x1, y1)) or ('circle', (cx, cy), r) in sheet mm -
    everything the view draws is cut to that region (detail and broken views)."""

    def __init__(self, sheet, origin, scale, n, xdir, clip=None):
        n, x = np.asarray(n, float), np.asarray(xdir, float)
        if n.shape != (3,) or x.shape != (3,):
            raise ValueError("n and xdir are 3D vectors, e.g. n=(0, -1, 0), xdir=(1, 0, 0); "
                             "drawlib.VIEWS has the standard ones")
        if np.linalg.norm(n) < 1e-12 or np.linalg.norm(x) < 1e-12:
            raise ValueError("n and xdir must not be zero vectors")
        if scale <= 0:
            raise ValueError("scale must be positive (2.0 means 2:1)")
        self.s, self.o, self.k = sheet, np.asarray(origin, float), float(scale)
        self.N, self.X = _unit(n), _unit(x)
        if abs(self.N @ self.X) > 1e-6:
            raise ValueError(f"xdir {tuple(xdir)} is not perpendicular to n {tuple(n)} "
                             f"(n·xdir = {self.N @ self.X:.3f}). xdir must lie in the view plane; "
                             "see drawlib.VIEWS or the table in references/drawlib_api.md")
        self.Y = np.cross(self.N, self.X)
        if abs(self.N[2]) < 1e-9 and self.Y[2] < -0.5:
            warnings.warn(f"view n={tuple(n)}, xdir={tuple(xdir)} shows the model upside down "
                          "(sheet-up is model -z). Reverse xdir.", DrawingWarning, stacklevel=2)
        if clip is None and not any(abs(self.k - s) < 1e-9 for s in SCALES):
            warnings.warn(f"scale {scale_text(self.k)} is not an ISO 5455 scale "
                          f"({', '.join(scale_text(s) for s in SCALES)})", DrawingWarning, stacklevel=2)
        self.clip = clip
        self.extent = [np.inf, np.inf, -np.inf, -np.inf]
        sheet._views.append(self)

    def uv(self, p3):
        p = np.asarray(p3, float)
        return np.array([p @ self.X, p @ self.Y])

    def P(self, p3):
        """3D model point -> sheet coordinates."""
        return self.o + self.k * self.uv(p3)

    def p(self, u, v=0.0):
        """View coordinates (model mm in the view plane) -> sheet coordinates."""
        return self.o + self.k * np.array([u, v], float)

    # --- output through the clip region ----------------------------------------------
    def _emit(self, pts, style, z=3, role="geom"):
        pts = np.asarray(pts, float)
        pieces = [pts] if self.clip is None else _clip_polyline(pts, self.clip)
        for pc in pieces:
            self.extent = [min(self.extent[0], pc[:, 0].min()), min(self.extent[1], pc[:, 1].min()),
                           max(self.extent[2], pc[:, 0].max()), max(self.extent[3], pc[:, 1].max())]
            self.s.line(pc, style, z, role=role)

    # --- hidden edges and sections --------------------------------------------------
    def _spurious_seams(self, shape):
        out = []
        for f in shape.faces():
            for e in f.edges():
                if not BRep_Tool.IsClosed_s(e.wrapped, f.wrapped):
                    continue
                try:
                    nrm = np.array(tuple(f.normal_at(e.center())))
                except Exception:
                    continue
                if abs(nrm @ self.N) > 0.03:
                    out.append(np.array([self.uv(tuple(e.position_at(t))) for t in np.linspace(0, 1, 25)]))
        return out

    @staticmethod
    def _edge_pts(e, k):
        if e.geom_type.name == "LINE":
            a, b = e.position_at(0), e.position_at(1)
            return np.array([[a.X, a.Y], [b.X, b.Y]])
        n = max(8, int(e.length * k / 0.4))
        return np.array([[q.X, q.Y] for q in (e.position_at(t) for t in np.linspace(0, 1, n))])

    def hlr(self, shapes):
        """Visible and hidden edges (view coordinates) for a list of solids."""
        shapes = [s for s in shapes if s is not None]
        if not shapes:
            return {"vis": [], "hid": []}
        comp = Compound(children=list(shapes)) if len(shapes) > 1 else shapes[0]
        seams = []
        for sh in shapes:
            seams += self._spurious_seams(sh)
        algo = HLRBRep_Algo()
        algo.Add(comp.wrapped)
        algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*self.N), gp_Dir(*self.X))))
        algo.Update()
        algo.Hide()
        h = HLRBRep_HLRToShape(algo)
        res = {}
        for key, names in (("vis", ("VCompound", "OutLineVCompound")), ("hid", ("HCompound", "OutLineHCompound"))):
            lines = []
            for nm in names:
                c = getattr(h, nm)()
                if c is None or c.IsNull():
                    continue
                for e in Compound(c).edges():
                    pts = self._edge_pts(e, self.k)
                    if self._on_seam(pts, seams):
                        continue
                    lines.append(pts)
            res[key] = lines
        return res

    @staticmethod
    def _on_seam(pts, seams, tol_=2e-3):
        if not seams:
            return False
        if len(pts) == 2:
            samples = [pts[0] + (pts[1] - pts[0]) * t for t in (0.2, 0.5, 0.8)]
        else:
            samples = [pts[int(len(pts) * t)] for t in (0.2, 0.5, 0.8)]
        for sp in seams:
            ok = True
            for q in samples:
                a, b = sp[:-1], sp[1:]
                ab = b - a
                tt = np.clip(np.einsum("ij,ij->i", q - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-12), 0, 1)
                if np.min(np.linalg.norm(a + ab * tt[:, None] - q, axis=1)) > tol_:
                    ok = False
                    break
            if ok:
                return True
        return False

    def draw(self, shapes, hidden=False, hidden_skip=None, thin_if=None):
        """Visible edges thick; hidden=True adds dashed hidden edges."""
        r = self.hlr(list(shapes))
        if not r["vis"]:
            warnings.warn(f"view n={tuple(np.round(self.N, 3))} shows no visible edge: the solids "
                          "may be empty or None. n must point FROM the part TO the viewer.",
                          DrawingWarning, stacklevel=2)
        for pts in r["vis"]:
            st = "thin" if thin_if is not None and thin_if(pts) else "thick"
            self._emit(self.o + self.k * pts, st)
        if hidden:
            for pts in r["hid"]:
                if hidden_skip and hidden_skip(pts):
                    continue
                self._emit(self.o + self.k * pts, "hidden")
        return r

    def _halfspace(self, solid, d, sign):
        """Big box filling the half space sign·(p·n) >= sign·d around the solid."""
        bb = solid.bounding_box()
        R = float(np.linalg.norm(np.maximum(np.abs(tuple(bb.min)), np.abs(tuple(bb.max)))))
        L = 4 * R + 100.0
        pl = Plane(origin=tuple(self.N * (d + sign * L / 2)), x_dir=tuple(self.X), z_dir=tuple(self.N))
        return pl * Box(L, L, L)

    def cut(self, solid, d=0.0):
        """The solid with everything between the viewer and the plane p·n = d removed -
        ready for section(). d = n · (any point of the cutting plane)."""
        return solid - self._halfspace(solid, d, +1)

    def removed_section(self, solid, d=0.0, angle=45.0, spacing=2.0):
        """Removed section (ISO 128-44, 'Profilschnitt'): only the cut face in the plane
        p·n = d, nothing behind it - e.g. a keyway section of a shaft."""
        slab = solid - self._halfspace(solid, d, +1) - self._halfspace(solid, d - 0.05, -1)
        segs = self.cut_faces(slab, d)
        if not segs:
            warnings.warn(f"removed_section: the plane p·n = {d:g} does not cut the solid",
                          DrawingWarning, stacklevel=2)
            return
        self.hatch(segs, angle, spacing)
        for a, b in segs:
            self._emit([a, b], "thick", 4)

    def cut_faces(self, shape, d, tol_=1e-4, grouped=False):
        """Cut faces of a sectioned solid in the plane p.N = d, as a list of segments (sheet).
        grouped=True: one segment list per face."""
        if grouped:
            out = []
            for fc in shape.faces():
                s = self.cut_faces(fc, d, tol_)
                if s:
                    out.append(s)
            return out
        segs = []
        for f in shape.faces():
            if f.geom_type.name != "PLANE":
                continue
            nrm = np.array(tuple(f.normal_at(f.center())))
            if abs(abs(nrm @ self.N) - 1) > 1e-6:
                continue
            if abs(np.array(tuple(f.center())) @ self.N - d) > tol_:
                continue
            for e in f.edges():
                ts = np.linspace(0, 1, 2) if e.geom_type.name == "LINE" else np.linspace(0, 1, 48)
                pts = [self.P(tuple(e.position_at(t))) for t in ts]
                segs += list(zip(pts[:-1], pts[1:]))
        return segs

    def _plane_hint(self, shape):
        vals = sorted({round(float(np.array(tuple(f.center())) @ self.N), 3) for f in shape.faces()
                       if f.geom_type.name == "PLANE"
                       and abs(abs(np.array(tuple(f.normal_at(f.center()))) @ self.N) - 1) < 1e-6})
        return ", ".join(f"{v:g}" for v in vals[:8]) or "none"

    def hatch(self, segs, angle=45.0, spacing=2.0, offset=0.0):
        hatch(self.s, segs, angle, spacing, offset,
              emit=lambda pts: self._emit(pts, "thin", 2, role="hatch"))

    def section(self, items, d=0.0, background=()):
        """Section view: items = [(sectioned solid, hatch angle, hatch spacing), ...];
        cut the solids with View.cut() first. hatch angle None leaves a face blank (or use
        'solid' to blacken thin sections). background: solids drawn uncut (shafts, screws)."""
        self.draw([it[0] for it in items] + list(background))
        for i, (sh, ang, sp) in enumerate(items):
            segs = self.cut_faces(sh, d)
            if not segs:
                warnings.warn(f"section item {i}: no cut face lies in the plane p·n = {d:g}. Faces "
                              f"perpendicular to n lie at p·n = {self._plane_hint(sh)}. Was the solid "
                              "cut (View.cut) and is d the plane you cut at?", DrawingWarning,
                              stacklevel=2)
                continue
            if ang == "solid":
                self._fill(segs)
            elif ang is not None:
                self.hatch(segs, ang, sp)
            for a, b in segs:
                self._emit([a, b], "thick", 4)

    def _fill(self, segs):
        """Blacken thin cut faces (shims, gaskets, sheet metal) by dense hatching."""
        self.hatch(segs, 45.0, 0.25)

    # --- special views --------------------------------------------------------------
    def detail(self, center, radius, at, scale, letter, frame=True):
        """Detail view (ISO 128-34): marks a circle of `radius` (model mm) around the view
        point `center` = (u, v) in this view and returns a new View at sheet point `at`,
        enlarged to `scale` and clipped to the circle. Draw into it with draw()/section()
        exactly as into this view."""
        c = self.p(*center)
        self.s.detail_mark(c, radius * self.k, letter)
        at = np.asarray(at, float)
        R = radius * scale
        v = View(self.s, at - scale * np.asarray(center, float), scale, self.N, self.X,
                 clip=("circle", tuple(at), R))
        with self.s._ann("annot"):
            if frame:
                self.s.circle(at, R, "thin")
            self.s.text(at[0], at[1] + R + 3.0, f"{letter} ({scale_text(scale)})", h=5.0)
        return v

    def half_section(self, parts, d=0.0, axis_v=0.0, side="upper", hidden=False, background=()):
        """Half section (ISO 128-44) of a symmetric part: one half of the view sectioned, the
        other half as a view, separated by the axis at view height axis_v.
        parts = [(uncut solid, hatch angle, hatch spacing), ...]."""
        ya = self.p(0, axis_v)[1]
        big = 1e5
        up = View(self.s, self.o, self.k, self.N, self.X, clip=("rect", (-big, ya, big, big)))
        lo = View(self.s, self.o, self.k, self.N, self.X, clip=("rect", (-big, -big, big, ya)))
        sec, vw = (up, lo) if side == "upper" else (lo, up)
        sec.section([(self.cut(s, d), a, sp) for s, a, sp in parts], d=d, background=background)
        vw.draw([s for s, _, _ in parts] + list(background), hidden=hidden)
        for v in (up, lo):
            self.extent = [min(self.extent[0], v.extent[0]), min(self.extent[1], v.extent[1]),
                           max(self.extent[2], v.extent[2]), max(self.extent[3], v.extent[3])]
        return sec, vw


class BrokenView:
    """Long part drawn shortened (ISO 128-34 interrupted view). breaks = [(u0, u1), ...] are
    the view ranges (model mm along xdir) left out; each is replaced by a `gap` mm wide break
    on the sheet. p(u, v) maps true view coordinates, so dimensions get the true positions -
    write the true length as their text."""

    def __init__(self, sheet, origin, scale, n, xdir, breaks, gap=8.0):
        self.s, self.k, self.gap = sheet, float(scale), gap
        self.breaks = sorted(breaks)
        o = np.asarray(origin, float)
        base = View(sheet, o, scale, n, xdir)
        sheet._views.remove(base)
        self.N, self.X, self.Y = base.N, base.X, base.Y
        self.views, self.ranges, self.cuts = [], [], []
        shift, u_prev = 0.0, -np.inf
        big = 1e5
        for u0, u1 in self.breaks + [(np.inf, np.inf)]:
            org = o - np.array([shift, 0.0])
            x_lo = -big if u_prev == -np.inf else org[0] + u_prev * self.k
            x_hi = big if u0 == np.inf else org[0] + u0 * self.k
            self.views.append(View(sheet, org, scale, n, xdir, clip=("rect", (x_lo, -big, x_hi, big))))
            self.ranges.append((u_prev, u0))
            if u0 != np.inf:
                self.cuts.append((x_hi, x_hi + gap))
                shift += (u1 - u0) * self.k - gap
            u_prev = u1

    def _view_for(self, u):
        for v, (a, b) in zip(self.views, self.ranges):
            if a <= u <= b:
                return v, u
        for v, (a, b) in zip(self.views, self.ranges):        # inside a break: nearest edge
            if u < a:
                return v, a
        return self.views[-1], u

    def p(self, u, v=0.0):
        vw, uu = self._view_for(u)
        return vw.p(uu, v)

    def P(self, p3):
        uv = np.array([np.asarray(p3, float) @ self.X, np.asarray(p3, float) @ self.Y])
        return self.p(*uv)

    def cut(self, solid, d=0.0):
        return self.views[0].cut(solid, d)

    def _breaklines(self):
        ys = [(v.extent[1], v.extent[3]) for v in self.views if np.isfinite(v.extent[1])]
        if not ys:
            return
        y0, y1 = min(a for a, _ in ys) - 2.0, max(b for _, b in ys) + 2.0
        for xa, xb in self.cuts:
            self.s.break_line((xa, y0), (xa, y1))
            self.s.break_line((xb, y0), (xb, y1))

    def draw(self, shapes, hidden=False):
        for v in self.views:
            v.draw(shapes, hidden=hidden)
        self._breaklines()

    def section(self, items, d=0.0, background=()):
        for v in self.views:
            v.section(items, d=d, background=background)
        self._breaklines()


def _thread(view, a, b, d_nom, d_core, internal):
    """Thread between view points a=(u, v) and b on its axis (ISO 6410): thin line at the
    thread root, thick thread-end line at b. Model mm."""
    S = view.s
    pa, pb = view.p(*a), view.p(*b)
    u = _unit(pb - pa)
    n = np.array([-u[1], u[0]])
    with S._ann("annot"):
        r_thin = (d_nom if internal else d_core) / 2 * view.k
        for sg in (1, -1):
            view._emit([pa + n * sg * r_thin, pb + n * sg * r_thin], "thin", 3, role="annot")
        r = d_nom / 2 * view.k
        view._emit([pb + n * r, pb - n * r], "thick", 3, role="geom")


def _thread_end(view, c, d, internal=True):
    """Thread seen from the end: thin three-quarter circle at the nominal Ø (internal) or at
    the root Ø (external, pass the core diameter)."""
    with view.s._ann("annot"):
        view.s.arc(view.p(*c), d / 2 * view.k, 95, 355, "thin")


View.thread = lambda self, a, b, d_nom, d_core, internal=False: _thread(self, a, b, d_nom, d_core, internal)
View.thread.__doc__ = _thread.__doc__
View.thread_end = lambda self, c, d, internal=True: _thread_end(self, c, d, internal)
View.thread_end.__doc__ = _thread_end.__doc__


# =====================================================================================
# sheet check
# =====================================================================================
def _segments(sheet, roles, styles_skip=("center", "phantom")):
    A, B, G, R = [], [], [], []
    for ln in sheet.ax.lines:
        gid = ln.get_gid() or ""
        parts = gid.split("|")
        if len(parts) != 3 or parts[1] not in roles or parts[0] in styles_skip:
            continue
        xy = ln.get_xydata()
        if len(xy) < 2:
            continue
        A.append(xy[:-1])
        B.append(xy[1:])
        G += [int(parts[2])] * (len(xy) - 1)
        R += [parts[1]] * (len(xy) - 1)
    if not A:
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0, int), np.array([])
    return np.vstack(A), np.vstack(B), np.array(G), np.array(R)


def _hits(A, B, box):
    lo, hi = np.minimum(A, B), np.maximum(A, B)
    cand = np.nonzero((lo[:, 0] <= box[2]) & (hi[:, 0] >= box[0]) &
                      (lo[:, 1] <= box[3]) & (hi[:, 1] >= box[1]))[0]
    out = []
    for i in cand:
        iv = _seg_rect(A[i], B[i], box)
        if iv and iv[1] - iv[0] > 1e-6:
            out.append(i)
    return out


def _overlap(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > 0 and min(a[3], b[3]) - max(a[1], b[1]) > 0


def _shrink(b, m):
    return (b[0] + m, b[1] + m, b[2] - m, b[3] - m)


def _check(self, verbose=True):
    """Look for what reviewers reject: overlapping texts, texts over contours or in the title
    block, geometry outside the frame, datums referenced but not shown, unknown or invalid
    fits, missing title block entries, non-standard scales. Returns a list of Issue."""
    out = []

    def add(level, msg, box=None):
        g = self.grid_ref((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) if box else ""
        out.append(Issue(level, msg, box, g))

    texts = []
    for t in self._texts:
        if t["role"] == "frame" or not t["s"].strip():
            continue
        b = text_box(t["x"], t["y"], t["s"], t["h"], t["ha"], t["va"], t["rot"])
        if b:
            texts.append(dict(t, box=b))
    F = (self.fl, self.fb, self.fr, self.ft)
    # texts outside the frame
    for t in texts:
        b = t["box"]
        if b[0] < F[0] - 0.05 or b[1] < F[1] - 0.05 or b[2] > F[2] + 0.05 or b[3] > F[3] + 0.05:
            add("error", f'text "{t["s"]}" runs outside the drawing frame', b)
    # texts on top of each other
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a, b = texts[i], texts[j]
            if a["group"] and a["group"] == b["group"]:
                continue
            if _overlap(_shrink(a["box"], 0.15), _shrink(b["box"], 0.15)):
                box = (min(a["box"][0], b["box"][0]), min(a["box"][1], b["box"][1]),
                       max(a["box"][2], b["box"][2]), max(a["box"][3], b["box"][3]))
                add("error", f'texts "{a["s"]}" and "{b["s"]}" overlap', box)
    # texts inside the title block, parts list or a table they do not belong to
    for rect, name, grp in self._regions:
        for t in texts:
            if t["group"] != grp and _overlap(_shrink(t["box"], 0.1), rect):
                add("error", f'text "{t["s"]}" lies inside the {name}', t["box"])
    # texts crossed by lines
    A, B, G, R = _segments(self, {"geom", "dim", "annot"})
    for t in texts:
        if t["role"] in ("tb", "table"):
            continue
        hit = [i for i in _hits(A, B, _shrink(t["box"], 0.12)) if not (t["group"] and G[i] == t["group"])]
        if any(R[i] == "geom" for i in hit):
            add("warning", f'text "{t["s"]}" is crossed by a part contour', t["box"])
        elif hit:
            add("warning", f'text "{t["s"]}" is crossed by another annotation line', t["box"])
    # geometry outside the frame or inside the title block / parts list / tables
    A, B, G, R = _segments(self, {"geom", "dim", "annot", "hatch"}, styles_skip=())
    if len(A):
        P = np.vstack([A, B])
        bad = (P[:, 0] < F[0] - 0.05) | (P[:, 0] > F[2] + 0.05) | (P[:, 1] < F[1] - 0.05) | (P[:, 1] > F[3] + 0.05)
        if bad.any():
            q = P[bad]
            add("error", "drawing content extends beyond the frame - smaller scale, larger "
                "sheet or move the view", (*q.min(0), *q.max(0)))
        for rect, name, grp in self._regions:
            idx = [i for i in _hits(A, B, _shrink(rect, 0.2)) if G[i] != grp]
            if idx:
                q = np.vstack([A[idx], B[idx]])
                add("error", f"{'view geometry' if 'geom' in set(R[idx]) else 'annotation'} "
                    f"runs into the {name}", (*q.min(0), *q.max(0)))
    # datums
    shown = [d for d, _ in self._datums]
    for letter in sorted(set(shown)):
        if shown.count(letter) > 1:
            add("error", f"datum {letter} is indicated {shown.count(letter)} times")
    for letter, box in self._datum_refs:
        if letter not in shown:
            add("error", f"a tolerance frame refers to datum {letter}, which is not indicated "
                "on this sheet (Sheet.datum)", box)
    for letter, box in self._datums:
        if letter not in [L for L, _ in self._datum_refs]:
            add("info", f"datum {letter} is indicated but no tolerance frame uses it", box)
    # fits written in texts
    for t in texts:
        if t["role"] == "tb":
            continue
        for size, c1, c2 in tol.parse_fits(t["s"]):
            for code in (c1, c2):
                if not code:
                    continue
                try:
                    tol.deviations(size, code)
                except ValueError as e:
                    lvl = "info" if "built-in table" in str(e) else "error"
                    add(lvl, f'"{t["s"]}": {e}', t["box"])
            if c2:
                try:
                    tol.fit(size, c1, c2)
                except ValueError as e:
                    add("error", f'"{t["s"]}": {e}', t["box"])
    # title block
    if self._tb is None:
        add("error", "the sheet has no title block (Sheet.title_block)")
    else:
        tb = self._tb_rect
        if not self._tb.get("material"):
            add("warning", "title block: material is empty", tb)
        sc = str(self._tb.get("scale", ""))
        if not sc:
            add("error", "title block: scale is empty", tb)
        for a, b in re.findall(r"(\d+(?:[.,]\d+)?)\s*:\s*(\d+(?:[.,]\d+)?)", sc):
            k = float(a.replace(",", ".")) / float(b.replace(",", "."))
            if not any(abs(k - s) < 1e-9 for s in SCALES):
                add("warning", f"title block: scale {a}:{b} is not an ISO 5455 scale", tb)
        if not self._tb.get("mass"):
            add("info", "title block: mass is empty", tb)
    if not self._views:
        add("warning", "the sheet has no view")
    if verbose:
        self.report(out)
    return out


Sheet.check = _check


def _interrupt_hatching(self, margin=0.8):
    """ISO 128-50: hatching is interrupted where text is written inside a hatched area."""
    boxes = []
    for t in self._texts:
        if t["role"] in ("frame", "tb") or not t["s"].strip():
            continue
        b = text_box(t["x"], t["y"], t["s"], t["h"], t["ha"], t["va"], t["rot"])
        if b:
            boxes.append((b[0] - margin, b[1] - margin, b[2] + margin, b[3] + margin))
    if not boxes:
        return
    R = np.array(boxes)
    for ln in list(self.ax.lines):
        gid = ln.get_gid() or ""
        if "|hatch|" not in gid:
            continue
        xy = ln.get_xydata()
        if len(xy) != 2:
            continue
        a, b = xy
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        cand = R[(R[:, 0] <= hi[0]) & (R[:, 2] >= lo[0]) & (R[:, 1] <= hi[1]) & (R[:, 3] >= lo[1])]
        ivs = [iv for r in cand if (iv := _seg_rect(a, b, r))]
        if not ivs:
            continue
        lw, z = ln.get_linewidth(), ln.get_zorder()
        ln.remove()
        for t0, t1 in _complement(ivs):
            if t1 - t0 > 1e-3:
                p, q = a + (b - a) * t0, a + (b - a) * t1
                self.ax.plot([p[0], q[0]], [p[1], q[1]], color="k", lw=lw, zorder=z,
                             solid_capstyle="butt", gid=gid)


Sheet._interrupt_hatching = _interrupt_hatching


def views_layout(front_origin, gap, sizes, projection="first"):
    """Sheet origins for standard views around the front view.
    sizes: {view name: (width, height) on the sheet}, must include "front"; returns
    {view name: centre point on the sheet}. Placement follows ISO 5456-2 for the method."""
    fx, fy = front_origin
    fw, fh = sizes["front"]
    out = {"front": np.array([fx, fy], float)}
    for name, (w, h) in sizes.items():
        if name == "front" or name not in PLACEMENT[projection]:
            continue
        dx, dy = PLACEMENT[projection][name]
        out[name] = np.array([fx + dx * (fw / 2 + gap + w / 2), fy + dy * (fh / 2 + gap + h / 2)])
    return out
