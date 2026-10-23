# Geometry operations and materials

## Pencil: guide, face projection and solid cutting

`pencil.py` owns drawing, sampled Bezier paths, controls and dispatch. Faces mode
uses Knife Project on a private mesh copy and restores the viewport. Solid modes
call `cutter_solid.apply` with world-space sampled points and the chosen normal or
XYZ direction. Finite depth converts profile units to world units once.

The exact Boolean solver produces difference/intersection results. A solid split
checks manifold output and conservation of volume before committing. Keep Both
creates separate objects by default, with a combined-mesh option. New brush IDs
must differ even when object settings are copied. Failures restore the original
mesh and remove temporary objects and data.

Visible modifiers are rejected because cutting raw base geometry while displaying
an evaluated mesh would make the preview dishonest. Finalization is an explicit
authoring boundary, not an implicit side effect of the cut.

## Cap materials

The cutting volume gets one material chosen from slots actually used by target
faces. Empty/unused slots are ignored. The same material and projected UVs transfer
to the new caps on both results. Existing face assignments remain intact.

```{code-sample} addon/wavelength/source/cutter_solid.py cap-materials
```

## Face assignment

Change polygon/BMesh material indices, not the contents of a shared material slot.
Auto scope follows Object/Edit Mode. A direct click targets a hit face, while an
Edit Mode drop targets selected faces across edited meshes and falls back to the
hit face only when the selection is empty. Object scope is an explicit override.

```{code-sample} addon/wavelength/source/asset_placement.py selected-face-drop
```

Update persistent texture records with the material path and preserve neighboring
UV/projection data. Use the existing busy guard when a direct assignment would
otherwise trigger the legacy dependency-graph material synchronization.

## Native vertex editing and live projection

Native Blender editing remains responsible for geometry and selection. The live
projection timer reads the Edit Mode BMesh rather than the uncommitted Mesh
datablock. Geometry/material/projection inputs are tracked separately from UVs so
writing preview UVs does not trigger a feedback loop. Temporary non-planarity is
allowed during interaction; export validation remains a separate boundary.

```{code-sample} addon/wavelength/source/editor.py live-edit-projection
```

## Terrain and engine evaluation

Terrain editing, procedural evaluation and Source displacement export are separate
steps. Do not make a general mesh representation depend on Source displacement
rules. Tests of Blender stitching do not replace engine neighbor/seam validation.

## Geometry Nodes generation boundary

`node_primitives.py` builds versioned native primitive/parametric graphs.
`node_pencil.py` maps native curves to mesh outputs and temporary cutting volumes.
Python supplies scalar parameters and curve control data, validates evaluated
geometry, manages object ownership and commits successful operations. Generated
mesh vertex positions are computed by nodes. The modal wire preview remains a
lightweight interaction proxy. Legacy Python generator identifiers are preserved.

Pencil Fill Curve is evaluated in a flattened local plane, then restored with its
plane offset. Closed extrusion adds a reversed bottom cap and welds its boundary;
the top is shifted to support oblique XYZ extrusion. Signed extrusion reverses
winding when necessary. Straight guides use their control polygon; curved guides
retain native Bezier sampling. Object Info dependencies propagate curve edits.

Exact Boolean nodes have a multi-input mesh socket for intersection and separate
operands for difference. Compact material slots before Boolean evaluation and
remap polygon indices explicitly. The optional combined result also needs a
shared material palette; concatenating BMeshes without remapping loses textures.
Preserve all data layers when committing evaluated meshes, and restore the active
UV layer when the evaluator returns no active layer.

Finalization is explicit. Primitive assemblies retain profile ownership and BSP
validation. Pencil outputs bake their evaluated graph and detach from the guide.
No automatic migration of existing saved generators occurs on load.

## Native transform interface and exclusive shortcuts

`transform_bridge.py` adapts the native Move, Rotate, Scale and Transform tool
identities per context. It keeps the existing wavelength controller/backend and
removes the duplicate engine transform buttons. Engine transforms currently
apply in Object Mode for engine profiles using Grid: Profile; other contexts
retain native Blender tools. The current controllers use world axes and the
active object's pivot, as before this interface consolidation.

```{code-sample} addon/wavelength/source/transform_bridge.py transform-routing
```

The Windows native event patch skips competing plain G/R/S transform keymap
entries only when `WAVELENGTH_OT_transform_route` polls in the event's context.
The addon binds those keys to the route operator, which invokes the existing
undoable move/rotate/scale operators. No keymap item active flags or user
preferences change. Explicit native operator calls, transform modal keymaps,
Edit Mode and other workspaces remain native. This also avoids the cross-window
race inherent in globally toggling shared keymap flags from a timer.

A small synchronization timer refreshes tool runtime bindings on context changes;
keyboard exclusion itself is evaluated synchronously for each event. Disabling
the addon restores native tool definitions and workspace runtime bindings. The
matched native executable and addon must be installed together for exclusive
keyboard routing; the current filter is part of the Windows candidate patch.

## Localized validation feedback

`geometry_diagnostics.problem` calls the same pure convex validator used by
export, then identifies the implicated vertex/edge/face indices using its exact
coincidence rule and tolerance. It reports the first geometry failure per brush;
repairing that failure allows the next one to become visible.

`geometry_debug` owns scene issue records, viewport overlays, native selection,
coalesced refresh and error capture. Brush exceptions carry structured
`object_name` metadata through export wrapping. The persistent logger queues only
that name; the main-thread timer reads Blender meshes. Existing Map Problems and
Validate actions reuse the same scan. No text parsing of human error messages is
needed to identify the object.

Edit Mode scans read the live BMesh. Modifier outputs use temporary evaluated
meshes and release them; evaluated indices never select base-mesh vertices.
Rendering uses cached diagnostic snapshots and only transforms referenced points.
Dependency updates recheck existing problem objects, not the entire map on every
mouse move. Repair selection remains a normal undoable Blender operation; scans
and overlays never merge, dissolve, delete or finalize geometry.

Draw handlers, timers and dependency/load callbacks are removed on unregister.
The context gate hides overlays outside wavelength and clean rendering. The
issue list is diagnostic state, not export geometry or an automatic repair pass.

## Shared CSG and convex BSP conversion

`csg.start` attaches the existing `node_pencil.boolean` graph to the target. It
stores the owning engine, modifier name, cutter pointer and reversible operand
settings on Blender IDs, so the editable preview survives saving and loading.
`csg.cancel` restores those settings. Operators are registered for the add-on
lifetime and poll the context policy; changing workspace does not bake geometry.

`csg.finalize` evaluates a temporary mesh and requires consistent closed manifold
geometry. Free profiles retain that evaluated mesh and its UV layers. BSP profiles
call `_bsp_meshes`, which transforms into engine units and delegates to the pure
`bsp_decompose.decompose` module. The converter splits a bounding convex cell by
unique boundary planes, classifies cells using the triangulated surface's solid
angle, validates every retained cell with the export validator, and checks volume
conservation. Limits bound plane count, intermediate cell count and total work;
it does not voxelize, quantize or approximate a surface with a convex hull.

Copies, mesh data, brush IDs, face metadata and projected engine UVs are prepared
before replacing the original target. Material indices follow matching boundary
planes; internal partition faces use a material present on the evaluated solid.
Empty cap slots inherit a used target material. This first implementation resets
engine UV projection on BSP outputs; it does not preserve custom per-face offsets
or minimize/merge the convex partition. Complex meshes should remain models.

`cutter_solid.apply` reuses the same conversion for pencil solid cuts. Map export
rejects live CSG; profile changes request finalization or cancellation. Construction
cutters remain excluded after commit, and cancellation restores their prior flags.
Tests cover holes, concavity, disconnected solids, transformed coordinates, winding,
limits, live node changes, cancellation, exportable materials, and failure rollback.

## Static mesh engine adapters

`mesh_assets` is separate from `scene.export_map` and the BSP compiler pipeline.
Profiles opt into `mesh_export`; Godot/Source 2 explicitly disable convex-brush
requirements and entity support. `profiles.PROFILE_ITEMS` assigns explicit,
stable RNA enum numbers to preserve existing .blend profile selection.

Candidate meshes are evaluated through the source dependency graph into a
temporary scene. Geometry is transformed into metres for Godot or Source units
for CS2; mirrored transforms have their winding corrected. Copies of materials
and images provide export-local PNG references. Unsupported base-color shader
graphs fail preflight instead of silently generating an unrelated material.
Cleanup restores the window scene and removes temporary Blender IDs on failure.
The real window scene must match the context override because Blender's glTF
exporter calls `frame_set`/dependency evaluation through the global context.
`use_active_scene=True` prevents accidental export of the authoring scene.

Godot uses Blender's GLB exporter without animations, lights, cameras or extras.
CS2 uses FBX with Z-up axes, a minimal ModelDoc36 document and DefaultMaterialGroup
remaps, and csgo_complex VMATs. FBX global_scale=.01 compensates Blender's
centimetre conversion; inspecting CS2's compiled bounds verified a two-metre
cube becomes 78.74016 Source units, rather than 100 times that size.

All source files are prepared in a dedicated temporary directory before copying
generated assets into the named package. A manifest records current files,
original mesh names/counts, scale, axes and conversion warnings. Unrelated files
and unused files from older exports are retained. This is not an atomic
multi-file transaction if filesystem writes fail during publication.

Engine tests check Godot-imported texture pixels, UVs, physical bounds and axes,
and CS2 resource-compiler success, material references and compiled bounds. This
path does not implement VMAP serialization, CS2 resource extraction, entities,
collision, animation or automatic deployment/compilation.
