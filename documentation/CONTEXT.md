# wavelength context

```{screenshot} clean-preview-context
:alt: wavelength Context controls and a clean level preview
Capture the context controls and a clean preview with editor helpers hidden.
```

Open **Scene Properties → wavelength Context** in any workspace.

- **Level Editing** enables wavelength tools in its workspace.
- **Clean Preview** hides editor helpers and pauses tools and asset preparation.
  Game geometry, entity model representations and real lights remain visible.
- **Suspended** pauses wavelength tools and preparation while retaining the
  current authored scene and helper visibility.

Editing Tools, wavelength Overlays and Asset Preparation can be enabled separately.
Show Editor Helpers independently controls viewport helper visibility in editing
and suspended contexts. Clean Preview always hides them. Leaving the wavelength
workspace suspends its tools; it does not change the scene context or finalize
procedural geometry.

Normal Blender renders exclude spawn icons, entity anchors, trigger/clip utility
volumes, cutter guides and diagnostics, regardless of the active workspace.
Actual entity meshes and sunlight remain renderable. Existing user visibility
settings are respected. **Include Helpers in Renders** enables diagnostic renders
outside Clean Preview. Render completion or cancellation restores prior flags.

**Object Properties → wavelength Visibility Role** overrides automatic detection
with Visible Content or Editor Helper. Utility detection hides an entire brush
only when it is a utility entity or all its recorded materials are utility
materials; mixed visible/utility brushes remain content.

Context and roles are saved with the scene. Viewport transitions restore previous
per-view-layer hide settings, including helpers already hidden by the user.
These display policies do not remove entities, change export metadata, switch
profiles or apply geometry finalization. Profile ownership remains a separate
state boundary. Native Blender overlays and compositing remain under Blender's
normal controls.
