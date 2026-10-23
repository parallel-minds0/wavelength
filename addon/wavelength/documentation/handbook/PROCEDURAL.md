# Procedural geometry boundaries

```{screenshot} procedural-finalization
:alt: Procedural brush parameters, node modifier and finalization control
Capture a generated stair or arch with its parameters and Finalize Geometry visible.
```

Each primitive assembly owns a versioned definition (`wl_definition`) independent
of the selected workspace or active profile. It records the owning engine and
saved profile identity, generator identity/version, parameters, units, grid and
geometry constraints. Existing files are migrated lazily on rebuild/finalization.

The current implementation is `wavelength.python_primitives`, version 1.
`procedural.evaluate` returns local-space mesh parts without mutating Blender.
`procedural.validate` checks adapter output and the owner's geometry constraints.
`primitive_ui.rebuild` commits validated output and stores the definition only
after generation. Parameter edits retain the original ownership and unit/grid
snapshot. Unknown generator/schema versions are rejected rather than silently
replacing an object's mesh. The legacy Python generator still validates its BSP
output internally; this is an adapter boundary, not a rewritten generator.

In Object Properties > Assembly & Primitive Parameters, **Finalize Geometry**
bakes each part's evaluated mesh, preserving UVs/materials, owner metadata and BSP
partitions. It validates prepared meshes before replacement, clears baked
modifiers, releases assembly transform locks and sets state FINALIZED. Parameter
regeneration is then rejected. Finalization is an undoable Blender operator.
Stored definitions remain provenance, not a promise of lossless unfinalization.

Creation/parameter confirmation yields PROCEDURAL. FINALIZED stops generator
updates; native mesh editing remains available. The unfinished modal draft stage
remains owned by the existing creation tool in this first increment.

New cubes, cylinders, cones, spheres, arches and curved stairs use versioned
Geometry Nodes generators. Straight stairs retain their existing node generator.
Python owns interaction, parameters, profile validation and assembly bookkeeping;
the graph owns the generated topology and vertex positions. Existing saved Python
definitions keep their original generator, including when parameters are edited.
The contextual dependency engine remains future work.

Profile switching prompts/conversion and workspace Active/Suspended state are
separate future integrations. This increment does not auto-finalize on switching,
reassign existing geometry, or implement a full workspace suspension policy.


## Straight stairs: Geometry Nodes v1

New straight stairs use `wavelength.geometry_nodes.straight_stairs` with a live
modifier and shared, inspectable `wavelength · Straight Stairs · v1` node group.
Step boxes are generated from Mesh Line, Index and Instance on Points nodes.
The Blender output unions the solids into a connected mesh; the BSP output emits
one convex box per identified part. Units, direction, landing, profile output,
UVs, material and face/part IDs are graph inputs or node-generated attributes.
Python installs the graph, normalizes profile parameters, validates evaluated
output and synchronizes the assembly's number of BSP parts on parameter edits.
It does not supply the generated vertex positions to the graph.

Use Edit Parameters on the assembly for changes affecting part count. Raw modifier
inputs are inspectable, but editing structural inputs independently on one BSP
child is not an assembly-level edit. The interactive footprint wire preview still
uses the existing preview path in this initial rollout. A live node-driven modal
preview is a subsequent migration step.

The BSP exporter reads evaluated stair modifiers through a temporary export mesh
and validates the result. Other unapplied modifiers retain the existing export
restriction. Finalization bakes the evaluated modifiers, retaining brush parts.
Existing Python definitions and legacy stairs remain Python-generated.

## Primitive generators and pencil outputs

Create primitives from the existing brush tools. Edit Parameters updates the whole
assembly, including the number of convex parts for BSP profiles. In a Blender
profile, arches and stairs produce a connected mesh. In Source/GoldSrc profiles,
they produce separately validated convex brush parts. Export uses evaluated node
geometry; Finalize Geometry bakes it for native vertex editing.

Pencil guides remain native Blender curves. Create Geometry produces a live node
output: edges, a filled face, an open extruded strip or a closed capped extrusion.
Editing the source curve updates the output. Height and Direction in Drawing / Cut
control extrusion; signed heights and XYZ directions are supported. Finalize
Geometry detaches the output from its guide and bakes the modifier. A guide on
its own remains usable without generating geometry.

Solid cutting uses temporary node-generated volumes and an exact Boolean node,
then commits validated mesh results. Face-only cutting still uses native Knife
Project. Drawing, snapping, preview gestures, Keep and Separate Objects controls
remain part of the interactive tool. The lightweight modal wire preview remains
an interaction proxy; committed geometry comes from the node graph.

## Transform tools

Use Blender's existing Move, Rotate, Scale and Transform toolbar buttons. In an
active wavelength workspace, Object Mode and an engine profile using Grid:
Profile, these use wavelength's controllers. G/R/S use the same backend; X/Y/Z,
numeric engine-unit movement, Enter/click confirmation and Esc cancellation remain.
There is no separate engine transform button row. The controllers retain world
axes and the active object's pivot. Leaving wavelength, suspending it, entering
Edit Mode or selecting a metric/free profile restores native Blender behavior.
Blender's snap settings continue to control quantization.

During Move/Rotate/Scale, selecting X/Y/Z shows the corresponding theme-colored
world-axis guide through the transform pivot. The guide remains visible through
geometry and is removed on confirmation, cancellation or tool cleanup.

## Shared snap controls and native grid commands

The native snap magnet, Shift+Tab and wavelength's Map Snapping button now control
the same Blender snap state. Turning snapping off permits free movement while
retaining wavelength transform ownership. Snap target and per-transform toggles
remain Blender settings; selecting vertices/edges remains a geometry snap target.

With an active Profile grid, native Edit Mode movement and native Shift+S
Selection/Cursor to Grid use the profile spacing, independent of viewport zoom.
Increment movement maps to the profile's absolute grid without changing the saved
snap-target setting. Native Selection to Grid routes mesh/object selections
through wavelength's assembly-aware operation so children do not move twice.
Outside wavelength, suspended contexts and free/metric profiles use native Blender
grid behavior. The boundary resize controller also respects the native snap state.
