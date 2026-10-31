# Source 1 displacements

Displacements are editable grids attached to four-sided brush faces. Their
backing brushes, material names, texture axes, Source units and per-surface
metadata remain part of the map. Imported grids are ordinary editable Blender
meshes; they are not reconstructed from a procedural heightmap after editing.

## Import

1. Activate the Source game profile that provides the map's materials and models.
2. Use **File > Import > wavelength IO**, then choose the `.vmf`.
3. Select a displacement surface in the viewport. Its backing brush remains in
   the Outliner; its ordinary sides are hidden by a display-only modifier.

The importer supports powers 2, 3 and 4, corresponding to 5×5, 9×9 and 17×17
vertices. Floors, walls, ceilings and sloped quad faces use the same system.
The original start-corner hint determines row orientation. Vector offsets and
elevation are included in the visible geometry. Original metadata, including
optional and branch-specific multiblend fields, is retained on export.

> Screenshot placeholder: imported displacement, backing brush in the Outliner,
> and the Source Displacement panel.

## Create and edit

Select quad brush faces in **Edit Mode**, then use **Face > Create Displacement
from Face** or search for that command with **F3**. The original brush is retained.
The new surface opens as a native Source grid with its own Object Properties panel.

- **Tab / Edit Mode:** move existing vertices using Blender's native tools.
- **Sculpt Mode:** sculpt the surface without changing its topology. Keep dynamic
  topology disabled. Use **Change Power** to change the grid resolution.
- **Object Properties > Source Displacement:** change power, paint, sew, change
  collision flags, inspect triangle tags, or validate the surface.
- **UV Editor:** affine edits to the continuous `wavelength` UV layer are captured
  as Source texture axes. UV seams and non-affine warps are rejected on export.
- **Change Power:** explicitly resamples the existing shape and blend values.
  Lowering power can remove detail. The operation supports Blender undo.
- **Remove Displacement:** removes the surface and restores its backing face.
  Deleting only the surface with Blender's Delete command leaves a missing-grid
  diagnostic; it does not silently turn the map into a different brush layout.

Topology-changing modifiers, subdivision, extruding, deleting or merging grid
vertices can make the surface invalid for Source export. Validation checks the
vertex identities and Source's alternating triangle topology, not just the count.
Topology-preserving modifiers can be evaluated for export.

## Paint geometry and material blends

Choose **Raise / Lower**, **Smooth**, or **Texture Blend** in the displacement
panel, set the radius in engine units, then press **Paint Displacement**.

- Drag **LMB** to paint; **Ctrl** lowers or erases blend weight.
- Hold **Shift** to smooth geometry.
- Use the mouse wheel to adjust the radius.
- **Enter** or **Esc** ends the paint session; **Ctrl+Z** undoes the completed session.
- A cyan circle shows the brush footprint.

Assigning a material through the texture browser covers the whole displacement
patch, because it is one Source face. Individual triangles cannot have different
Source materials; use separate patches or a transition material instead.

Texture Blend edits the displacement's per-vertex alpha. Assign a Source
`WorldVertexTransition` material to preview its two layers. The image textures
must be available through the active game's material search paths. The native
paint tool currently edits this two-layer alpha, not branch-specific four-layer
multiblend weights; existing multiblend arrays are preserved.

**Paint Across Connected Surfaces** includes neighboring native grids. Painting
then sews compatible boundaries after each stroke. Turn it off when working on
an intentional gap or independently authored boundary.

> Screenshot placeholder: raised terrain, cyan paint cursor and transition material.

## Sew surfaces

Select adjacent native displacement surfaces in Object Mode and choose **Sew
Selected**. **Smooth Seams** also softens the adjacent geometry. Full-edge and
half-edge neighbors are supported, including different powers. Fine edge samples
are interpolated along the common coarse grid so the two surfaces meet between
shared vertices as well as at their corners.

Sewing is explicit: importing a map does not automatically close authored gaps.
Move connected pieces consistently. Arbitrary partial-edge matches are reported
rather than exported as unsupported Source neighbors.

## Procedural terrain

Existing wavelength Geometry Nodes terrain remains procedural. To use native
Source-grid editing, choose **Make Editable Displacements** from its Object
context menu. The evaluated patches become native displacement grids; the
procedural original is retained, hidden, and excluded from export. This is an
explicit conversion so editing an imported surface cannot reset hand-authored
geometry from procedural parameters.

## Export and checks

Use **File > Export > wavelength IO > Source 1 (.vmf)**. Each grid is serialized
onto its original backing face, preserving brush-entity membership and side IDs.
Editor scale is converted back to Source units using the stored object units.

Unchanged imported geometry retains its original displacement fields. Edited
positions are encoded back into displacement vectors and distances while the
original base domain and optional metadata are preserved. Collision flags,
blend values, triangle tags and allowed-vertex data are kept rather than replaced
with export defaults. Explicit power changes reset the old allowed-vertex mask.

**Check Displacement** reports missing backings, duplicate face ownership,
changed topology, non-finite/out-of-range positions and collapsed triangles.
A displacement surface alone, or its entire backing brush, can be duplicated:
the copy gets a consistent backing/grid relationship.

A displacement is not a substitute for ordinary world brushes used to seal a map.
Its backing solid is retained as editable source data, not as a promise of BSP
visibility sealing.
