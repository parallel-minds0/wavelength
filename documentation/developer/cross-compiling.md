# Cross-profile compiler

`source/cross_compile.py` owns profile-family routing and conversion contracts.
`LEVEL_BACKENDS` dispatches whole-level conversions; `BACKENDS` dispatches entity
adapters. Both have explicit unimplemented entries. Engine extensions register
adapters with `register_backend(source_family, target_family, level=...,
entities=...)`; the UI does not hardcode dispatch decisions.

`convert_entity` receives source/target profile IDs, ordered property pairs and
point/brush kind. Results contain status (`converted`, `manual`, `stub`), source
class and original pairs, target properties and warnings. Unknown properties
remain in the report. I/O conversion is deliberately a stub. Identical class
names are not sufficient evidence of compatible behavior.

`scene_entities` snapshots enabled point entities and brush groups once. New
imports persist their profile on objects and the scene. Explicit source profile
selection takes priority over that provenance. Serialized reports also contain
current world transforms in meters. Blender objects are excluded from reports.

The Source 1 → Source 2 level adapter delegates to `source2_map.export` with
separate target settings, preserving the active authoring profile. The VMAP
writer bakes brush mesh transforms into Source units, nests compatible brush
meshes under CMapEntity nodes, and writes point QAngles from current world
rotations. Unsupported brush entities never become world collision accidentally.
Compiler-only visibility hints remain independent of gameplay conversion.

Each VMAP export refreshes its `.crosscompile.json` report, including when
conversion is disabled, so sharing cannot reuse a stale entity report. Source
property pairs and transforms survive unsupported conversion, but the report
is not a geometry backup. Packaging includes the report. Source files and
Blender authoring data remain unchanged.

Verification: `test_cross_compile.py` covers property mapping, unsupported I/O,
backend stubs and extension registration. `blender_cross_compile.py` exercises
real map import, 18 player spawns, four brush entities, edited world transforms,
report packaging and source scene invariance. A stock-surface world/VIS/entity
compile of that converted map succeeded with the installed CS2 tools. Gameplay
and lighting are not validated by that compiler-only check.
