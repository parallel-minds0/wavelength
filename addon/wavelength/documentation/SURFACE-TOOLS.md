# Surface textures and the asset picker

## Click placement

Select a texture or point entity in the Asset Browser. **Click Place** activates
automatically. Click the level repeatedly, or drag a texture from its tile onto
the level; both paths use the same assignment rules.
Texture dragging also works with Click Place stopped. In Edit Mode, a Surface/Auto
drop applies to the selected faces across meshes being edited, preserving all other
faces. If no faces are selected, it paints the face under the drop. Shift-click
remains available to select additional faces while Click Place is active.
You can select another browser item while the mode remains active.

- **Auto** (default) paints the whole object in Object Mode and the hit face in Edit Mode.
- **Surface** overrides Auto and paints only the clicked face in either Object Mode or Edit Mode.
  It does not require selecting that face first, and leaves neighboring face
  assignments, UVs and Edit Mode selection intact.
- **Object** paints the whole clicked mesh or locked brush assembly.
- An entity is placed at the surface hit point. Empty space uses a plane through
  the 3D cursor. Blender's grid snap controls apply; placing never moves the cursor.

A green 3D cross shows the placement point. Middle mouse navigation and zoom remain
available. Each successful click has its own undo step. Press **Esc**, right-click,
or **Stop Placing** to end the mode. Profile, scene and Wavelength context changes
also stop it. Point entities can be placed in Object Mode; brush entities require
their normal brush-geometry workflow. Generated topology must be finalized before
individual evaluated faces can be textured reliably.

## Apply to selection

In the Asset Browser's **Textures** section, select a material and press **Use Asset**.
In Edit Mode this changes only selected faces, including multi-object mesh editing.
In Object Mode it changes whole selected meshes and locked brush assemblies.
Brush face texture metadata and viewport UVs stay synchronized. Choosing a material
preserves existing mapping; **Apply Mapping** deliberately applies the settings.

Open **Texture Settings** in the browser header or its Wavelength Assets panel.
It contains shift, rotation, signed U/V scales, flip, mapping copy/paste, Fit,
Center and edge justification. Valve profiles support world or face-plane
alignment. Source 1 additionally exposes lightmap scale. These are brush mapping
controls; ordinary model UVs continue to use Blender's mesh UV editing tools.
This is not a complete implementation of Hammer 2's material editing system.

Click the eyedropper in the browser header or **Pick** in its left panel, then
click a surface in the viewport. A brush face picks its engine texture and mapping.
An entity model or icon picks its entity class. Hold Shift while clicking to
force texture picking from an entity model. Esc/right-click cancels.

**Use Held** applies the held texture to selected brush faces/objects or places
the held entity class at Blender's 3D cursor. Picking leaves scene geometry and
selection unchanged. Entity picking holds the class, not the original entity's
unique name, links, transform or custom property values. Held assets are tied
to their engine profile; pick again after changing profiles.
