---
name: technical-drawing
description: Produce standards-compliant technical drawings (ISO/DIN, also ASME-style third-angle in English) as vector PDF/SVG/DXF from parametric build123d models or from a STEP file - part drawings, assembly drawings and weldments with sections, detail/half/broken views, hatching, dimensions, ISO 286 fits and limits tables, surface texture, geometrical tolerances (GD&T) and datums, threads, weld symbols, gear data tables, title block and parts list, checked automatically for collisions and inconsistencies. Use this skill whenever the user asks for a technical/engineering/manufacturing drawing, technische Zeichnung, Fertigungszeichnung, Einzelteilzeichnung, Zusammenbauzeichnung, Schweißzeichnung, teknik resim, a drawing from a STEP/CAD file, a BOM/Stückliste on a drawing, or wants fits, tolerances, roughness or GD&T put on a part - also when they only say "make CAD and drawings for this part" or want an existing drawing checked against the standards. Do not use it for software diagrams, flowcharts or UI mock-ups.
---

# Technical drawings

Drawings are generated, not drawn by hand: a parametric build123d model (or a STEP file) is
the single source of truth, `scripts/drawlib.py` derives the views from it (hidden-line
removal, sections, hatching) and adds the annotations a workshop needs. Every save runs an
automatic sheet check. The result is a vector PDF per sheet (optionally DXF/SVG) plus a PNG
preview that you look at before you call anything finished.

Why this route: views can never disagree with the model, a changed parameter regenerates
every sheet, and the same model gives STEP files and an interference check for free.

## What a good drawing has to achieve

A drawing is a contract with the person who makes and inspects the part. Someone who has
never seen the project must be able to manufacture it from the sheet alone. That decides
everything below: dimension what the *function* needs, tolerate only what matters, and say
how each functional surface has to look. A sheet with every edge dimensioned but no fits,
roughness or geometrical tolerances is not manufacturable in the sense examiners and
workshops mean.

## Choose the route

- **The user has a STEP file and wants a drawing quickly**: run
  `python scripts/step2drawing.py part.step [--section] [--lang en --projection third]
  [--units in] [--material ...] [--density ...] [--dxf]`. It gives views, hidden lines, centre
  lines, overall dimensions, title block and the check. Then say clearly that functional
  dimensions, fits, tolerances and surface texture still have to be added - and offer to add
  them: `auto_drawing()` in the same module returns `(sheet, views, issues)` with `out=None`, so
  you can keep annotating the sheet in Python (`--up y` for Y-up exports).
- **Anything that has to be manufactured from**: model the part(s) and write the sheet in Python
  (workflow below). STEP input can still be the model: `D.load_step(path)`.

## Workflow

1. **Clarify the function first.** For each part ask: which surfaces mate with what, what
   must be coaxial/perpendicular/flat for the machine to work, which dimensions come from
   purchased parts (bearings, pins, screws). These become datums, fits and tolerances. If
   the user has a report, BOM or older drawing, read it and keep its numbers; mark every
   value you invent as your assumption and tell the user. Ask which language and projection
   method the drawing is for (default: German, first-angle; North America: English,
   third-angle) and whether there is a company title block.
2. **Model the parts** in one module, each part in its manufacturing position, all
   dimensions as named parameters. Turned parts: revolve a half-profile `(x, r)`; prismatic
   parts: boxes minus bore solids, or extrude one profile (no fused seams). Model threads as
   core holes only. Put purchased/standard parts in as simple solids so the assembly and the
   interference check are complete.
3. **Check the assembly before drawing**: pairwise `(a & b).volume` over all parts; every
   overlap must be either zero or deliberate (thread engagement, press fit). Fix the model,
   not the drawing.
4. **Write one function per sheet**, copying the closest example in `examples/`:
   `flanged_bush.py` (turned part, the basic template), `bearing_bracket.py` (assembly,
   parts list), `stepped_shaft.py` (broken view, detail, removed section, thread),
   `flange.py` (half section, pitch circle, position tolerance), `spur_gear.py` (gear data
   table), `weldment.py` (weld symbols), `milled_block.py` (English, third-angle, company
   title block). Start with geometry only, render, look, then add annotations in layers:
   centre lines -> dimensions -> datums and tolerances -> surface texture -> notes, tables ->
   title block.
5. **Render, read the check, look at every sheet.** `Sheet.save(pdf, png=...)` prints the
   check report and writes `<png>_check.png` with each finding framed. Fix every error and
   warning (move the annotation, change offsets, `tshift`, `tpos`, knees of leaders). Then
   read the PNG yourself - the check finds collisions and inconsistencies, not a wrong
   dimensioning concept or an arrow pointing at the wrong edge. Crop dense regions to zoom.
   Never report a sheet as done that you have not seen.
6. **Deliver**: one PDF per sheet named by drawing number, a merged set (pypdf
   `PdfWriter.append`), DXF if the user edits in CAD, STEP per part and for the assembly
   (`export_step`). State plainly what is not drawn yet and which values are assumptions.

Setup once per machine: `pip install -r requirements.txt`. The ISO 3098 font osifont is
not bundled; it is found in `$DRAWLIB_FONT`, `scripts/fonts/`, `~/.drawlib/fonts/` or the
system fonts (see `scripts/fonts/README.md`). Without it the library uses DejaVu Sans -
same geometry, lettering not ISO 3098; the check measures whichever font is active.

## Using drawlib

Read `references/drawlib_api.md` before writing the first sheet - every call with its
coordinate conventions, recipes and pitfalls. The essentials:

- `S = D.Sheet("A4"|"A3"|"A2"|"A1"|"A0", lang="de"|"en", projection="first"|"third")`. A4 is
  portrait, the others landscape (`landscape=` overrides). Sheet coordinates are mm from the
  lower left corner. Numbers the library writes follow the language's decimal marker, and
  decimals inside dimension texts are converted (`"0.02"` -> `0,02` on a German sheet).
- `V = D.View(S, origin, scale, *D.VIEWS["front"])` - `VIEWS` has front, top, bottom, left,
  right, rear, iso. `V.p(u, v)` turns view coordinates (model mm) into sheet mm - use it for
  every annotation. Wrong vectors raise a clear error; non-ISO scales and upside-down views warn.
- Views: `V.draw(solids, hidden=)`, `V.section([(V.cut(solid), angle, spacing), ...],
  background=[uncut parts])`, `V.half_section(...)`, `V.removed_section(...)`,
  `V.detail(centre, r, at, scale, "Z")`, `D.BrokenView(...)`, `V.thread(...)`,
  `D.views_layout(...)` for placement by projection method.
- Dimensions: `S.hdim`, `S.vdim`, `S.dim`, `S.dim_angle`, `S.rdim`, `S.ddim`; options `tol=`,
  `box=True`, `outside=True`, `half=True`, `tshift=`.
- Fits: write them in the text (`"Ø20 H7"`, `"Ø20 H7/s6"`); `S.fit_table`, `S.fit_pair_table`
  print ISO 286 values; `iso_tolerances` gives deviations, limits, fits, ISO 2768.
- GD&T: `S.datum`, `S.fcf(x, y, kind, "0.02", ["A", "B"])`, `S.fcf_leader`.
- Surfaces: `S.rough`, `S.rough_leader`, `S.general_surface`.
- `S.notes`, `S.leader_text`, `S.posnum`, `S.cutting_plane`, `S.bom`, `S.table`, `S.weld`,
  `S.pitch_circle`, `S.title_block(values, layout=json_or_dict, logo=png)`.

## Rules that make the difference

These are the points examiners and workshops check; `references/normen.md` has the tables
(line types, ISO 2768 values, common fits, typical Ra values, which geometrical tolerance
for which function) and should be read when choosing values.

- **Projection and views**: state the method (symbol in the title block). Fewest views that
  define the part; a turned part needs one section along its axis. Prefer sections over hidden
  lines. Scales from ISO 5455 only; small parts are drawn enlarged so dimensions have room;
  long parts are broken; small details get a detail view.
- **Dimension from the functional datum**, not in chains, never twice. Auxiliary dimensions
  in parentheses. Dimensions outside the contour where possible; hole patterns in the view that
  shows them as circles; smaller dimensions closer to the part.
- **Fits and tolerances**: every mating diameter gets an ISO 286 fit (bearing seats as the
  bearing maker recommends). Everything untoleranced falls under the general tolerance in the
  title block (ISO 2768-mK by default; ISO 13920 for weldments).
- **Geometrical tolerances only where function needs them**, always with a datum that is
  itself a functional, measurable feature. Datum on an axis: in line with that diameter's
  dimension line. The leader meets the surface square on. Hole patterns: theoretically exact
  dimensions plus position tolerance.
- **Surface texture on every functional surface**, the general value once beside the title
  block. Symbols must read from below or from the right - use a leader for faces pointing down.
- **Sections**: shafts, pins, screws, keys, rolling elements and ribs are not cut in a
  longitudinal section. Neighbouring parts get different hatching; thin cut faces are blackened
  (`angle="solid"`); hatching is interrupted around text automatically.
- **Threads** (ISO 6410), **welds** (ISO 2553), **gears** (ISO 2203): drawn simplified, with
  the callout or data table carrying the information.
- **Assembly drawings**: item numbers in a row, leaders ending in a dot; parts list above the
  title block, item 1 at the bottom; standard parts with their standard designation; only
  functional and mounting dimensions; notes say how it is assembled and adjusted.
- **Title block**: title, drawing number, material with standard designation, mass
  (`solid.volume` × density), scale, general tolerance, date, sheet n/m, document type,
  revision. Never leave material or scale empty - the check flags it.

## Honesty about limits

- Output is PDF/SVG/PNG/DXF plus STEP, not a native SolidWorks/Inventor drawing. For further
  editing in CAD give the DXF and STEP and say so.
- The sheet check finds collisions and inconsistencies; it does not judge whether the
  dimensioning, tolerancing or the choice of views is right. That is your review of the PNG
  against the checklist in `references/normen.md`.
- Tolerance values you choose are engineering proposals. Say which come from the user's
  documents and which are yours, so they can defend them.
