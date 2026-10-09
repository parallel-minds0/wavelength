# Foundation, native assets and standard primitives

Scope: init.txt milestones 1 and 2, plus WP-029/030/031. No prop-production,
CSG, new engines, Pro procedural features, or HL2 runtime repair is included.

## Use

Install the add-on ZIP in Blender 5.2.2 (Preferences → Add-ons → Install from Disk),
enable Wavelength, then open the `wavelength` workspace tab. The workspace is
created once and saved with the .blend. Existing workspaces are not rearranged.
A large viewport, native Asset Browser, Outliner, inspector and Wavelength sidebar
are provided. Engine/profile controls are in the sidebar. Save the startup file
if this layout should be your personal default.

This milestone runs on an **unpatched Blender**. It does not need the old
experimental embedded-shader patch. The old native installer remains a separate
experimental path; do not patch Blender merely to get this map-unit overlay.

- Select an engine, then enable Engine grid mode. Blender's adaptive grid stays
  unchanged. A separate world-position shader draws the exact selected interval
  in yellow. Subpixel highlights fade; larger native grid lines remain neutral.
- The workspace's Editing, Grid, Snap, Handles and Live UV switches control effects.
  Leaving the workspace disables its overlay, G binding and gizmos. Object IDs
  and persistent data infrastructure remain registered.
- G uses an undoable exact engine-grid move in Object Mode. X/Y/Z constrain it,
  numeric input is in engine units, Ctrl permits free movement, Esc restores the
  original matrices. The Engine Grid Move toolbar tool provides matching arrows.
  Ordinary Blender Move remains available. Edit-mode native transforms remain
  Blender's; Snap Selection to Grid explicitly quantizes selected vertices.
  The previous settle-time matrix-correction timer is no longer registered.
- Use Shift+A → Mesh → Stairs/Arch/Sphere, or their sidebar buttons. Parameters
  remain stored on the parent. Select the parent or a child and choose Primitive
  Parameters → Edit Parameters. Each operation participates in Blender undo.
  Stairs expose count/rise/run/width/landing/direction. Arches expose
  radius/thickness/depth/angle/segments/direction. Spheres expose radius and
  20/80-face polyhedral detail. Move/rotate the parent to orient the assembly.
- Existing face material assignments are preserved by part/face index on
  regeneration; newly added parts inherit the last existing part's materials.
  Arbitrary child mesh edits are replaced when regenerating; keep a duplicate
  before making destructive changes to generated children.
- In the native Asset Browser, select Current File, then Publish Game Assets.
  Filter the category/name; publishing is bounded to a configurable batch.
  Existing material assets are reused. Select Use Asset to apply materials to
  selected brush faces/objects or place model/entity/sound proxies at the cursor.
  Native material drag/drop is also available. Assets/previews persist in .blend.
- Materials use existing WAD/VPK/VMT/VTF readers. Model bounds use checked MDL
  headers; model tiles are labelled placement proxies, **not decoded meshes**.
  Named particle effects require entering the actual effect name from the PCF.
  Unsupported engine/category combinations report errors, never invent entities.
  Decal and sky materials are discoverable as categories. This does not implement
  a projected-decal editor or environment/sky-authoring workflow from later milestones.
- User Profiles supports create, save/edit, duplicate, rename, delete, import,
  export and validation. Data lives in Blender's user configuration directory
  under `wavelength/profiles`, outside the add-on. Stable UUIDs survive renaming.
  Built-in engine names remain stable; user names add a project hierarchy.
  Coordinate convention is currently Z-up; arbitrary axis adapters are not added.

## Audit and dependency map

`workspace.py` owns activation and layout; `grid.py` draws the independent GPU
highlight; `precision_move.py` owns transactional object movement; existing
`identity.py` owns IDs. No transform-settling handler is registered.
`asset_index.py` records metadata; `asset_browser.py` publishes native assets,
reusing `textures.py`, `source_assets.py`, WAD readers and the entity catalog.
The old gallery backend is preserved but ordinary browsing buttons now publish
native assets. Full dead-code removal belongs to WP-017.
`profile_store.py` handles versioned disk data; `profile_ui.py` handles controls.
`primitives.py` is Blender-independent convex geometry; `primitive_ui.py` owns
persistent Blender assemblies. Existing MAP/VMF serializers remain authoritative.

Free and Pro have separate complete source trees. `tools/sync_editions.py` copies
only an explicit shared allowlist; checks prior hashes before overwriting; removes
only unchanged previously shared files; preserves Pro extension directories;
and never introduces runtime links/submodules. `.wavelength-shared.json` tracks
the common baseline in Pro. Run the same Python and Blender regressions there.
`tools/provision_pro.py` refuses a non-private GitHub target.

## Validation and remaining risks

The committed regression scripts exercise convexity, dimensions, invalid inputs,
profile persistence, asset IDs/cache reuse, Blender registration, primitive
regeneration, object identity, real Source material/MDL assets, and VMF export.
The UI regression creates the workspace once, checks unrelated layout preservation,
native grid settings, the Asset Browser and switching away. A sealed room with
stairs, arch and sphere has been accepted by the installed VBSP++ compiler.

Platform validation is Linux Blender 5.2.2. Native model geometry decoding,
full material dependency graphs, independent asset-library .blend caches,
Edit Mode replacement transforms and Windows interaction testing are not claimed.
The GPU layer should be tested on additional graphics backends. Existing
experimental installer/runtime and game launch limitations remain as documented.
User-authored maps, game installations, installed Blender settings and unrelated
pending deletions were not overwritten by this implementation.
