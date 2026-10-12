# Native grid validation — 0.13.0-pre.alpha

Validated on 12 October 2026 using the separately compiled Blender 5.2.2 LTS.
The host's installed Blender executable was not replaced.

- Exact upstream revision: `d13f752e3b9c4f8c261cda552b1021f8bcc0382c`.
- Native executable SHA-256: `58b112baaa75970a4a5078e94088400244b310ab0cf2057f947b4add8c356abe`.
- Build: Release, GCC 16.2, `-O1`, Linux x86-64-v2, Debian glibc 2.43.
- 137 automated Python/installer tests passed.
- Real native RNA startup probe passed.
- OpenGL and Vulkan viewport pixel checks passed on AMD Radeon 780M:
  yellow parent intervals, grey subdivisions, orthographic and perspective
  occlusion by solid geometry above the grid plane, and workspace restoration.
- Blender UI checks passed for engine/metric spacing, `[` / `]` bindings and
  bounds, exact restoration of native fields, and clean unregistration.
- Saved-file check passed: a file saved in the wavelength workspace opens with
  the native wavelength renderer disabled when the add-on is absent.
- Real compiled-runtime installer install, repair, and uninstall passed in
  temporary directories; the executable hash remained unchanged.

Reproduce with `tests/blender_native_grid_ui.py` (both `--gpu-backend opengl`
and `--gpu-backend vulkan`) and `tests/blender_grid_shortcuts_ui.py` in the
compiled Blender UI. Test scripts write their results under `build/`.

## Limits of this build

This is a Linux native-grid preview, not a patch that can be injected into an
arbitrary stock Blender or AppImage. The Python add-on alone cannot supply the
new native API. Windows and macOS native builds have not been compiled/tested.
The binary was built on Debian sid; older distributions may require rebuilding
from the supplied source. CUDA, HIP, oneAPI and OptiX Cycles device backends are
disabled in this preview; viewport OpenGL/Vulkan and Cycles CPU are included.
X11 tablet support is enabled. Other Blender features and GPUs were not broadly
regression-tested. The grid's physical plane can correctly appear in front of
geometry below that plane; tests verify occlusion by geometry above it.
