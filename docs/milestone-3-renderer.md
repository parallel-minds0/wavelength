# Milestone 3 — Blender native grid renderer

## Current status

The C++ ABI and Python ctypes bridge are working prototypes, **not** Blender renderer hooks. No executable modifications are implemented. The patch manifest has zero verified builds. `patch-blender` intentionally raises an exception.

## Integration investigation

Blender's viewport grid is produced by its internal GPU draw code and shaders, not ordinary Python viewport line objects. A CPU-side `is_highlight_line` predicate cannot by itself recolor the existing grid. A valid integration must establish whether to modify shader source, shader constants, or native GPU draw setup for an **exact Blender build**. It must also preserve the existing zoom-dependent grid levels, axis appearance, perspective fade, and nonselected line colors.

Before any patch implementation:
1. Obtain Blender 5.2.1 source matching the exact target binary, and inspect the overlay grid shader and draw pass.
2. Determine how the shader computes grid coordinates, major/minor spacing and opacity; document the desired predicate in shader-space rather than assuming a CPU callback per line.
3. Establish an explicit data channel from the Python add-on to the native shader state, with update and disable behavior.
4. Validate a patch point and reversible backup/restore on a disposable copy of the exact AppImage build.
5. Add a manifest entry containing an exact SHA-256, a patch ID, and test evidence **only after** the modified Blender has been tested.

Compiler discovery and successful native compilation do **not** imply a compatible binary patch. AppImage modification also requires extraction/repackaging and validation; the installer must never patch an in-use AppImage in place.
