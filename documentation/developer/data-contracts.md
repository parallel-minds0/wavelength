# Scene data and ownership contracts

## Profiles and procedural definitions

`profiles.PROFILES` supplies format, grid, unit scale, family, build stages and
explicit geometry constraints. Read those capabilities rather than inferring all
behavior from the name "Source". `procedural.Definition` records generator kind,
owner and parameters separately from the adapter used to evaluate geometry.
Finalization commits evaluated geometry; changing workspace is a visibility/tool
transition and must not silently finalize or reinterpret authored data.

```{code-sample} addon/wavelength/source/profiles.py convex-contract
```

## Brush identity and faces

A brush mesh uses `wl_role`, a unique object `wl_id`, `wl_unit_meters`, per-face
`wl_face_id`, and serialized `wl_faces` metadata. Face IDs must remain positive
and unique after topology operations. Material identity and projection data are
different concerns: changing a texture must preserve unedited faces' projection.
See {source}`addon/wavelength/source/scene.py` and
{source}`addon/wavelength/source/textures.py`.

The `formats.Face` record carries plane points, texture name, projection and
optional Valve axes/VMF information. Export validates engine restrictions; a
renderable arbitrary Blender mesh is not necessarily a valid BSP brush.

## Entities and representations

Entity keyvalues and brush-entity membership are persisted independently of an
editor representation. A model/SVG helper is not the entity's game definition.
Model capabilities depend on the resolved game schema. Custom editable meshes
use the custom model compiler/packaging path when assigned to model-capable
entities; brush entities use brush geometry.

## Asset identity and caches

Asset records include category, engine and path. A same-named item from another
profile is not interchangeable. Setup validates catalog/library identity before
applying queued preview results. Cache files are regenerable local content;
project data must not depend on a transient thumbnail object name.

## Source of truth

Do not independently cache a profile unit, material path or operation choice in
multiple UI panels. The active header, modal preview and committed guide must use
the same settings. Document new persisted keys, schema changes and migration
behavior beside the code that reads/writes them.
