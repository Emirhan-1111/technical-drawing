"""From a STEP file to a drawing without writing drawing code.

Writes the bracket of the assembly example as data/bracket.step (in practice this file comes
out of SolidWorks, Inventor, Fusion, FreeCAD, ...) and runs the command line tool on it -
once German / first-angle with a full section, once English / third-angle in inches.

Same as on the command line:
    step2drawing examples/data/bracket.step --section --material "EN AW-6082 T651" --density 2.7
    step2drawing examples/data/bracket.step --lang en --projection third --units in -o out.pdf
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build123d import export_step  # noqa: E402

import step2drawing  # noqa: E402
from bearing_bracket import bracket  # noqa: E402

HERE = Path(__file__).parent

if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "output"
    step = HERE / "data" / "bracket.step"
    step.parent.mkdir(exist_ok=True)
    export_step(bracket(), str(step))
    step2drawing.main([str(step), "-o", str(out / "BSP-300.pdf"), "--section",
                       "--title", "Lagerbock", "--number", "BSP-300",
                       "--material", "EN AW-6082 T651", "--density", "2.7"])
    step2drawing.main([str(step), "-o", str(out / "BSP-300-en.pdf"), "--lang", "en",
                       "--projection", "third", "--units", "in", "--title", "Bearing bracket",
                       "--number", "BSP-300", "--material", "EN AW-6082 T651",
                       "--density", "2.7", "--dxf"])
