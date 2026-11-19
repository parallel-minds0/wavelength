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


### Hammer VisGroups

Source 1 VMF import preserves the VisGroup hierarchy, colors and memberships of
brushes and entities. Save the Blender project and export a VMF to carry those
groups back into Hammer. To edit the groups, use Hammer. In Blender, use the
Outliner and engine tree for visibility and export inclusion.

Ordinary Hammer object groups also survive the Source 1 VMF round trip, including nested groups and brush and entity membership. Use Hammer to edit those groups.

Hammer camera bookmarks and the active bookmark also survive VMF import and
export. Open the exported VMF in Hammer to use or edit the bookmarks.

Hammer view settings and inactive cordon regions also survive a VMF round trip.
Disable cordon mode in Hammer before importing a VMF into Blender.

Editable VMF exports also preserve known Hammer++ editor settings for palettes,
color correction, lighting, post-processing and background images. Use Hammer++
to edit the settings and keep any referenced external assets available.

Editable VMF exports retain the imported Hammer version header and world map
revision. New maps use a generated header.

Source 1 VMF exports also carry the original Hammer editor colors on brushes
and entities. Use Hammer to view or edit those colors.

For Source 1 lightmaps, open Texture Settings and use Read Face to sample its
scale. Set Lightmap Scale and use Apply Scale to change just that setting.
Edit Mode applies to selected faces. Object Mode applies to whole brushes.

For Source 1 smoothing groups, use Texture Settings > Read Face to sample the
mask and Apply Groups to set it on the selected faces or brushes. Enter a
decimal mask: 1 selects group 1, 2 selects group 2, 3 selects both, and 0 clears
all groups. The exported VMF carries the setting to the Source compiler.

Source 1 VMF imports also retain explicit brush-face contents and surface
flags in editable exports and compiler inputs.

Use Read Face in Source 1 Texture Settings to sample the Contents Mask and
Surface Flags Mask. Enter a decimal mask and click Apply on its row. Clear the
field and click Apply to remove that override. Edit Mode targets selected faces.
Object Mode targets whole brushes.

The texture eyedropper also samples the Source 1 face settings into Texture
Settings. Use the corresponding Apply button to transfer a setting to another face.

Use Apply All Face Settings to transfer the four Source 1 fields together.
Blank Contents Mask and Surface Flags Mask fields remove those overrides.

For Source 1, open Build & Validation and choose Build Preview for a fast
visibility pass with normal lighting. Use Play Preview to launch the separate
preview BSP. Use Build and Play for the regular output.

Choose **Build & Play Preview** to launch the game automatically once the
preview BSP is ready. If the build fails or you cancel it, the game stays closed.

While building, Build & Validation shows the running compiler and its elapsed
time. The progress bar counts completed stages.

The build panel also shows recent output from the running compiler. Use Load
Build Log to see the full logs in the Text Editor.

A failed compiler stage reports its name and log file in Build & Validation.
Use Load Build Log to open the full diagnostics.

If a rebuild fails or is cancelled, Play still opens the last successfully
built BSP while that file remains available.

Use Open Build Folder in Build & Validation to find the latest staged build,
including compiler logs and any BSP or pointfile it produced.

Use Show Leak Path after a compiler produces a pointfile. It draws the path
in the current scene using the build scale. Click it again after rebuilding
to refresh the overlay.

Use Clear Leak Path to remove the overlay from the current scene. The compiler
pointfile stays available for Show Leak Path.

After showing a leak overlay, use Frame Leak Path to center a 3D Viewport on
it while keeping your current selection.

When VBSP produces a leak pointfile, the Source 1 build stops before visibility
and lighting. Use Show Leak Path to trace the leak, then rebuild.

Use Import Leak Pointfile in Build & Validation to open a .lin or .pts file
from Hammer or an external compiler. Set the matching map profile scale first.

First Leak Point and Last Leak Point zoom in on either endpoint in pointfile
order. Frame Leak Path returns to the whole path.

Use **Rebuild** in Build & Validation to repeat the last queued build in the
current scene. It uses your latest edits and compiler settings with the previous
build mode and output destination. Build & Play Preview also repeats its launch.

The Last build and Last preview labels show which BSP each Play button will
use, including after a failed rebuild.

The folder icon beside a playable BSP opens its directory. If the file was
moved or deleted, its label shows missing and its Play button is disabled.

For a missing Source 1 BSP, click Relink beside its label and select the file
in its new location. Keep its compiled filename for embedded map assets.

Before your first Source 1 build, use Choose BSP or Choose Preview BSP to
assign an existing compiled map to its Play button.

Use Change BSP beside an available Source 1 BSP to switch that Play target.
Use **Deploy BSP** or **Deploy Preview** in **Build & Validation** to copy
the corresponding BSP into the configured Source 1 game’s `maps` folder
without starting the game. Deployment replaces any BSP with the same filename.
Use **Verify Deployment** or **Verify Preview Deployment** to check whether
the BSP in the game folder matches the selected file.
Use **Open Game Maps Folder** to open the deployment directory once it exists.



Source 1 exports write orientation using the vector **angles** key. Legacy
scalar **angle** values are converted automatically, including the upward and
downward special values, while the original imported properties remain stored
in Blender. Re-export and rebuild older maps to obtain this correction.
