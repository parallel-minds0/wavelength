# Editable model assets

A model asset is an editable source document, separate from a placed map entity.
The common model pipeline owns source provenance, profile ownership, object
membership and asynchronous build jobs. Engine adapters decode game files and
compile the edited sources. Source 1 is the first adapter.

## Import and edit

With a Source 1 profile selected, drop an `.mdl` into a 3D viewport, or use
**File > Import > wavelength Model IO**. Keep matching `.vvd` and `.vtx` companions
beside the MDL; external animation blocks also need their `.ani` companion.
Materials resolve through the selected game's mounted assets. Missing materials
are reported rather than silently replaced with an unrelated profile's texture.

The imported asset contains ordinary independent mesh data, UVs, material slots,
and, for supported animated models, an armature, vertex groups, Blender actions
and named NLA clips. Editing it does not alter shared game-model previews.

[SCREENSHOT: imported model asset with mesh, armature and animation clips]

## Publish

Drag a source object's entry from the Outliner into the asset browser's **Models**
section. This uses Blender's native object-ID drag; dragging inside the viewport
continues to use Blender's normal selection/transform tools. Alternatively use
**Object Properties > Model Asset > Publish Model**.

The **Publish Model** dialog lets you choose a target profile, model name and
output directory. Enable **Deploy to Game** to install the result, and optionally
include an editable package. Successful publishing remembers these choices for
this asset. Independent variants start with their own defaults.

Compilation runs as a modal background process with a retained compiler log.
Escape cancels it. Successful output is validated before deployment to a managed
`models/wavelength/<identity>/model.mdl` path, with its companion/material files.
The original game model is never overwritten. The selected profile must match
this asset's owning profile and game directory. The installed Source compiler is
required. Save the blend file to retain editable sources and asset identity.

Publishing makes a model available in the Models browser; it does not place a map
prop. Dropping an existing browser model onto `prop_static` remains an assignment
action. Animated output uses a dynamic model build, not `$staticprop`.

[SCREENSHOT: source-object drag into Models browser and resulting compiled asset]

## Create a Source 1 model from your own mesh

For a standalone asset, select your meshes in Object Mode under a Source 1
profile. Choose **Object → Create Model Asset** or the same entry in the
right-click menu, enter a name, and confirm. The active object's position and
rotation define the asset origin. Existing mesh scale stays in the source
geometry. Modelling controls referenced by supported modifiers are included.

The **Model Asset** panel then provides source selection, collision settings,
attachment and publishing. Original collection membership and material sharing
are retained. Use **Make Model Unique** when you want independent materials and
geometry. Creating the asset marks its sources as model content for map export.


Place a model entity such as `prop_static`. In Object Mode select your source
meshes and make the entity active, then use **Object Properties > wavelength
Custom Model > Assign Selected Model to Entity**. Building the map compiles its
model dependencies. The mesh world placement and rotation are preserved; the
compiler cancels StudioMDL's default 90-degree SMD yaw conversion explicitly.

To check an attached Source 1 model before building, select its entity or a source
mesh in Object Mode. In **Object Properties → Wavelength Custom Model**, choose
**Check Model for Compilation**. Open **Text Editor → wavelength Model Preflight**
for per-source triangle counts and the first blocking error. The check generates
model inputs in memory. StudioMDL and the game still perform their own checks.

In that panel, **Collision** offers:

- **None**: no generated collision model.
- **Auto Convex Hull**: one simplified convex hull around the render geometry.
- **Auto Box**: a simple bounding box around the render geometry.
- **Use Collision Mesh**: pick a separate mesh with the eyedropper. A convex hull
  is compiled from it; it need not belong to the model source collection. This
  mode does not preserve concave recesses. The chosen mesh is excluded from world
  brush export while attached as a collision source.

For managed static and dynamic props, **None** also exports the placement as
non-solid. The editor retains the authored entity properties. Excluding an
assigned collision source from export also disables that prop's collision output.

An assigned render mesh may also be selected as its own collision source. It
continues to supply visible triangles; only a separate collision-only helper is
omitted from render geometry. Sharing these roles must not exclude the prop or
its model build.

In **Model Asset**, choose **Preview / Refresh Collision** to display the generated
collision as a green wire overlay. It uses the Source exporter collision output.
Refresh after changing geometry, placement or collision settings. **Clear Preview**
hides it. The snapshot is cleared when loading a file or using undo/redo.
The preview requires valid model UVs and other exporter inputs.

Choose **Game Directory** deployment for loose compiled files, or **Inside BSP**
to package them into the map. Loose files use `models/wavelength/<identity>/`
and `materials/wavelength/<identity>/` beneath the selected game directory.
Rebuild previously compiled models after changing the rotation/collision settings.

The source geometry remains editable while assigned. For managed assets, use
**Detach Model** in the Model Asset panel to create an independent working copy;
the placed model stays unchanged. Older unmanaged custom definitions retain the
legacy **Detach Custom Model** binding-removal action. Use **Edit Model** to adopt
an older definition into the managed lifecycle. **Alt+P > Clear Parent (Keep
Transform)** changes parenting only; it does not create an independent asset.

[SCREENSHOT: assigned custom model with collision selection and deployment]

## Model origin

Place Blender's 3D cursor at the desired pivot. Select the model source or an
attached placement, then choose **Model Asset → Model Origin to 3D Cursor**.
The model keeps its visible geometry and origin orientation. Its placement
coordinates change to account for the new pivot.

This edits the shared model pivot and compensates all linked placements.
Use **Make Model Unique** first for an independent pivot. Bake animated or
constrained placement transforms before changing the origin. Refresh collision
preview afterward.

## Named model revisions

Set the scene's project directory, select an editable asset, and open
**Object Properties → Model Asset → Revisions**. Choose **Save Named Revision**
and enter a checkpoint name. Save the blend file to retain the revision list.

**Open as Variant** restores a checkpoint as an independent editable model at
the asset's current origin. You can inspect it, publish it, or use **Attach
Model to Entity** to replace a chosen placement.

With an attached model entity selected, **Restore Placement** applies the chosen
revision to that entity. It first saves a **Before revision restore** checkpoint
of the current source. Other linked placements keep their existing model.
The restored asset retains the revision list, including the automatic checkpoint.

Checkpoint files live in
`.wavelength/model-revisions/<asset identity>/` inside the project directory.
Keep these files with the project. They contain editable source packages and
are checked for changes before restoration. Moving the project currently
requires importing a checkpoint package manually if its recorded path changes.
Blender modifier toggles remain available for viewing individual stages of
the current model.

## Current Source 1 scope

MDL versions 44–49 with VVD4/VTX7 render geometry are supported by the mesh reader.
The animation adapter handles ordinary compressed skeletal tracks, raw transforms,
external animation blocks, sectioned clips, names, frame timing and looping.
Runtime blended sequence graphs, additive clips, IK/root-motion tracks and included
sequence models are explicitly rejected for editable animated import. Facial
flexes, attachment/physics reconstruction and event export are not implemented;
sequence events produce a warning. This is an editable render-mesh/skeletal-clip
workflow, not a lossless decompiler for every Source runtime feature.

## In-level modelling: phase one

Select a placed model entity (or its visible representation), then choose
**Object > Edit Model**, the same action in the right-click menu, or
**Object Properties > Model Asset > Edit Model**. Source 1 models are decoded
straight from the active profile's mounted folders/VPKs, including companion
files and material references. The editable geometry opens at the entity's
position and rotation using the profile's engine units. The original game asset
and preview cache are retained. Use Blender's normal modelling tools and
modifiers; wavelength adds no custom curving tool.

The **Model Asset** panel shows how many placements share the asset. **Edit Shared
Model** selects the original source objects and updates all their linked placements.
Source geometry can be at the original placement's location. Use **Make Model
Unique** first when your changes should affect only the selected placement.

**Source Parts** lists the asset's objects. Click a name to select that source,
or choose **Select All Source Parts**. Each inclusion control follows the same
policy as the Outliner and engine tree.

To add parts, select the new meshes or modelling controls together with an
existing source and make the existing source active. Choose **Source Parts →
Add Selected Parts**. The parts keep their world placement and join the shared
definition, including all its linked placements.

The **X** beside a source releases it from the asset while retaining its object
and geometry in the scene. Released parts remain excluded model content; use
**Create Model Asset** to start a separate asset from them. Required controls,
assigned collision sources and the final mesh must be resolved before removal.

The Model Asset panel and Object menu provide:

- **Detach Model:** creates an independent editable copy at this placement.
  The placed model and other placements remain unchanged. Geometry, materials,
  static texture image buffers, shader node groups, rigs and supported actions
  are separate. Owned images are packed into the blend on save; their original
  file paths are not writable destinations. Move the copy or hide the original
  using Blender if overlapping copies make editing inconvenient.
- **Make Model Unique:** makes only the chosen placement use an independent
  variant. Other linked placements retain their original asset.
- **Attach Model to Entity:** select the editable sources, then make the target
  entity active and click this button. Attaching an unbound asset preserves its
  current world geometry. Attaching an already placed definition creates a
  linked placement at the target. Attaching to an occupied entity explicitly
  replaces that placement's model while retaining the old definition.
- **Compile Model to Game:** retains the existing Source 1 compiler workflow.
  Standalone builds use a private compile origin, not an extra map prop. Edited
  clip names/ranges remain authoritative when building a detached asset.

Native duplication of an entity shares its editable definition and supplies a
linked viewport representation. Use Make Model Unique before editing one copy
independently. Mesh/rig data and modelling controls owned by a variant are
remapped to that variant. Existing Blender curve/lattice modifiers stay ordinary
Blender tools. External level-mesh references are not automatically pulled into
an asset; include such modelling dependencies explicitly when needed.

Asset identity and dependencies survive save/reopen. Detached sources remain
ordinary Blender objects and can be exported through Blender's native exporters,
or appended into a standalone scene. They are excluded from wavelength's world
brush export, while their standard Blender render/export inclusion flags remain
under your control. The owning profile/game must be active for attachment. Compilation uses an isolated target snapshot without switching the level profile.

Existing Source 1 animation/decompiler limitations above still apply. Tiled,
movie and multiview images require baking to static images before independent editing.

## Compile, convert and package

Select an editable source, then open **Object Properties → Model Asset**.

1. **Compile Model to Game** rebuilds into the asset's owning Source 1 game.
   Resources use `models/wavelength/<asset UUID>/model.mdl` and
   `materials/wavelength/<asset UUID>/`. Original game assets are preserved.
2. **Compile / Export Model** opens target settings. Choose a shipped or registered
   **Target Profile**, a **Model Name** without extension, and an **Output Directory**.
   The name becomes the lowercase native file stem. For Source 1, a named game
   deployment is a separate model path from any existing placement.
   Blank game/compiler paths use the profile; override them for a custom install.
   CS2 deployment also requires a **CS2 Target Addon** name.
3. Enable **Include Editable Package (.wlmodel)** to add `asset.wlmodel` beside the target output.
   **Export Editable Model Package** saves the editable asset without compiling.
   Import through **File → Import → wavelength Model IO**, or drag into the viewport.
   Each import receives an independent identity.

| Target | Output and limits |
| --- | --- |
| Source 1 profiles | MDL/VVD/VTX, optional PHY, owned VMT/VTF dependencies and QC/SMD. StudioMDL compiles supported skeletal clips and convex/box/assigned collision. |
| Godot 4 | GLB with embedded supported PBR textures, meshes, skeletal animation and named clips. Configure looping in Godot's animation import settings. Collision reconstruction is not implemented. |
| CS2 | Static FBX/ModelDoc, VMAT/PNG and validated compiled resources under `content/` and `compiled/`. Animation and collision need manual ModelDoc work. |
| Other routes | Explicit unimplemented errors; no universal model conversion or Source 2 model-import claim. |

**Allow Static/Approximate Conversion** accepts reported unsupported native shader
features, static-pose conversion or omitted collision. It is off by default.
Procedural shaders still require baking. Source detail/envmap/phong and other
engine effects do not automatically become equivalent PBR shaders.
Inspect `conversion-report.json` and **Text Editor → wavelength Model Conversion
Report** for target files and omissions.

Editable Source materials own full-resolution base and supported normal images,
plus original VMT/texture dependencies. Edit those owned image nodes normally;
Source 1 builds use edited pixels without modifying original game textures.
Portable packages contain packed images, supported rigs/actions/clips and owned
native modelling controls. Later editing does not require the source game.
Unrelated level dependencies must be included or baked explicitly. An assigned
external collision mesh is copied as an owned collision-only dependency.

Compiler status and log paths appear in Model Asset. **Esc** cancels compilation.
Validated file sets commit with rollback; failures do not replace working output.
Blender's native modelling tools remain the editing tools. Packages capture the
editable source before target-specific changes.

[SCREENSHOT: Compile / Export Model target, deployment and package controls]
[SCREENSHOT: Owned editable texture nodes and completed conversion report]

[SCREENSHOT: Model Asset actions and an independently detached track beside its placed original]
