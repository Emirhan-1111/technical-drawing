"""Every example renders and passes the sheet check without errors or warnings;
the STEP command line tool produces a sheet from a STEP file."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "examples"))

EXAMPLES = ["flanged_bush", "bearing_bracket", "stepped_shaft", "flange", "spur_gear",
            "weldment", "milled_block"]


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_is_clean(name, tmp_path):
    mod = importlib.import_module(name)
    if name == "milled_block" and not (ROOT / "examples" / "data" / "logo.png").exists():
        mod.logo(ROOT / "examples" / "data" / "logo.png")
    issues = mod.sheet().save(tmp_path / f"{name}.pdf", quiet=True)
    bad = [str(i) for i in issues if i.level in ("error", "warning")]
    assert bad == [], "\n".join(bad)
    assert (tmp_path / f"{name}.pdf").stat().st_size > 5000


def test_english_variant_is_clean(tmp_path):
    import flanged_bush
    issues = flanged_bush.sheet("en").save(tmp_path / "en.pdf", quiet=True)
    assert [i for i in issues if i.level in ("error", "warning")] == []


@pytest.mark.parametrize("args", [["--section"], ["--lang", "en", "--projection", "third", "--units", "in"]])
def test_step2drawing(tmp_path, args):
    from build123d import export_step

    import step2drawing
    from bearing_bracket import bracket
    step = tmp_path / "bracket.step"
    export_step(bracket(), str(step))
    rc = step2drawing.main([str(step), "-o", str(tmp_path / "out.pdf"), "--material", "AlMgSi"] + args)
    assert rc == 0 and (tmp_path / "out.pdf").exists() and (tmp_path / "out.png").exists()
