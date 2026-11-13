"""Spot checks of the built-in ISO 286 / ISO 2768 tables against published values."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import iso_tolerances as T  # noqa: E402

# (size, class, upper µm, lower µm) taken from ISO 286-2 tables
CASES = [
    (10, "H7", 15, 0), (20, "H7", 21, 0), (50, "H7", 25, 0), (100, "H8", 54, 0),
    (20, "g6", -7, -20), (10, "h6", 0, -9), (25, "f7", -20, -41), (40, "e8", -50, -89),
    (16, "k6", 12, 1), (20, "m6", 21, 8), (20, "n6", 28, 15), (20, "p6", 35, 22),
    (20, "s6", 48, 35), (60, "s6", 72, 53), (90, "r6", 73, 51), (110, "s6", 101, 79),
    (16, "K7", 6, -12), (16, "M7", 0, -18), (16, "N7", -5, -23), (25, "P7", -14, -35),
    (25, "S7", -27, -48), (16, "G7", 24, 6), (16, "F7", 34, 16), (16, "K8", 8, -19),
    (16, "M8", 2, -25), (16, "N9", 0, -43), (16, "P9", -18, -61), (2, "N9", -4, -29),
    (2, "K7", 0, -10), (16, "js6", 5.5, -5.5), (35, "c11", -120, -280), (45, "c11", -130, -290),
]


@pytest.mark.parametrize("size,code,up,lo", CASES)
def test_deviations(size, code, up, lo):
    assert T.deviations(size, code) == (up, lo)


def test_fit_kinds():
    assert T.fit(20, "H7", "g6")["kind"] == "clearance"
    assert T.fit(20, "H7", "k6")["kind"] == "transition"
    f = T.fit(20, "H7", "s6")
    assert f["kind"] == "interference" and f["max_clearance"] == -14 and f["min_clearance"] == -48


def test_general():
    assert T.general(45, "m") == 0.3
    assert T.general(6, "f") == 0.05
    assert T.general(6.5, "c") == 0.5


def test_parse_and_format():
    assert T.parse_fits("Ø20 H7/s6") == [(20.0, "H7", "s6")]
    assert T.parse_fits("Ø10,5 g6") == [(10.5, "g6", None)]
    assert T.parse_fits("für ISO 4762 M5") == []
    assert T.parse_fits("25 H8") == [(25.0, "H8", None)]
    assert T.fmt_dev(21) == "+0,021" and T.fmt_dev(-7, ".") == "-0.007" and T.fmt_dev(0) == "0"
    assert T.fmt_dev(5.5) == "+0,0055"


def test_out_of_table():
    with pytest.raises(ValueError):
        T.deviations(600, "H7")
    with pytest.raises(ValueError):
        T.deviations(20, "u6")
    with pytest.raises(ValueError):
        T.fit(20, "h7", "G6")
