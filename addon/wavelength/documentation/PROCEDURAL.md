# Procedural geometry boundaries

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

A future Geometry Nodes adapter should consume the same definition and expose
evaluated mesh output to the same validator/finalizer. It must explicitly version
its node group and define BSP conversion requirements. The first Geometry Nodes adapter now handles new straight stairs. Curved stairs
and arches retain the Python adapter; the contextual dependency engine is future work.

Profile switching prompts/conversion and workspace Active/Suspended state are
separate future integrations. This increment does not auto-finalize on switching,
reassign existing geometry, or implement a full workspace suspension policy.


## Straight stairs: Geometry Nodes v1

New straight stairs use `wavelength.geometry_nodes.straight_stairs` with a live
modifier and shared, inspectable `Wavelength · Straight Stairs · v1` node group.
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
Existing Python definitions and legacy stairs remain Python-generated. New curved
stairs and arches also remain Python-generated until their node adapters land.
