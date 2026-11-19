# High-level cell-map backend

The `civ5` profile inherits mesh viewing, not BSP constraints, and declares
`authoring: hex_cells`. Core context policy blocks low-level authoring operations
for this profile. The dedicated Object Mode tool edits cell properties directly.

`civ5_format.py` is Blender-independent. It bounds-checks map dimensions and
length-prefixed header tables, locates the eight-byte geography records and
retains the entire original file. Export patches specified cell records only;
unknown scenario and mod metadata are never reconstructed or discarded. Current
layout support covers the installed version-7/9/10/11/12 fixtures. The format is
binary, not an SQLite database.

`civ5_cells.py` materializes one hex polygon per cell in one display mesh. Face
attributes contain the eight geography values. A Blender Text ID retains the
base64 original document, surviving saves. A fast bulk-coordinate/topology hash
rejects low-level geometry edits. Painting updates only selected cell attributes;
the display mesh is regenerated from elevation/terrain values. River controls
mask only the three owned edge bits. Geographic dimensions and original scenario
sections are preserved. A cached GPU overlay displays river edges; the panel
exposes human-readable choices from the map's own type tables.

Tests include synthetic malformed/truncated inputs, raw no-op equality, field-only
byte changes, 90 shipped maps, actual Blender import/export and save/reload, and
viewport ray selection plus cell painting. No shipped game files are modified by
the tests. In-game edited-map validation and gameplay-rule enforcement remain open.

Format research: https://github.com/samuelyuan/Civ5MapImage/blob/master/FORMAT.md
and https://github.com/fechan/civ5map-tools/blob/master/civ5map.ksy
