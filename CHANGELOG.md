# Changelog

## 1.0.0

First public release.

- **STEP to drawing** without code: `step2drawing part.step` - three views placed by the
  projection method, isometric view, hidden lines, centre lines on all cylindrical features,
  overall dimensions, title block with mass, sheet size and scale chosen automatically.
- **Sheet check** on every save: overlapping texts, text crossed by contours or other lines,
  text in the title block / parts list / tables, content outside the frame, datum references,
  ISO 286 classes in dimension texts, empty title block fields, non-ISO scales. Report with
  grid references and a marked `_check.png`.
- **Languages and projection methods**: German and English built in, others via
  `drawlib.TEXTS`; first- and third-angle with the matching symbol; decimal marker per language.
- **Company title blocks** from a JSON layout, with logo.
- **ISO 286 / ISO 2768** tables built in: deviations, limits, fits, limits table and fit table
  on the sheet.
- **Views**: detail view, half section with half dimensions, broken view, removed section,
  clip regions, A1/A0 and landscape A4.
- **Annotations**: radius and diameter dimensions, pitch circles, threads in side view,
  weld symbols (ISO 2553), generic tables, break lines; hatching interrupted around text.
- **Output**: DXF with layers, line types and line weights (ezdxf).
- Clear errors for impossible view directions, warnings for upside-down views, non-ISO
  scales, empty views and cutting planes that miss the part.
- Example gallery: part, assembly, shaft, flange, gear, weldment, English third-angle part,
  STEP import. Tests for the ISO 286 values, the check and every example.
- Installable with pip, `step2drawing` command.
