"""Library behaviour: argument checks, the sheet check, languages, title block, DXF."""
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build123d import Box, Cylinder  # noqa: E402

import drawlib as D  # noqa: E402


def tb(S, **kw):
    S.title_block(dict(title="Test", number="T-1", material="S235JR", mass="1 g", scale="1:1", **kw))


def levels(issues):
    return sorted((i.level, i.msg.split(" ")[0]) for i in issues if i.level != "info")


def test_view_rejects_non_perpendicular_xdir():
    S = D.Sheet()
    with pytest.raises(ValueError, match="not perpendicular"):
        D.View(S, (100, 150), 1.0, (0, -1, 0), (0, 1, 0))


def test_view_warns_upside_down_and_bad_scale():
    S = D.Sheet()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        D.View(S, (100, 150), 1.5, (0, -1, 0), (-1, 0, 0))
    msgs = " ".join(str(x.message) for x in w)
    assert "upside down" in msgs and "ISO 5455" in msgs


def test_unknown_sheet_and_language():
    with pytest.raises(ValueError):
        D.Sheet("A5")
    with pytest.raises(ValueError):
        D.Sheet("A4", lang="xx")


def test_clean_sheet_passes():
    S = D.Sheet("A4")
    V = D.View(S, (105, 180), 1.0, *D.VIEWS["front"])
    part = Box(60, 30, 40) - Cylinder(8, 100)
    V.section([(V.cut(part), 45, 2.5)])
    S.hdim(V.p(-30, -20), V.p(30, -20), 150, "60")
    tb(S)
    assert [i for i in S.check(verbose=False) if i.level == "error"] == []


def test_check_finds_problems():
    S = D.Sheet("A4")
    V = D.View(S, (105, 180), 1.0, *D.VIEWS["front"])
    V.draw([Box(60, 30, 40)])
    S.text(105, 180, "inside the part")                     # crossed by nothing, but...
    S.text(105, 180.5, "overlapping text")                   # ...overlaps this one
    S.text(105, 200, "crossing a contour", h=3.5)            # the top edge is at y = 200
    S.vdim(V.p(30, -20), V.p(30, 20), 150, "Ø10 H17")        # no IT17 in the table
    S.fcf(40, 250, "position", "Ø0.1", ["B"])                # datum B never indicated
    S.text(200, 30, "outside")                               # runs out of the frame
    tb(S)
    S.text(150, 40, "in the title block")
    found = " | ".join(i.msg for i in S.check(verbose=False))
    assert "overlap" in found
    assert "crossed by a part contour" in found
    assert "IT17" in found
    assert "datum B" in found
    assert "outside the drawing frame" in found
    assert "inside the title block" in found


def test_check_geometry_outside_and_missing_title_block():
    S = D.Sheet("A4")
    V = D.View(S, (20, 150), 1.0, *D.VIEWS["front"])
    V.draw([Box(60, 30, 40)])
    found = " | ".join(i.msg for i in S.check(verbose=False))
    assert "beyond the frame" in found and "no title block" in found


def test_section_warns_when_plane_misses():
    S = D.Sheet()
    V = D.View(S, (105, 150), 1.0, *D.VIEWS["front"])
    with pytest.warns(D.DrawingWarning, match="no cut face"):
        V.section([(V.cut(Box(20, 20, 20)), 45, 2)], d=5.0)


def test_english_third_angle_and_decimal():
    S = D.Sheet("A3", lang="en", projection="third")
    assert S.dec == "." and S.T["material"] == "Material"
    assert S._dec("0,02") == "0.02"
    assert D.Sheet("A4")._dec("0.02") == "0,02"
    tb(S)
    assert S._tb["doctype"] == "Part drawing"


def test_custom_title_block(tmp_path):
    lay = {"width": 120, "rows": [0, 10, 25],
           "cells": [{"row": 1, "x": [0, 80], "label": "title", "type": "title"},
                     {"row": 1, "x": [80, 120], "label": "number", "type": "number"},
                     {"row": 0, "x": [0, 60], "label": "Cost centre", "key": "cc"},
                     {"row": 0, "x": [60, 120], "label": "scale"}]}
    S = D.Sheet("A4")
    S.title_block(dict(title="T", number="N", scale="1:1", cc="4711"), layout=lay)
    texts = [t["s"] for t in S._texts]
    assert "Cost centre" in texts and "4711" in texts
    assert S._tb_rect[2] - S._tb_rect[0] == 120


def test_fit_tables_values():
    S = D.Sheet("A4")
    S.fit_table(20, 100, ["Ø20 g6"])
    S.fit_pair_table(20, 60, ["Ø20 H7/s6"])
    texts = [t["s"] for t in S._texts]
    assert "-0,007 / -0,020" in texts and "19,980" in texts
    assert "-0,014" in texts and "-0,048" in texts and "Übermaßpassung" in texts


def test_scale_text():
    assert D.scale_text(2) == "2:1" and D.scale_text(0.5) == "1:2" and D.scale_text(1) == "1:1"


def test_save_pdf_png_dxf(tmp_path):
    pytest.importorskip("ezdxf")
    S = D.Sheet("A4")
    V = D.View(S, (105, 180), 1.0, *D.VIEWS["front"])
    V.draw([Box(40, 20, 30)])
    tb(S)
    S.save(tmp_path / "t.pdf", png=tmp_path / "t.png", dxf=tmp_path / "t.dxf", quiet=True)
    for suffix in ("pdf", "png", "dxf"):
        assert (tmp_path / f"t.{suffix}").stat().st_size > 1000
    import ezdxf
    doc = ezdxf.readfile(tmp_path / "t.dxf")
    assert {"VISIBLE", "TEXT", "FRAME"} <= {e.dxf.layer for e in doc.modelspace()}
