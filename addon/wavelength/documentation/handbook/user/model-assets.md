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
**Object Properties > Model Asset > Compile Model to Game**.

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

## Current Source 1 scope

MDL versions 44–49 with VVD4/VTX7 render geometry are supported by the mesh reader.
The animation adapter handles ordinary compressed skeletal tracks, raw transforms,
external animation blocks, sectioned clips, names, frame timing and looping.
Runtime blended sequence graphs, additive clips, IK/root-motion tracks and included
sequence models are explicitly rejected for editable animated import. Facial
flexes, attachment/physics reconstruction and event export are not implemented;
sequence events produce a warning. This is an editable render-mesh/skeletal-clip
workflow, not a lossless decompiler for every Source runtime feature.
