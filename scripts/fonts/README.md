# osifont

Technical drawings to ISO 3098 need a technical lettering font. This project uses
**osifont**, which is **not bundled here** so that this repository stays under a single,
simple licence.

Download `osifont-lgpl3fe.ttf` from https://github.com/hikikomori82/osifont and put it in
any one of these places - drawlib looks in this order:

1. the path in the environment variable `DRAWLIB_FONT`
2. this folder (`scripts/fonts/`)
3. `~/.drawlib/fonts/` (handy after `pip install`)
4. installed system-wide (double-click the file and "Install" on Windows/macOS)

Or call `drawlib.set_font(path)` before creating a sheet.

osifont is published under the **LGPL-3.0 with a font exception**: you may use it freely,
including in commercial drawings, and embedding it in a PDF does not affect the licence of
that PDF. If you redistribute the font file itself, pass on the LGPL-3.0 licence text with it.

Without the font everything still runs on DejaVu Sans. Dimensions, line widths and layout
are unaffected; only the lettering is then not ISO 3098 compliant, which matters if the
drawing is handed over as a standards-compliant document. The sheet check measures the
text of whichever font is active.
