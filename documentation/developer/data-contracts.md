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

Environment layers use native terrain vertex groups as authoritative masks and
`Object.wavelength_environment_layers` RNA records for rules, palettes and
serialized candidate overrides. Corrections are authoritative in the object's
`wl_environment_placement_overrides` JSON map keyed by layer UUID; the RNA accessor
retains a fallback for earlier per-layer strings. Checkpoint forks remap that map
alongside layer identities. `wl_environment_id` identifies a terrain or
prototype; layer UUIDs identify mask/rule bindings. Candidate addresses are scoped
by terrain and layer and use seeded physical-world cell/slot coordinates, not
object names or Python's randomized hash. Generated point meshes and node groups
are disposable previews. Removal of a rule leaves its native mask intact.

Adopted placements retain a separate point mesh with original point IDs, rotation,
scale and sampled ground height. They preserve full original placement offsets
while optionally following sculpt height deltas. The original point set remains
a hidden backup and a native remainder preserves its outside instances. Material
composition stores the authored base independently and exposes masks through a
native modifier. Blender's representative biome preview is a derivative; native
Godot biome material references and painted-weight injection remain authoritative
for the target appearance.

The Godot schema-1 bundle resolves the same authored records used by the preview,
retaining a complete static instance list independent of preview thinning.
Transforms are basis columns then origin in Godot Y-up world meters. Raw override
matrices are separately labeled Blender-world data. Evaluated mask vertices and
triangles share the terrain GLB's world-space coordinates. The sample loader is
a consumer; runtime streaming and seasonal materials are not Blender authoring
policy. This is a concrete procedural-layer client of the integrated roadmap,
not an implementation of general map revisions or compositions.

Do not independently cache a profile unit, material path or operation choice in
multiple UI panels. The active header, modal preview and committed guide must use
the same settings. Document new persisted keys, schema changes and migration
behavior beside the code that reads/writes them.
