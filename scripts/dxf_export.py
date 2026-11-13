"""DXF export of a drawlib sheet (needs ezdxf: pip install ezdxf).

Everything on the sheet is written to model space in mm, sorted into layers by line type:
visible edges, thin lines, hidden, centre, phantom, frame, hatching, text. Line widths are
set per layer (0,5 / 0,25 / 0,7 mm), text uses the style ISO with the font isocp.shx that
every AutoCAD-compatible program ships with. Raster images (logos) are not exported.
"""
import warnings

from matplotlib.image import AxesImage
from matplotlib.patches import Circle, Polygon

LAYERS = {  # name: (lineweight 1/100 mm, linetype)
    "VISIBLE": (50, "CONTINUOUS"), "THIN": (25, "CONTINUOUS"), "HIDDEN": (25, "DL_HIDDEN"),
    "CENTER": (25, "DL_CENTER"), "PHANTOM": (25, "DL_PHANTOM"), "FRAME": (70, "CONTINUOUS"),
    "HATCH": (25, "CONTINUOUS"), "TEXT": (25, "CONTINUOUS"),
}
_STYLE_LAYER = {"thick": "VISIBLE", "thin": "THIN", "xthick": "FRAME", "hidden": "HIDDEN",
                "hidden_thick": "HIDDEN", "center": "CENTER", "phantom": "PHANTOM"}
_SPECIAL = {"Ø": "%%c", "⌀": "%%c", "±": "%%p", "°": "%%d"}


def save_dxf(sheet, path):
    try:
        import ezdxf
        from ezdxf.enums import TextEntityAlignment as TA
    except ImportError as e:
        raise ImportError("DXF export needs ezdxf:  pip install ezdxf") from e
    import drawlib as D

    doc = ezdxf.new("R2010", units=4)                       # 4 = millimetres
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LTSCALE"] = 1.0
    doc.header["$LWDISPLAY"] = 1
    doc.linetypes.add("DL_HIDDEN", pattern=[4.5, 3.0, -1.5], description="Hidden __ __ __")
    doc.linetypes.add("DL_CENTER", pattern=[18.5, 14.0, -2.0, 0.5, -2.0],
                      description="Centre ____ _ ____")
    doc.linetypes.add("DL_PHANTOM", pattern=[21.0, 14.0, -2.0, 0.5, -2.0, 0.5, -2.0],
                      description="Phantom ____ _ _ ____")
    doc.styles.add("ISO", font="isocp.shx")
    for name, (lw, lt) in LAYERS.items():
        doc.layers.add(name, color=7, lineweight=lw, linetype=lt)
    msp = doc.modelspace()
    align = {("baseline", "left"): TA.LEFT, ("baseline", "center"): TA.CENTER,
             ("baseline", "right"): TA.RIGHT, ("bottom", "left"): TA.BOTTOM_LEFT,
             ("bottom", "center"): TA.BOTTOM_CENTER, ("bottom", "right"): TA.BOTTOM_RIGHT,
             ("center", "left"): TA.MIDDLE_LEFT, ("center", "center"): TA.MIDDLE_CENTER,
             ("center", "right"): TA.MIDDLE_RIGHT, ("top", "left"): TA.TOP_LEFT,
             ("top", "center"): TA.TOP_CENTER, ("top", "right"): TA.TOP_RIGHT}

    for ln in sheet.ax.lines:
        style, role, *_ = ((ln.get_gid() or "thin|annot|0").split("|") + ["", ""])[:3]
        layer = "HATCH" if role == "hatch" else _STYLE_LAYER.get(style, "THIN")
        msp.add_lwpolyline([tuple(p) for p in ln.get_xydata()], dxfattribs={"layer": layer})

    for p in sheet.ax.patches:
        if isinstance(p, Polygon):
            pts = [tuple(q) for q in p.get_xy()]
            h = msp.add_hatch(color=7, dxfattribs={"layer": "THIN"})
            h.paths.add_polyline_path(pts, is_closed=True)
        elif isinstance(p, Circle):
            msp.add_circle(p.center, p.radius, dxfattribs={"layer": "THIN"})
            h = msp.add_hatch(color=7, dxfattribs={"layer": "THIN"})
            h.paths.add_edge_path().add_arc(p.center, p.radius, 0, 360)

    for t in sheet.ax.texts:
        s = t.get_text()
        if not s.strip():
            continue
        for k, v in _SPECIAL.items():
            s = s.replace(k, v)
        h = t.get_fontsize() / D.fsize(1.0)
        va = t.get_verticalalignment()
        va = "baseline" if va == "center_baseline" else va
        e = msp.add_text(s, height=h, rotation=t.get_rotation(),
                         dxfattribs={"layer": "TEXT", "style": "ISO"})
        e.set_placement(t.get_position(), align=align[(va, t.get_horizontalalignment())])

    n_img = sum(isinstance(a, AxesImage) for a in sheet.ax.get_children())
    if n_img:
        warnings.warn(f"{n_img} raster image(s) (logo) not written to the DXF", D.DrawingWarning)
    doc.saveas(str(path))
    return path
