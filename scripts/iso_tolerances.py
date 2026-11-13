"""ISO 286-1/-2 limits and fits and ISO 2768-1 general tolerances.

    >>> deviations(20, "g6")          # (upper, lower) in micrometres
    (-7, -20)
    >>> limits(20, "H7")              # (largest, smallest) size in mm
    (20.021, 20.0)
    >>> fit(20, "H7", "s6")["kind"]
    'interference'
    >>> general(45, "m")              # ISO 2768-m, permissible deviation in mm
    0.3

Covered: nominal sizes above 0 up to 500 mm, IT3 to IT14, shafts c d e f g h js k m n p r s,
holes C D E F G H JS K M N P R S. That covers the fits used in general mechanical
engineering. Anything outside raises ValueError instead of returning a guessed value.
"""
import bisect
import re

# upper bounds of the nominal size ranges ("above ... up to and including")
_MAIN = [3, 6, 10, 18, 30, 50, 80, 120, 180, 250, 315, 400, 500]
_FINE_RS = [3, 6, 10, 18, 30, 50, 65, 80, 100, 120, 140, 160, 180, 200, 225, 250, 280, 315,
            355, 400, 450, 500]
_FINE_C = [3, 6, 10, 18, 30, 40, 50, 65, 80, 100, 120, 140, 160, 180, 200, 225, 250, 280, 315,
           355, 400, 450, 500]

# standard tolerance grades in micrometres, ISO 286-1 table 1
IT = {
    3: [2, 2.5, 2.5, 3, 4, 4, 5, 6, 8, 10, 12, 13, 15],
    4: [3, 4, 4, 5, 6, 7, 8, 10, 12, 14, 16, 18, 20],
    5: [4, 5, 6, 8, 9, 11, 13, 15, 18, 20, 23, 25, 27],
    6: [6, 8, 9, 11, 13, 16, 19, 22, 25, 29, 32, 36, 40],
    7: [10, 12, 15, 18, 21, 25, 30, 35, 40, 46, 52, 57, 63],
    8: [14, 18, 22, 27, 33, 39, 46, 54, 63, 72, 81, 89, 97],
    9: [25, 30, 36, 43, 52, 62, 74, 87, 100, 115, 130, 140, 155],
    10: [40, 48, 58, 70, 84, 100, 120, 140, 160, 185, 210, 230, 250],
    11: [60, 75, 90, 110, 130, 160, 190, 220, 250, 290, 320, 360, 400],
    12: [100, 120, 150, 180, 210, 250, 300, 350, 400, 460, 520, 570, 630],
    13: [140, 180, 220, 270, 330, 390, 460, 540, 630, 720, 810, 890, 970],
    14: [250, 300, 360, 430, 520, 620, 740, 870, 1000, 1150, 1300, 1400, 1550],
}

# fundamental deviations of shafts in micrometres, ISO 286-1 table 2:
# (size range bounds, values); c..h give the upper deviation es, k..s the lower deviation ei
_SHAFT = {
    "c": (_FINE_C, [-60, -70, -80, -95, -110, -120, -130, -140, -150, -170, -180, -200, -210,
                    -230, -240, -260, -280, -300, -330, -360, -400, -440, -480]),
    "d": (_MAIN, [-20, -30, -40, -50, -65, -80, -100, -120, -145, -170, -190, -210, -230]),
    "e": (_MAIN, [-14, -20, -25, -32, -40, -50, -60, -72, -85, -100, -110, -125, -135]),
    "f": (_MAIN, [-6, -10, -13, -16, -20, -25, -30, -36, -43, -50, -56, -62, -68]),
    "g": (_MAIN, [-2, -4, -5, -6, -7, -9, -10, -12, -14, -15, -17, -18, -20]),
    "h": (_MAIN, [0] * 13),
    "k": (_MAIN, [0, 1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 4, 5]),          # valid for IT4..IT7
    "m": (_MAIN, [2, 4, 6, 7, 8, 9, 11, 13, 15, 17, 20, 21, 23]),
    "n": (_MAIN, [4, 8, 10, 12, 15, 17, 20, 23, 27, 31, 34, 37, 40]),
    "p": (_MAIN, [6, 12, 15, 18, 22, 26, 32, 37, 43, 50, 56, 62, 68]),
    "r": (_FINE_RS, [10, 15, 19, 23, 28, 34, 41, 43, 51, 54, 63, 65, 68, 77, 80, 84, 94, 98, 108,
                     114, 126, 132]),
    "s": (_FINE_RS, [14, 19, 23, 28, 35, 43, 53, 59, 71, 79, 92, 100, 108, 122, 130, 140, 158,
                     170, 190, 208, 232, 252]),
}
_UPPER_LETTERS = "cdefgh"          # letters whose fundamental deviation is the upper one

# ISO 2768-1 permissible deviations for linear sizes, mm
_GEN_BOUNDS = [3, 6, 30, 120, 400, 1000, 2000, 4000]
_GEN = {
    "f": [0.05, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, None],
    "m": [0.1, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2, 2.0],
    "c": [0.2, 0.3, 0.5, 0.8, 1.2, 2.0, 3.0, 4.0],
    "v": [None, 0.5, 1.0, 1.5, 2.5, 4.0, 6.0, 8.0],
}


def _idx(bounds, size):
    if not 0 < size <= bounds[-1]:
        raise ValueError(f"nominal size {size} mm is outside the table (above 0 up to {bounds[-1]} mm)")
    return bisect.bisect_left(bounds, size)


def it(size, grade):
    """Standard tolerance ITgrade in micrometres."""
    if grade not in IT:
        raise ValueError(f"IT{grade} is not in the built-in table (IT3 to IT14)")
    return IT[grade][_idx(_MAIN, size)]


def _split(code):
    m = re.fullmatch(r"\s*([A-Za-z]{1,2})\s*(\d{1,2})\s*", code)
    if not m:
        raise ValueError(f"'{code}' is not a tolerance class such as H7 or g6")
    return m.group(1), int(m.group(2))


def _shaft_fd(size, letter, grade):
    """Fundamental deviation of a shaft letter, micrometres."""
    if letter == "k":
        if size <= 3 or not 4 <= grade <= 7:
            return 0
    bounds, vals = _SHAFT[letter]
    return vals[_idx(bounds, size)]


def deviations(size, code):
    """(upper, lower) deviation in micrometres of tolerance class `code` at nominal `size` mm.
    Lower-case letters are shafts, upper-case letters are holes."""
    letters, grade = _split(code)
    t = it(size, grade)
    if letters.islower():
        if letters == "js":
            return (t / 2, -t / 2)
        if letters not in _SHAFT:
            raise ValueError(f"shaft deviation '{letters}' is not in the built-in table "
                             f"(available: c d e f g h js k m n p r s)")
        fd = _shaft_fd(size, letters, grade)
        return (fd, fd - t) if letters in _UPPER_LETTERS else (fd + t, fd)
    if not letters.isupper():
        raise ValueError(f"'{code}': write holes in capitals (H7) and shafts in lower case (g6)")
    L = letters.lower()
    if L == "js":
        return (t / 2, -t / 2)
    if L not in _SHAFT:
        raise ValueError(f"hole deviation '{letters}' is not in the built-in table "
                         f"(available: C D E F G H JS K M N P R S)")
    if L in _UPPER_LETTERS:                       # A..H: EI = -es
        ei_hole = -_shaft_fd(size, L, grade)
        return (ei_hole + t, ei_hole)
    # J..ZC: ES = -ei, with the delta rule for fine grades (ISO 286-1, 5.3.2.5)
    delta = 0 if size <= 3 or grade < 3 else it(size, grade) - it(size, grade - 1)
    ei_shaft = _shaft_fd(size, L, 6)              # k: value of the IT4..IT7 column
    if L == "k":
        es_hole = 0 if (size <= 3 or grade > 8) else -ei_shaft + delta
    elif L == "m":
        es_hole = -ei_shaft + (delta if grade <= 8 else 0)
    elif L == "n":
        es_hole = (-ei_shaft + delta) if grade <= 8 else 0
        if size <= 3:
            es_hole = -ei_shaft
    else:                                         # P, R, S
        es_hole = -ei_shaft + (delta if grade <= 7 else 0)
    return (es_hole, es_hole - t)


def limits(size, code):
    """(largest, smallest) permissible size in mm."""
    up, lo = deviations(size, code)
    return (round(size + up / 1000, 4), round(size + lo / 1000, 4))


def fit(size, hole, shaft):
    """Fit of hole class and shaft class at one nominal size.
    Returns dict(max_clearance, min_clearance) in micrometres (negative = interference)
    and kind: 'clearance', 'transition' or 'interference'."""
    ES, EI = deviations(size, hole)
    es, ei = deviations(size, shaft)
    if not hole[:1].isupper() or not shaft[:1].islower():
        raise ValueError(f"a fit is written hole/shaft, e.g. H7/g6, not {hole}/{shaft}")
    cmax, cmin = ES - ei, EI - es
    kind = "clearance" if cmin >= 0 else ("interference" if cmax <= 0 else "transition")
    return dict(max_clearance=cmax, min_clearance=cmin, kind=kind)


def general(size, cls="m"):
    """ISO 2768-1 permissible deviation (+/-, mm) for a linear size in class f, m, c or v."""
    cls = cls.lower()
    if cls not in _GEN:
        raise ValueError("ISO 2768-1 classes are f, m, c and v")
    if size < 0.5:
        raise ValueError("ISO 2768-1 starts at 0,5 mm; below that write the tolerance at the size")
    v = _GEN[cls][_idx(_GEN_BOUNDS, size)]
    if v is None:
        raise ValueError(f"ISO 2768-{cls} gives no value for {size} mm")
    return v


# --- reading fits out of dimension texts ---------------------------------------------------
_FIT_RE = re.compile(r"(?:Ø|⌀|R)?\s*(\d+(?:[.,]\d+)?)\s+([A-Za-z]{1,2}\d{1,2})"
                     r"(?:\s*/\s*([A-Za-z]{1,2}\d{1,2}))?(?![\w.,])")


def parse_fits(text):
    """Find tolerance classes in a dimension text. 'Ø20 H7/s6' -> [(20.0, 'H7', 's6')],
    'Ø10 g6' -> [(10.0, 'g6', None)]. Only texts with a diameter sign or a text that is
    nothing but 'size class' are read, so thread callouts like 'ISO 4762 M5' are ignored."""
    out = []
    for m in _FIT_RE.finditer(text):
        whole = text.strip() == m.group(0).strip()
        if not (m.group(0).lstrip().startswith(("Ø", "⌀")) or whole):
            continue
        out.append((float(m.group(1).replace(",", ".")), m.group(2), m.group(3)))
    return out


def fmt_dev(um, dec=","):
    """Deviation in micrometres as a signed mm string: 21 -> '+0,021', 0 -> '0'."""
    if abs(um) < 1e-9:
        return "0"
    s = f"{um / 1000:+.4f}".rstrip("0")
    if s.endswith("."):
        s = s[:-1]
    if len(s.split(".")[1]) < 3:
        s = f"{um / 1000:+.3f}"
    return s.replace(".", dec)
