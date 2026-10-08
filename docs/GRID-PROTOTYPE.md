# Native grid viewport experiment

This is an executable **native-shader prototype**, not the C++ renderer/state
bridge or a supported installer recipe. It modifies embedded vertex/fragment
shader text in a copy of the exact Blender 5.2.1 ELF investigated earlier.
Blender's native GPU shader compiler then compiles and draws it. No Python GPU
draw-handler grid or global theme recoloring is used.

## Run locally

The prepared local launcher is `../bin/test-native-grid`. It launches an isolated
factory-startup Blender with the current Wavelength source loaded for testing.
In the sidebar choose **wavelength**, then adjust **Grid & Units → Step**.
Try steps 8, 16, 32 and 64; top/front/right views; orbit, pan and zoom.
The running experiment does not modify the installed AppImage or enable patches
in the normal Blender launcher. Quit the experimental window to leave the test.

Recreate on this exact build (an unsupported SHA-256 is rejected):

```sh
mkdir -p build/grid-runtime
cd build/grid-runtime
/path/to/Blender.AppImage --appimage-extract
cd ../..
python3 tools/prototype_grid.py build/grid-runtime/squashfs-root/blender build/grid-runtime/squashfs-root/blender-grid-test
build/grid-runtime/squashfs-root/blender-grid-test --factory-startup --python tools/grid_demo.py
```

The source executable remains intact. Do not ship the experiment's generated
recipe as verified: its `verified` flag deliberately remains false.

## Mechanism

The vertex stage requires each native grid line’s own spacing to equal the
selected interval, then checks its perpendicular world coordinate. Other levels
preserve native emphasis colors instead of becoming yellow just because they
are multiples of the interval, reusing the existing flat emphasis
varying. The fragment stage uses yellow for matching non-axis lines, leaving axes
and Image/UV-grid coloring alone. Existing line placement, depth, alpha/fading and
AA code is retained. Text is compacted into existing string capacity; the byte
length, NUL termination and ELF offsets remain unchanged. Input is hash-locked.

The temporary Python demo sets subdivisions to 10 and scene units to NONE. It
passes interval through Blender's existing grid scale; aligned views read level
3, user views level 0. This assumption is specific to the inspected native
`ED_view3d_grid_steps` behavior. Production add-on code is unchanged.

## Limits

- Not a compiled C++ state bridge. The C++ math prototype remains separate.
- The isolated executable recolors applicable 3D grids even if engine mode is
  disabled. Per-view enable/color/state transport is future work.
- Unit system NONE and subdivisions 10 are required; other settings are not
  supported by this experiment.
- Only lines selected by Blender's native LOD exist. Highlighting cannot force
  invisible fine snap intervals to appear at distant zoom levels.
- Full Vulkan, multiple-window, Image/UV, geometry occlusion and long-session
  performance verification remain outstanding.

## Captures

`WL_GRID_CAPTURE=1 WL_GRID_TEST_QUIT=1` runs top 16, top 32, front 16, right 16 and
perspective 16 views, saves screenshots to ignored `build/grid-viewport-test/`,
and exits. Add `WL_GRID_BASELINE=1` when running the original executable to capture
an unmodified comparison in `build/grid-viewport-baseline/`.
