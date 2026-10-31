# First level workflow

## Install and choose a profile

Use the installer instructions for the exact compatible Blender executable.
Enter the wavelength workspace. Select the game/platform profile and configure
the installed game directory, entity definitions and compiler paths. Do not treat
a model thumbnail being available as evidence that map compilers are configured.

```{screenshot} profile-configuration
:alt: wavelength profile and game/toolchain configuration in Blender
Capture Scene Properties with a configured game profile and the relevant paths visible.
```

## Prepare assets

Run Profile Setup or enable automatic preparation. Indexing discovers materials,
entities and models; a separate worker prepares previews progressively. Missing
assets are reported without discarding the rest of the cache. See
[Profile setup](../PROFILE-SETUP.md) for lifecycle and recovery controls.

## Author geometry and apply textures

Brush and pencil creation always target nearby visible mesh vertices and edges,
even when Blender's grid magnet is off. A highlighted vertex/edge takes priority
over the grid and preserves its exact position. Otherwise the cursor follows the
surface under it, with profile-grid snapping when enabled, or the profile's
construction plane in empty space. Hover works before the first click and does
not require selecting the target object. Hidden meshes and editor helpers are
excluded. Geometry targets remain active while Ctrl changes the grid snap state.

Brush footprints and profile-grid pencil strokes keep the construction plane
established at their first point; subsequent targets must lie on that plane.
Brush height can match a nearby surface/vertex level without jumping to distant
background geometry. Gold/orange highlights identify vertex/edge targeting;
green indicates surface/grid placement. No extra snapping mode needs enabling.

Use brush primitives or ordinary Blender geometry according to the active
profile. Finalize procedural geometry before tools that require an editable base
mesh. Blender mode matters: Auto texture scope paints objects in Object Mode and
faces in Edit Mode. A texture drop in Edit Mode paints selected faces; with no
faces selected it paints the face under the drop.

```{screenshot} selected-face-texture-drop
:alt: Several selected brush faces receiving an Asset Browser texture
Capture two selected faces, the texture tile, and neighboring unselected faces.
```

## Add entities, validate and build

Choose a game-appropriate entity. Point entities can be placed from the browser;
brush entities own brush geometry. Model-capable entities can use installed game
models or the custom model workflow. Validate before building, then inspect the
compiler log before launching the game. Engine format restrictions still apply
even when Blender can display a mesh.

Save the blend file as the editable project. Exported MAP/VMF, compiled BSP and
generated model files are outputs, not replacements for that project.
