# drawlib API

`import drawlib as D` (with `scripts/` on `sys.path`, or after `pip install`). Needs
build123d, matplotlib, numpy; DXF output needs ezdxf. All lengths in mm. Sheet coordinates
start at the lower left corner of the trimmed sheet. Angles in degrees, counter-clockwise
from +x.

Contents: Sheet · View · special views · dimensions · fits · geometrical tolerances ·
surfaces · text, leaders, tables, assembly · welds · title block · check and output ·
STEP · view directions · recipes · pitfalls

## Sheet

| Call | Purpose |
|---|---|
| `S = D.Sheet(fmt="A4", lang="de", projection="first", landscape=None, decimal=None)` | `fmt` A4…A0 (A4 portrait, others landscape unless `landscape=`). `lang` "de"/"en" or a key you add to `D.TEXTS`. `projection` "first" (ISO method 1) or "third" (method 3). Drawing area `S.fl, S.fb, S.fr, S.ft`. |
| `S.line(pts, style)` / `S.seg(a, b, style)` | Styles: `thick` 0,5, `thin` 0,25, `xthick` 0,7, `hidden`, `center` (long-dash dot), `phantom` (long-dash double dot). |
| `S.circle(c, r, style)` / `S.arc(c, r, a0, a1, style)` | Any style, e.g. `"center"` for a pitch circle. |
| `S.centerline(a, b)` | Centre line starting and ending with a dash; overshoot the contour by 2–3 mm. |
| `S.centre_cross(c, r, over=2.5)` | Crossed centre lines of a circle of sheet radius `r`. |
| `S.pitch_circle(c, r, holes=[angles])` | Pitch circle plus radial centre lines through the holes. |
| `S.thread_end(c, r_nom)` | Internal thread seen from the end: thin three-quarter circle. |
| `S.break_line(a, b)` | Thin break line with zigzag. |
| `S.text(x, y, s, h=3.5, ha="center", va="baseline", rot=0)` | ISO 3098 lettering, `h` = cap height. 3,5 dimensions, 2,5 notes, 5 view names. `D.text_width(s, h)`. |
| `S.num(x, nd)` | Number with the sheet's decimal marker. |
| `S.grid_ref(x, y)` | Grid reference such as "C3". |

## View

```python
V = D.View(S, origin=(72, 190), scale=2.0, n=(0, -1, 0), xdir=(1, 0, 0), clip=None)
V = D.View(S, (72, 190), 2.0, *D.VIEWS["front"])          # same
```

- `origin`: sheet position of the model origin; `scale` 2.0 = 2:1. `n` points from the part to
  the viewer, `xdir` is the model direction shown to the right, sheet-up is `n × xdir`.
  `xdir` not perpendicular to `n` raises `ValueError`; an upside-down view or a scale outside
  ISO 5455 gives a `DrawingWarning`.
- `V.p(u, v)` view coordinates → sheet; `V.P((x, y, z))` model point → sheet. Use them for
  every annotation.
- `V.draw(solids, hidden=False, thin_if=None)`: visible edges thick, `hidden=True` adds dashed
  hidden edges. Warns if nothing is visible.
- `V.cut(solid, d=0.0)`: removes everything between the viewer and the plane `p·n = d`.
- `V.section(items, d=0.0, background=())`: `items = [(cut_solid, angle, spacing), ...]`.
  `angle=None` leaves a face blank, `angle="solid"` blackens it (thin parts). `background` =
  solids drawn uncut (shafts, pins, screws). Warns if a cut face is not in the plane and lists
  the planes that exist.
- `V.removed_section(solid, d, angle, spacing)`: only the cut face, nothing behind it.
- `V.thread((u0, v), (u1, v), d_nom, d_core, internal=False)`: thread between two points on its
  axis (model mm), thin root lines and thick thread end. `V.thread_end((u, v), d)` end view.
- `D.views_layout(front_centre, gap, sizes, projection)`: centre points of top/bottom/left/right
  views around the front view, placed by the projection method; `sizes = {name: (w, h)}` in
  sheet mm.

Section through the plane y = 0 looking in +y: `V = D.View(S, o, k, *D.VIEWS["front"]);
V.section([(V.cut(part), 45, 2.5)])`. For a plane x = c seen from the left
(`n = (-1, 0, 0)`): `d = -c`, i.e. `d = n · (point on the plane)`.

## Special views

| Call | Purpose |
|---|---|
| `Vd = V.detail((u, v), r, at, scale, "Z")` | Marks a circle of radius `r` (model mm) around `(u, v)` in `V`, returns a view clipped to a circle at sheet point `at`, labelled "Z (5:1)". Draw into `Vd` like into `V`. |
| `sec, vw = V.half_section([(solid, angle, spacing)], axis_v=0, side="upper")` | Half section of a symmetric part: one half cut, the other half as a view. Pass *uncut* solids. |
| `bv = D.BrokenView(S, origin, scale, n, xdir, breaks=[(u0, u1)], gap=8)` | Long part with the ranges `u0..u1` left out. `bv.p(u, v)` takes *true* coordinates; `bv.draw`, `bv.section`, `bv.views[i]` for details/threads. Write the true length on dimensions across a break. |
| `View(..., clip=("rect", (x0, y0, x1, y1)))` / `("circle", c, r)` | Any view cut to a region. |

## Dimensions (ISO 129-1)

| Call | Notes |
|---|---|
| `S.hdim(p1, p2, y, text, **kw)` | Horizontal, dimension line at sheet height `y`. |
| `S.vdim(p1, p2, x, text, **kw)` | Vertical, dimension line at sheet `x`, text reads from the right. |
| `S.dim(p1, p2, off, text, orient="a")` | Aligned, offset `off` left of p1→p2. |
| `S.dim_angle(c, r, a0, a1, text, box=False, ext=None)` | Angle about vertex `c`. |
| `S.rdim(c, r, angle, text, outside=None, concave=False)` | Radius "R5": line from the centre along `angle`, arrow on the arc. `concave=True` for fillets whose centre lies in free space. |
| `S.ddim(c, r, angle, text, box=False, tpos=0.5)` | Diameter across a circle seen as a circle. `tpos` = where the value sits (0 centre, 1 circle, >1 outside with the line run on to it). |

Keyword options for `hdim/vdim/dim`: `outside=True` (arrows outside for short dimensions),
`tshift=mm` (slide the value along the line), `tol=("+0.05", "0")` (limit deviations),
`box=True` (theoretically exact), `ext1=False/ext2=False` (no extension line),
`tside="below"`, `half=True` (half dimension in half sections: only the p2 end, line ends
just past the axis).

The text is free: `"Ø5 H7"`, `"24 ±0.01"`, `"(Ø36.92)"`, `"2× Ø4 H7"`, `"M4"`. Decimal
markers between digits are converted to the sheet's language. Space dimension lines ≥ 8 mm
from the contour and 6–7 mm apart.

## Fits (ISO 286, ISO 2768)

- Write the class in the dimension text; the check verifies it exists (`H17` is an error,
  `h7/G6` is an error, a letter outside the built-in table is an info).
- `S.fit_table(x, y, ["Ø10 H7", "Ø20 g6"])`: table with deviations, max. and min. size.
- `S.fit_pair_table(x, y, ["Ø20 H7/s6"])`: max./min. clearance (negative = interference), type.
- `import iso_tolerances as T`: `T.deviations(20, "g6") -> (-7, -20)` µm,
  `T.limits(20, "H7") -> (20.021, 20.0)`, `T.fit(20, "H7", "s6")`, `T.general(45, "m") -> 0.3`,
  `T.it(20, 7)`. Covered: sizes up to 500 mm, IT3–IT14, shafts c d e f g h js k m n p r s,
  holes C D E F G H JS K M N P R S.

## Geometrical tolerances (ISO 1101, ISO 5459)

```python
S.datum("A", foot, direction, length=7)                  # filled triangle on `foot`
box = S.fcf(x, y, "perpendicularity", "0.01", ["A"])     # lower left corner (x, y)
S.fcf_leader(box, target, side="left", via=None)         # leader with arrow onto the feature
```

- `kind`: straightness, flatness, circularity, cylindricity, profile_line, profile_surface,
  parallelism, perpendicularity, angularity, position, coaxiality, symmetry, runout,
  total_runout.
- Datum on a **surface**: triangle on the contour or its extension line, away from dimension
  lines. Datum on an **axis**: triangle in line with that diameter's dimension line. The same
  for the tolerance arrow. The leader meets the feature square on.
- A frame placed directly under a hole callout (`leader_text` shelf) applies to that feature.
- The check reports frames that refer to a datum not indicated on the sheet.

## Surfaces (ISO 21920-1)

| Call | Notes |
|---|---|
| `S.rough(tip, "Ra 0.8", rot=0)` | Tip on the surface (or its extension line), symbol on the material-free side. `rot=90` for a vertical surface with free space to the left. Must read from below or the right - for downward faces use the leader. |
| `S.rough_leader(target, knee, "Ra 0.8")` | Arrow onto the surface, symbol on a horizontal line from `knee`. |
| `S.general_surface(x, y, "Ra 3.2", others=True)` | General note beside the title block: `(140, 61)` on A4, `(330, 61)` on A3. |

## Text, leaders, tables, assembly items

| Call | Notes |
|---|---|
| `S.notes(x, y, lines, head=None)` | Numbered notes; heading from the language ("Hinweise"/"Notes"), `head=""` for none. Returns the y below. |
| `S.leader_text(target, knee, text, under=None, arrow=True, dot=False)` | Leader with text on a shelf, optional second line. Hole and thread callouts. |
| `S.view_label(x, y, "A-A")` | View or section name, h = 5. |
| `S.posnum(target, at, num)` | Item number: dot in the part, number at `at`; align the `at` points. |
| `S.cutting_plane(a, b, letter, look)` | Section line with thick ends, arrows in sheet direction `look`, letters. |
| `S.detail_mark(c, r, letter)` | Circle and letter for a detail (done by `View.detail`). |
| `S.table(x, y, rows, widths, h=2.5, head_rows=1, align=None)` | Table, upper left corner at (x, y): gear data, revision table, anything. |
| `S.bom(rows)` | Parts list above the title block; rows `(Item, Qty, Description, Part no./Standard, Material)`, first row at the bottom. Headings follow the language. |

## Welds (ISO 2553)

```python
S.weld(target, knee, kind="fillet", size="a5", length="", side="arrow",
       all_around=False, field=False, process="135")
```

`kind` fillet, I, V, HV. `side` "arrow" (symbol on the continuous line), "other" (under the
dashed identification line), "both" (symmetric, no dashed line). The symbol sits next to the
arrow line, the tail with the process at the far end.

## Title block (ISO 7200, or your own)

```python
S.title_block(dict(title="Lagerbock", subtitle="...", number="KS-100-05",
                   material="EN AW-6082 T651", mass="38 g", scale="2:1", author="...",
                   dept="...", project="...", ref="...", approved="...", doctype=None,
                   status=None, rev="A", sheet="1/1", gentol="ISO 2768-mK",
                   tolprinciple="ISO 8015", edges=("-0.3", "+0.1")),
              layout=None, logo=None)
```

Required: `title`, `number`. Defaults follow the language (doctype "Einzelteilzeichnung" /
"Part drawing", status "Entwurf" / "Draft"). Long values shrink to fit. Two scales:
`"5:1 (2:1)"`.

`layout` replaces the ISO 7200 layout: a dict or a JSON file with `width`, `rows` (row edges
from the bottom), and `cells`, each with `row` or `rows: [r0, r1]`, `x: [x0, x1]`, `label`
(a key of `D.TEXTS` or literal text), `key` (entry of the values dict), `type` (`text`,
`title`, `number`, `projection`, `edges`, `image`), optional `h`, `align`. `logo=` fills an
image cell with key `logo`. Example: `examples/data/title_block_company.json`.

## Check and output

- `S.save(path, png=None, dpi=150, check=True, dxf=None, quiet=False)`: `.pdf`, `.svg`, `.png`
  or `.dxf` by suffix; `png=` preview; `dxf=` additional DXF. Runs `S.check()`, prints the
  report, writes `<png>_check.png` with findings framed. Returns the list of `Issue`.
  Closes the figure - call it last.
- `S.check(verbose=True)`: `Issue(level, msg, box, grid)`, levels error / warning / info.
  Overlapping texts, text crossed by contours or other annotation lines, text in title
  block/parts list/tables, content outside the frame or in the title block, datum references,
  invalid fits, empty material/scale, non-ISO scales.
- Hatching is interrupted around text automatically on save (ISO 128-50).
- DXF: layers VISIBLE, THIN, HIDDEN, CENTER, PHANTOM, FRAME, HATCH, TEXT with line weights and
  line types, text style ISO (isocp.shx), units mm. Logos are not exported.

## STEP

- `D.load_step(path)` → build123d shape.
- `step2drawing.auto_drawing(shape, out=None, fmt="auto", scale="auto", lang="de",
  projection="first", title=..., number=..., material="", density=None, up="z",
  section=False, hidden=True, iso=True, dims=True, units="mm", dxf=False)` →
  `(sheet, views, issues)`. With `out=None` nothing is written: add annotations to `sheet`
  using `views["front"].p(...)` etc., then `sheet.save(...)`. The part is moved so its
  bounding box is centred in x and y and stands on z = 0.
- Command line: `step2drawing part.step --help`.

## View directions (part with x right, y back, z up)

| View | `D.VIEWS` | `n` | `xdir` | first-angle | third-angle |
|---|---|---|---|---|---|
| Front (looking +y) | `front` | `(0, -1, 0)` | `(1, 0, 0)` | centre | centre |
| Top (looking down) | `top` | `(0, 0, 1)` | `(1, 0, 0)` | below | above |
| From below | `bottom` | `(0, 0, -1)` | `(1, 0, 0)` | above | below |
| From the left (looking +x) | `left` | `(-1, 0, 0)` | `(0, -1, 0)` | right | left |
| From the right (looking −x) | `right` | `(1, 0, 0)` | `(0, 1, 0)` | left | right |
| Isometric | `iso` | `(1, -1, 1)` | `(1, 1, 0)` | free | free |

Views that share an axis must share that sheet coordinate (`D.views_layout` does it).

## Recipes

- **Thread in a section**: model only the core hole; `V.thread(a, b, d_nom, d_core,
  internal=True)` plus `S.leader_text(..., "M6 - 12 tief")`.
- **Gear** (ISO 2203): model the blank up to the tip circle; in the section draw the pitch line
  `S.line(..., "center")` and the root line thick; in the end view the pitch circle
  `S.circle(c, r, "center")`; data in `S.table`. See `examples/spur_gear.py`.
- **Hole pattern**: `S.pitch_circle`, boxed pitch diameter `S.ddim(..., box=True, tpos=...)`,
  callout "6× Ø9" with the position frame directly under its shelf.
- **Adjacent or moving parts**: `S.circle(V.P(c), r * V.k, "phantom")` or `S.line(..., "phantom")`.
- **Theoretical apex / extended contour**: thin lines beyond the part.
- **Assembly section**: cut only the parts that may be cut; shafts, pins, screws go into
  `background=` so hidden-line removal treats everything together.
- **Rolling bearings**: leave the cut rings unhatched (`angle=None`) and draw an upright cross
  in each ring section (ISO 8826-1).
- **Mass**: `solid.volume * rho / 1000` in g, rho in g/cm³ (Al 2,70 · steel 7,85 · stainless
  7,9 · cast iron 7,2 · brass 8,5 · PTFE 2,17 · POM 1,41).
- **Merged PDF**: `w = pypdf.PdfWriter(); [w.append(p) for p in pdfs]; w.write(out)`.
- **Zoom into a region**: `PIL.Image.open(png).crop((x0, y0, x1, y1))`.

## Pitfalls

- Empty or mirrored view: check `n`/`xdir` against the table; `n × xdir` must point up.
- No hatching: the solid was not cut, or `d` is not the cutting plane - the warning lists the
  planes that exist.
- Stray lines along cylinders: surface seams; `draw` removes them, but a solid fused from many
  pieces can keep split edges - revolve or extrude one profile instead.
- A check warning that only appears with one font: texts have different widths in osifont and
  DejaVu Sans. Leave a few mm of room; render once with and once without
  `DRAWLIB_FONT` set (the CI runs without the font).
- Files edited with PowerShell `Set-Content -Encoding utf8` get a BOM; prefer the Edit tool.
