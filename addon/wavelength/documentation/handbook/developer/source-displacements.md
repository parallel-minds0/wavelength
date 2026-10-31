# Source displacement implementation

`source/displacement.py` is independent of Blender. It validates and serializes
VMF `dispinfo`, reconstructs the bilinear base grid in Source row order, adds
elevation/offset/normal-distance contributions and defines the alternating
triangle topology. Known row grids are validated against bounded powers 2–4.
Unknown scalar fields and nested extension blocks remain in `_raw` and are
serialized again. Empty triangle-tag blocks and omitted optional grids remain
valid, matching real decompiled maps.

`source/source_displacement.py` adapts this data to Blender. A backing `BRUSH`
retains `wl_faces` and `wl_face_id`; child `DISPLACEMENT` objects contain a
`wl_source_displacement` record with the face ID, base-corner vertex indices,
Source data and an initial preview signature. The mesh carries:

| Attribute | Domain | Meaning |
|---|---|---|
| `wl_displacement_index` | Point / int | Stable row-major grid identity |
| `wl_terrain_blend` | Point / float | Preview/edit alpha, normalized to 0–1 |
| `wl_displacement_triangle_tags` | Face / int | Source triangle flags |
| `UVMap` | Corner | Normalized surface sampling domain |
| `wavelength` | Corner | Original material projection |

Native vertex/sculpt edits change the grid itself. Export validates the evaluated
mesh, including vertex identities and triangle membership. Geometry-changing
operations are not guessed into valid Source topology. Explicit resampling uses
the same alternating triangles as the Source surface. Coarse/fine sewing averages
shared knots and interpolates intermediate samples; half-edge neighbors use the
same world-space interval mapping. Imported gaps are not automatically repaired.

Import centres each brush's local mesh to limit float32 error on large maps.
`scene.world_point` evaluates coordinates using Python double precision. Original
planes are reused when the imported local mesh, topology, face IDs and transform
are unchanged. Displacement base quads come from those exported planes, not the
rounded viewport vertices. `startposition` is an orientation hint and is retained
when the backing domain is unchanged, even if it differs slightly from the true
corner. These distinctions matter on decompiled coast geometry around 10,000 units.

All native grids are exported on their backing faces. Ordinary backing sides are
masked only for display. Native duplication copies missing grid children; copying
a grid alone creates an independent backing. Pure geometry and Blender-dependent
code remain separate. The legacy procedural terrain path shares the same VMF
serialization and offers explicit conversion to editable native grids.

Reference behavior was checked against Valve's
[displacement generation](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/builddisp.cpp)
and [VMF displacement loading](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/utils/vbsp/map.cpp).
No Valve implementation is vendored into the addon.

## Verification

- `tests/test_displacement.py`: powers, planes, start corners, offsets, elevation,
  metadata round trips, optional/extension blocks, malformed rows.
- `tests/blender_source_displacement.py`: native import/edit/export, UVs, blend
  and triangle attributes, retained backing brushes.
- `tests/blender_source_displacement_authoring.py`: face creation, power changes,
  painting, full/half-edge mixed-power sewing, transforms, duplication, diagnostics.
- `tests/blender_source_displacement_ui.py`: real mouse painting, GPU cursor,
  export after a stroke and single-step undo.

The developer's `d2_coast_01.vmf` was imported/exported with all 211 displacement
fields retained. A separate native-export fixture was accepted by installed HL2
VBSP; decoded compiled vertices agreed with editor reconstruction within 0.000003
Source units. These local checks supplement the portable regression fixtures.
