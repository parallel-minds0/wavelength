# Line / Curve Cutter

```{screenshot} pencil-solid-clipping
:alt: Pencil path, depth preview and Keep Both separate-object result
Capture the depth preview with the header options visible, then the two capped output objects.
```

Choose the pencil below Create Brush in the wavelength workspace. Select a mesh
first to make it the cutting target. Clicking the pencil automatically enters Mesh
Edit Mode and activates the cutter. Highlighting and snapping read live edited
vertices and edges. You can also set Target Mesh after drawing. The tool is
also available in Mesh Edit Mode near Blender's Knife tool.

Closing an outline starts mouse-driven extrusion automatically. Move the mouse
to set height, then click or press Enter to finish. Faces mode creates one mesh;
solid cutting follows the Keep and Separate Objects settings. This uses the brush
primitives' height interaction and Blender/profile grid snapping. Type a number
for an exact height in profile units; Esc cancels without creating geometry.

In Faces mode this creates a new extruded shape. In Split/Subtract mode it sets
the cutting depth and applies the cut on confirmation. Shift+C closes a guide
without extrusion, or turn off Auto Extrude in the tool header. Enter during
point drawing finishes an open guide in Faces mode. In Split/Subtract mode, Enter
applies the active solid cut, just like K. Shift+Enter keeps an open guide without
cutting in either mode. E starts extrusion from an open path.

| Input | Action |
| --- | --- |
| Click | Place a corner |
| Click-drag | Place a curved point and pull its tangent handles |
| Enter | Faces: finish an open guide; Solid: apply the open cut |
| Shift+Enter | Finish an open guide without cutting |
| K while drawing | Finish the open guide and apply the cut |
| Click first point / C | Close outline and start mouse-driven extrusion |
| Shift+C | Finish a closed guide without extrusion |
| E | Start mouse-driven extrusion from an open path |
| Backspace | Remove the last point, or edit numeric input |
| X / Y / Z | Choose world cutting direction and enable solid cutting; repeat to restore surface normal |
| V | Toggle Faces / Split Solid |
| D | Toggle through-all / finite depth and enable solid cutting |
| B | Cycle Keep Both / Outside / Inside and enable Split Solid |
| Shift + wheel | Cycle Keep mode forward/backward, including during depth extrusion |
| Type a number | Set the next segment length in profile units |
| Esc / right click | Cancel the unfinished guide |
| Wheel | Adjust depth in finite-depth mode; otherwise zoom |
| Middle mouse | Viewport navigation |

Points follow ray hits on the target mesh. Outside its silhouette, placement
continues on the initial surface plane so an open cut can extend past a face.
The initial normal also defines the knife projection direction. Blender's snap
toggle, targets and Ctrl inversion govern placement; engine grid spacing comes
from the active profile. Snapped points stay on the hit face plane. Shift+Tab
remains available to toggle native snapping. Bezier segments interpolate between
points; they do not wrap automatically around curved surfaces.

## Edit the path

Select the guide and press Tab for Blender's Curve Edit Mode. Use the normal
point, handle, subdivision and cyclic-curve controls. Changes update the visible
guide immediately and leave the target mesh untouched.

Curve Resolution controls how many straight knife edges approximate each curved
segment. Straight segments remain single edges.

## Face or solid operation

Choose **Faces**, **Split Solid**, or **Subtract** in the tool header, before drawing
or on the finished guide. Faces splits surface topology, including open meshes.
Split Solid keeps both capped parts as separate objects by default. Disable
**Separate Objects** beside Keep Both to retain them in one mesh instead. Subtract
removes the region inside a closed outline. Solid operations require a closed,
manifold target mesh. Draw open splits across the silhouette of the whole object.
Finalize procedural geometry or apply visible modifiers before cutting. The cutter
rejects live modifier stacks so it cannot cut a different base mesh from the one
shown in the viewport.

**Through All** spans the target volume. Disable it and set
**Depth** in profile units to cut inward from the initial drawing plane. Open paths also support finite depth. Curves are sampled at Curve Resolution; volume
operations project the path onto the initial plane and extrude along its normal.
Choose Keep Both, Outside or Inside for Hammer-style clipping. Self-intersecting outlines are rejected. The guide remains available afterward.

**Keep Both leaves the outer silhouette unchanged.** Its result contains two
separately selectable capped objects. If Separate Objects is disabled, the two
disconnected capped volumes share one mesh instead. Choose **Keep Outside** or
**Keep Inside** to discard one side and see the clipped shape immediately.
The tool-header Keep menu sets this before drawing or on a finished guide. During
drawing or depth extrusion, B and Shift+wheel change it without altering depth.
The drawing header always shows the current Keep choice. Starting a new drawing
uses the same settings shown by the tool header.

New cut faces inherit one material actually used by the target's faces, with
projected UVs. A single-texture object reuses that texture; if multiple textures
are in use, one is chosen randomly for the cut. Empty and unused slots are ignored.
Both retained pieces use the same chosen cut texture.

The cutter always targets nearby vertices and edges, even with Blender's global
snap toggle off. Grid snapping still follows Blender's snap toggle and profile. Vertices within 14 screen pixels take priority,
then edges, then the profile grid. Occluded geometry is excluded. The target
vertex or edge highlights orange; faces are never highlighted; the placement cursor is orange for geometry
snaps and green for face/grid placement. The oriented ring, crosshair and normal
stem appear before the first click and follow the live point while drawing.
Hold Ctrl to bypass vertex/edge magnetism. Ctrl still inverts grid snapping,
and Shift+Tab toggles Blender grid snapping normally.

## Choose an explicit action

The active tool header and Object Properties → wavelength Cutter expose:

- **Apply Cut**, or **K** with the cutter active: split the target's faces using
  Blender's Knife Project in Faces mode. Solid modes instead use capped exact
  Boolean difference/intersection. Projection follows the guide's stored plane normal,
  including object rotation, and restores your viewing angle afterward. Cut
  Through includes occluded faces. The target enters Edit Mode for inspection.
  Faces mode retains both sides of each cut face. Solid modes keep the chosen
  side(s), or remove the inside volume in Subtract mode. Ctrl+Z undoes the cut,
  and the guide is retained.
- **Create Geometry**: create a separate ordinary mesh. Choose Edges for an open
  or closed mesh path, Face for a closed planar outline, or Extrusion with an
  explicit height in profile units. Open-path extrusion produces a surface strip;
  closed-path extrusion produces a solid. The target mesh is not modified.
- **Keep Guide**: select the editable curve and leave geometry unchanged. The
  guide is hidden from renders and excluded from map export.

If no target was selected, the first surface hit can assign one. Target Mesh can
always be changed in the header or drawing panel. Failed or missed cuts restore
the original mesh. Shared mesh data is isolated so linked duplicates are not cut.
UVs and material slots are preserved through native knife projection.

Created meshes are not automatically tagged as engine brushes. Existing brush
export rules still apply after topology editing: convex solids and merged
coplanar faces are required for brush export.

The previous parallel-copy, array, terrain, displacement and scatter controls have
been removed from this tool. Existing objects from that workflow are left intact.

## Development checks

- `tests/blender_pencil.py`: background guide/geometry and restricted addon enable tests.
- `tests/blender_cutter_knife.py`: GUI native knife, curved cuts, Edit Mode, rollback,
  shared-data isolation, material/UV and viewport restoration tests.
- `tests/blender_pencil_controls.py`: GUI gestures and native undo, using
  `--enable-event-simulate`.

GUI fixtures disable preference saving and store recovery files under `build/cutter`.

## Live generated geometry

Create Geometry now adds a Geometry Nodes modifier driven by the native guide
curve. Edit that curve to adjust the output, and use Height / Direction on the
guide to adjust extrusion. Closed outlines produce one capped mesh; open paths
produce an extruded strip. Use **Finalize Geometry** on the output before ordinary
vertex editing or cutting the generated result. Finalization keeps the current
mesh and disconnects it from subsequent guide edits.

The existing Faces, Split, Subtract, Keep and Separate Objects controls remain.
Solid cuts use node-generated volumes and exact Boolean evaluation; the resulting
cut pieces are committed meshes, ready for native editing.

## Profile-grid drawing depth

When the profile uses its **Profile** grid, empty-space placement uses a
world-origin plane aligned with the view's main axis. It does not switch planes
as the pointer moves across a perspective viewport. Starting on a surface uses
that surface plane. A pencil stroke stays on its initial plane rather than
following other surfaces behind or in front of it. Vertices and edges on that
plane remain available as snap targets.

With Blender grid snapping enabled (Increment/Grid), points align to the profile
grid's world origin and selected spacing; they do not inherit an arbitrary offset
from the previous point. The chosen surface depth is preserved. Blender's snap
toggle and Ctrl inversion still control grid quantization.

This policy only applies when **Grid: Profile** is active and the profile defines
a grid. Metric/free profiles retain their normal surface following and Blender
snapping. A grid is a separate profile capability from BSP/convex brush rules.
