# Standards and reference values for technical drawings

Tables for choosing values, plus the final checklist. Values are the commonly used ones; when a
drawing goes to real production, confirm fits and limits against the standard itself or the
purchased part's data sheet.

Contents: standards overview · lines and lettering · general tolerances · fits · roughness ·
geometric tolerances · threads and holes · standard-part designations · materials · checklist

## Standards overview

| Topic | Standard |
|---|---|
| Sheet sizes, frame, grid | ISO 5457 |
| Title block | ISO 7200 |
| Parts list (Stückliste) | ISO 7573 |
| Scales | ISO 5455 |
| Lines | ISO 128-2 (formerly 128-20/-24) |
| Views, projection methods | ISO 128-3, ISO 5456-2 |
| Sections, hatching | ISO 128-3 (formerly 128-40/-44/-50) |
| Lettering | ISO 3098 |
| Dimensioning | ISO 129-1 |
| Limits and fits | ISO 286-1/-2 |
| General tolerances | ISO 2768-1 (linear, angular); ISO 2768-2 (geometrical, withdrawn 2021 in favour of ISO 22081 but still what German teaching and many workshops write as "ISO 2768-mK") |
| Tolerancing principle | ISO 8015 (independency), envelope requirement Ⓔ per ISO 14405-1 |
| Geometrical tolerances | ISO 1101; datums ISO 5459; position ISO 5458 |
| Surface texture indication | ISO 21920-1 (replaces ISO 1302) |
| Edges of undefined shape | ISO 13715 |
| Threads, representation | ISO 6410-1 |
| Rolling bearings, simplified | ISO 8826 |
| Item references (Positionsnummern) | ISO 6433 |
| Protection notice | ISO 16016 |

## Lines and lettering (line group 0,5)

| Line | Width | Use |
|---|---|---|
| Continuous wide | 0,5 | Visible edges, cut-face outlines, thread crest, frame of title block |
| Continuous narrow | 0,25 | Dimension, extension and leader lines, hatching, thread root, short centre lines, imaginary intersection lines |
| Dashed narrow | 0,25 | Hidden edges (avoid where a section does the job) |
| Long-dash dot narrow | 0,25 | Centre lines, lines of symmetry, pitch circles |
| Long-dash dot wide | 0,5 | Cutting-plane ends; surfaces with a special requirement (e.g. zone to be hardened) |
| Long-dash double-dot narrow | 0,25 | Adjacent parts, extreme positions of moving parts, contour before forming |

Lettering heights: 3,5 mm for dimensions and tolerances, 2,5 mm for notes, 5 mm for view and
section names and position numbers, 1,6–1,8 mm for field captions.

## General tolerances ISO 2768-1 (limit deviations in mm)

| Class | 0,5–3 | >3–6 | >6–30 | >30–120 | >120–400 | >400–1000 |
|---|---|---|---|---|---|---|
| f (fein) | ±0,05 | ±0,05 | ±0,1 | ±0,15 | ±0,2 | ±0,3 |
| m (mittel) | ±0,1 | ±0,1 | ±0,2 | ±0,3 | ±0,5 | ±0,8 |
| c (grob) | ±0,2 | ±0,3 | ±0,5 | ±0,8 | ±1,2 | ±2 |

Chamfers and radii, class m: 0,5–3: ±0,2 · >3–6: ±0,5 · >6: ±1. Angles, class m: side up to
10 mm ±1°, >10–50 ±0°30′, >50–120 ±0°20′.

ISO 2768-2 geometrical general tolerances:

| Class | Straightness/flatness ≤10 | >10–30 | >30–100 | >100–300 | Perpendicularity ≤100 | >100–300 | Symmetry ≤100 | Run-out |
|---|---|---|---|---|---|---|---|---|
| H | 0,02 | 0,05 | 0,1 | 0,2 | 0,2 | 0,3 | 0,5 | 0,1 |
| K | 0,05 | 0,1 | 0,2 | 0,4 | 0,4 | 0,6 | 0,6 | 0,2 |
| L | 0,1 | 0,2 | 0,4 | 0,8 | 0,6 | 1 | 0,6 | 0,5 |

Consequence: a requirement tighter than these numbers must be written on the drawing; a
requirement looser than them needs nothing.

## Fits (ISO 286, hole-basis system: bores H, shafts chosen)

| Function | Fit | Example |
|---|---|---|
| Sliding/locating clearance, parts move or are assembled by hand | H7/g6 | Sliding bush, locating pin that must come out |
| Close running clearance | H7/f7 | Plain bearing, guide |
| Locating, hand push, practically no play | H7/h6 | Shaft in hub with set screw, spacer, pulleys |
| Transition, light tapping | H7/k6, H7/j6 | Gears, couplings that are keyed |
| Light press fit | H7/n6, H7/p6 | Bushes pressed in, dowel in the fixed part |
| Press fit transmitting torque | H7/r6, H7/s6 | Permanently pressed hubs |
| Dowel pins ISO 8734 / ISO 2338 (pin m6) | bore H7 | press in one part, H7 or slightly larger in the other |

Rolling bearings (bearing tolerances are fixed, only seats are toleranced): rotating inner ring
with point load on the outer ring -> shaft j6/k6 (small bearings j5/h5 or the ground shaft
h6 for light loads), housing H7 (loose, allows axial adjustment); rotating outer ring -> housing
N7/M7, shaft g6/h6. Seat roughness Ra 0,8 (shaft) / Ra 1,6 (housing) or better, shoulder
perpendicular to the seat, fillet radius smaller than the bearing chamfer.

Limit deviations in µm for frequently used fields:

| Nominal | H7 | h6 | g6 | k6 | p6 |
|---|---|---|---|---|---|
| ≤3 | +10 / 0 | 0 / −6 | −2 / −8 | +6 / 0 | +12 / +6 |
| >3–6 | +12 / 0 | 0 / −8 | −4 / −12 | +9 / +1 | +20 / +12 |
| >6–10 | +15 / 0 | 0 / −9 | −5 / −14 | +10 / +1 | +24 / +15 |
| >10–18 | +18 / 0 | 0 / −11 | −6 / −17 | +12 / +1 | +29 / +18 |
| >18–30 | +21 / 0 | 0 / −13 | −7 / −20 | +15 / +2 | +35 / +22 |
| >30–50 | +25 / 0 | 0 / −16 | −9 / −25 | +18 / +2 | +42 / +26 |

Plastics (PTFE, POM, PA) creep and expand strongly with temperature: give a plain limit
dimension (e.g. Ø4,9 +0,05) with a reference temperature instead of an IT6/IT7 field.

## Surface roughness by function (Ra in µm)

| Ra | Process that reaches it | Use |
|---|---|---|
| 0,2–0,4 | Grinding, fine turning, polishing | Seal running surfaces, plain-bearing journals, ground shafts h6 |
| 0,8 | Fine turning, reaming, grinding | Fit surfaces H7/h6, bearing seats on shafts, sliding and rolling contact surfaces |
| 1,6 | Finish turning/milling | Bearing seats in housings, locating and mounting faces, datum faces |
| 3,2 | Normal turning/milling | General machined surfaces (usual collective value) |
| 6,3 | Rough machining, sawing | Surfaces without function, clearance holes |
| 12,5 and up | Raw, cast, flame cut | Untouched semi-finished surfaces |

Write as "Ra 1,6". A surface that must stay as delivered gets the symbol without the bar and a
note (e.g. "Halbzeug, geschliffen"). Coatings and treatments (anodised, hardened 58+2 HRC,
sand-blasted) go in a note or with a wide dash-dot line marking the zone.

## Which geometric tolerance for which function

| Function | Tolerance | Typical value for small precision parts |
|---|---|---|
| Face that locates a bearing, hub or flange axially | Perpendicularity of the face to the bore/shaft axis (or axial run-out) | 0,01–0,03 |
| Two seats on one shaft, bore and outer seat of a bush | Coaxiality, or run-out to the datum axis (easier to measure) | 0,01–0,05 |
| Two bearing bores in one housing or in two blocks bored together | Straightness of the common axis "Ø… CZ", or coaxiality to a common datum A–B | Ø0,01–0,02 |
| Mounting face, sealing face, base of a block | Flatness | 0,01–0,05 |
| Axis height above a base, guide parallel to base | Parallelism to the base datum, plus a toleranced height | 0,01–0,05 |
| Hole pattern for screws/pins | Position with boxed (theoretically exact) spacing dimensions | Ø0,1–0,2 for screws, Ø0,02 for dowels (or drill and ream together at assembly) |
| Slot or tongue centred on a part | Symmetry | 0,02–0,1 |
| Cone, sphere seat, cam, free-form | Surface profile to datums with boxed angle/radius/position | 0,02–0,1 |
| Long slender shaft | Straightness of the axis (Ø zone) | Ø0,01–0,05 |
| Cylinder that seals or guides | Cylindricity or circularity | 0,005–0,02 |

Rules of thumb: a geometric tolerance is smaller than the size tolerance it lives inside; form <
orientation < location for the same feature; choose datums in the order the part is clamped and
assembled (primary = largest locating face or the bore the part sits on). If a tolerance cannot
be reached by setting the part up once, say how it is to be achieved in a note ("in einer
Aufspannung fertigen", "mit Pos. 7 verstiftet gemeinsam bohren und reiben").

## Threads and holes

| Thread | Core drill | Clearance hole (medium, ISO 273) | Counterbore for ISO 4762 head (Ø × depth) |
|---|---|---|---|
| M2,5 | 2,05 | 2,9 | 5 × 2,9 |
| M3 | 2,5 | 3,4 | 6,5 × 3,4 |
| M4 | 3,3 | 4,5 | 8 × 4,6 |
| M5 | 4,2 | 5,5 | 10 × 5,7 |
| M6 | 5,0 | 6,6 | 11 × 6,8 |
| M8 | 6,8 | 9,0 | 15 × 9,0 |

Usable thread depth in aluminium about 2 × d, in steel 1–1,5 × d; core hole about 2–3 mm
deeper than the thread. Callout: "M4 – 10 tief, Kernloch Ø3,3 × 12", "2× Ø4 H7 – 9 tief",
"Ø4,5 durch, Senkung Ø8 × 4,6".

## Designations of standard parts in the parts list

- Zylinderschraube ISO 4762 – M4 × 14 – 8.8
- Gewindestift ISO 4026 – M3 × 8 – 45H (flat point), ISO 4027 (cone), ISO 4029 (cup)
- Zylinderstift ISO 8734 – 4 × 12 – A (hardened, m6), ISO 2338 (unhardened)
- Scheibe ISO 7089 – 4 – 200 HV; Passscheibe DIN 988 – 4 × 8 × 0,1
- Sicherungsring DIN 471 – 5 × 0,6 (shaft), DIN 472 (bore)
- Stellring DIN 705 – A 5
- Rillenkugellager DIN 625-1 – 625-2Z
- Passfeder DIN 6885 – A 3 × 3 × 10

## Material designations

Aluminium EN AW-6082-T6 (AlSi1MgMn; plates T651), EN AW-5083 (cast/rolled precision plate),
EN AW-7075-T6; structural steel S235JR (1.0038); free-cutting steel 11SMn30+C (1.0715);
quenched and tempered C45E (1.1191), 42CrMo4 (1.7225); stainless X8CrNiS18-9 (1.4305,
machinable), X5CrNi18-10 (1.4301); precision shafting Cf53 / 1.1213 induction hardened, h6;
brass CuZn39Pb3; plastics PTFE, POM-C, PA6, PUR with Shore hardness.

## Final checklist (read the rendered sheet against this)

Single part:
1. Enough views/sections to define every feature; section planes marked and named.
2. Centre lines on every rotational feature and hole, overshooting the contour.
3. All sizes present exactly once; dimensions start from functional datums; none inside hatching
   without a clear text gap.
4. Every mating diameter has a fit or limits; tight lengths have explicit tolerances.
5. Datums defined on functional surfaces; geometric tolerances reference existing datums.
6. Roughness on every functional surface; collective indication beside the title block.
7. Threads, chamfers, radii, undercuts specified (or covered by a note "nicht bemaßte Fasen …").
8. Notes: manufacturing sequence that matters, heat/surface treatment, edges.
9. Title block: title, number, material, mass, scale, general tolerance, date, sheet, status.
10. Nothing overlaps: no text on lines, no leader through a dimension number, no crossed
    dimension lines where avoidable.
11. Manufacturable: tool access for every bore and thread, internal corners with radius or
    relief, wall thickness under threads, tolerances reachable with the named process.

Assembly:
1. Every part has exactly one position number (identical parts share one); numbers in a row.
2. Parts list complete, quantities match the model, standard parts with full designation.
3. Sections show how parts are located, fastened and adjusted; standard parts uncut.
4. Only assembly, connection and overall dimensions; fits at joints (e.g. "Ø5 H7/h6").
5. Notes on adjustment, joint machining, locking of screws, lubrication.
6. Interference check of the 3D assembly done, deliberate overlaps explained.
