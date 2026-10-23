# CSG: subtract, union and intersect

CSG combines two closed solid meshes through an editable Geometry Nodes Boolean.
The **active object is the target**; the other selected object is the cutter.

1. Finalize procedural primitives first using **Object → Finalize Geometry**, F3,
   or **N → wavelength → CSG → Finalize Active Brush**. Do this for each brush.
   Apply any other modifiers to a copy.
2. Select the cutter, then Shift-select the target last. Select exactly two meshes.
3. In the 3D Viewport, press **N → wavelength → CSG**.
4. Choose **Subtract**, **Union**, or **Intersect**.
5. Move, rotate, scale or edit the wire cutter to change the live preview.
6. Select the target or cutter and press **Finalize Geometry** in the CSG panel.
   **Cancel CSG** restores the original target and the cutter's previous settings.

The original target mesh stays intact while the preview is live. The cutter is
excluded from map export and normal rendering. After finalization it remains as
a hidden, excluded construction object; show it from the Outliner if needed.
Do not delete the cutter before finalizing or cancelling the operation.

Basic wavelength brushes have an assembly wrapper and a child mesh. After
finalization, selecting that single-mesh wrapper is supported: CSG resolves the
mesh and counts the wrapper/child pair as one operand. Finalize **each** brush
before selecting the pair. An empty modifier list on the wrapper does not mean
its child generator has been finalized. For multi-mesh assemblies, select an
individual finalized mesh instead.

```{screenshot} csg-live-preview
:alt: A selected wall with a wire doorway cutter and the wavelength CSG panel
Capture the live preview before finalization, then the resulting convex brushes.
```

## Profile-specific results

For the Blender profile, finalization bakes a single mesh object. Disconnected
solid components may remain inside that mesh.

For Source, GoldSrc and Quake profiles, finalization partitions the Boolean
result into separate closed, convex brush objects with planar faces. The volume
and boundary planes are preserved without rounding to the profile grid. Brush
entities retain their entity membership. Resulting brushes receive distinct IDs,
face IDs, materials and projected engine UVs. An untextured cutter inherits a
used material from the target; a textured cutter can supply its own cap material.

This initial converter prioritizes valid geometry over a minimal brush count.
It is limited to 96 distinct planes, 512 partition cells and 50,000 cell/plane
checks. Detailed curved or imported assets can exceed these limits; simplify the
solid or use the model pipeline. A failed or empty conversion preserves the live
preview and original meshes rather than committing partial geometry.

Live CSG must be finalized or cancelled before switching profiles or exporting a
map. Changing workspace or suspending wavelength does not finalize the operation;
the node preview remains part of the scene.

The pencil's solid cuts use the same BSP conversion. For BSP profiles, separate
convex brush objects are required even when the pencil's combined-mesh option is
selected. Face-only cuts keep their existing behaviour.
