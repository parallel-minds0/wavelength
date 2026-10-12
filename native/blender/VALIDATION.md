# v0.15.0 Windows patch validation

- Windows x64 MSVC compilation and exact binary-patch reconstruction passed in
  [GitHub run 38279076226](https://github.com/parallel-minds0/wavelength/actions/runs/38279076226).
- Downloaded patch SHA-256 matches the build manifest.
- Windows installation, injection, and rendering have not been tested.
- No Windows executable was run by the maintainer. Manual verification is required.
- The Linux native payload remains unchanged from the tested v0.14.0 payload below.

# v0.14.0 Linux patch validation

- 143 automated tests passed.
- Generated binary difference round-tripped to the exact intended output.
- Actual `--force` install on a temporary copy of the user's stock Blender 5.2.2
  patched the executable and installed the add-on together.
- Native API startup used the existing installation's libraries and resources.
- Repair passed; uninstall restored the exact original bytes and removed the add-on.
- Final OpenGL viewport passed yellow-parent/grey-subdivision, orthographic and
  perspective occlusion, and workspace restoration checks on Radeon 780M.
- The user's host executable was left untouched during verification.
- CUDA, HIP, HIPRT, OptiX and oneAPI host support are enabled in the internal
  reference used for this delta. Existing Blender kernel resources remain installed.
- Windows C ABI grid-math helper compiled on Linux using LLVM-MinGW; not executed.
  It is not a Windows Blender grid patch. Windows injection is untested and not supplied.

Base executable SHA-256: `51dd3d8f494b1a47959307bd5d52c67e3d586fa8540243628ac89e2185743868`.
Patched executable SHA-256: `fc0c055d06c23d0f646300c2c4250f3d9705546981d2c3b874b7794f9128c02f`.

This patch is experimental and verified on this Linux host, not every distribution.
The startup probe prevents installation when the resulting executable cannot run
against the selected host's resources. No separate Blender runtime is shipped.

## Earlier internal build verification (historical)

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
