# Blender 5.2.1 renderer integration audit

Official tag `v5.2.1` resolves to commit
`9e2066aef7ef7e20c142ad7bd3303138a4304c93`. The inspected host reports the
same short build hash. Source links below are pinned to that commit.

## Verified path through Blender

1. [RNA overlay properties](https://github.com/blender/blender/blob/9e2066aef7ef7e20c142ad7bd3303138a4304c93/source/blender/makesrna/intern/rna_space.cc#L5025)
   expose grid scale/subdivisions, not a per-line Wavelength highlight predicate.
2. [ED_view3d_grid_steps](https://github.com/blender/blender/blob/9e2066aef7ef7e20c142ad7bd3303138a4304c93/source/blender/editors/space_view3d/view3d_draw.cc#L793)
   supplies the native step hierarchy. `grid_subdivisions=1` is not proof that
   all rendered levels equal the requested snap step: repeated levels are
   expanded by the C++ overlay to a factor of ten.
3. [Grid::init_v3d / begin_sync](https://github.com/blender/blender/blob/9e2066aef7ef7e20c142ad7bd3303138a4304c93/source/blender/draw/engines/overlay/overlay_grid.hh)
   compute zoom levels, camera-relative coverage, flags, grid UBO, passes and
   procedural line draws. This is the C++ integration point for per-view state.
4. [OVERLAY_GridData](https://github.com/blender/blender/blob/9e2066aef7ef7e20c142ad7bd3303138a4304c93/source/blender/draw/engines/overlay/overlay_shader_shared.hh#L134)
   is the CPU/GPU shared layout: steps, offset, clip rectangle, level, line count,
   padding. Adding fields requires synchronized layout and shader rebuilds.
5. [overlay_grid_infos.hh](https://github.com/blender/blender/blob/9e2066aef7ef7e20c142ad7bd3303138a4304c93/source/blender/draw/engines/overlay/shaders/infos/overlay_grid_infos.hh)
   declares UBO slot 3, grid flags/iteration push constants, interpolated position
   and flat alpha/emphasis. A new flat highlight value belongs here as well as
   in both shaders. This fifth file was missing from the original four-file plan.
6. [Vertex shader](https://github.com/blender/blender/blob/9e2066aef7ef7e20c142ad7bd3303138a4304c93/source/blender/draw/engines/overlay/shaders/overlay_grid_vert.glsl#L137)
   computes `line.P = step_offs + step_size * line.P`. The perpendicular line
   coordinate is `line.P[1 - line.axis]`, constant for both endpoints. Classify
   that coordinate against origin + integer multiples of the snap interval;
   classify only SHOW_GRID and exclude GRID_SIMA and axis draws. Pass a flat
   result to avoid producing little highlighted segments at line intersections.
7. [Fragment shader](https://github.com/blender/blender/blob/9e2066aef7ef7e20c142ad7bd3303138a4304c93/source/blender/draw/engines/overlay/shaders/overlay_grid_frag.glsl#L47)
   mixes normal/emphasis colors. Apply the highlight only in this non-axis color
   branch, keeping native alpha, depth, AA, stipple, iteration weights and fade.
8. [Draw CMake shader embedding](https://github.com/blender/blender/blob/9e2066aef7ef7e20c142ad7bd3303138a4304c93/source/blender/draw/CMakeLists.txt#L805)
   calls `glsl_to_c` and generates shader source/metadata lists.
   [GPU dependency initialization](https://github.com/blender/blender/blob/9e2066aef7ef7e20c142ad7bd3303138a4304c93/source/blender/gpu/intern/gpu_shader_dependency.cc#L509)
   registers embedded `datatoc_*` data. Dropping a GLSL file beside Blender is
   therefore not a replacement mechanism for these shaders.

## What this means for injection

The host AppImage wraps a stripped x86-64 ELF Blender payload. Its executable
SHA-256 is `4b98e176544d587178ed9d4a0b29d41506b5c797fbdf4da77c0314f2061a944b`;
its ELF build ID is `d1350ce4272b6eff171a9c87f1b9a12a97888945`.
The examined dynamic symbol table does not export the grid begin_sync method or
`gpu_shader_dependency_get_source`. Thus no simple LD_PRELOAD symbol override was
established. `ctypes.CDLL` loading the math library installs no call site.
Shader marker strings do exist in this binary, but are not relocation, capacity,
metadata, or ABI evidence sufficient to patch them.

The current same-length-byte recipe engine cannot insert the native library,
redirect the draw call, grow shader metadata, or negotiate UBO layout. A practical
first prototype is a **source-built Blender integration** at the points above.
Once that works, evaluate a build-specific offline ELF hook separately; do not
advertise a universal injector. Replacing an extracted AppImage's Blender binary
with a compatible source-built payload is another deployment option, but requires
matching libraries/resources and does not prove arbitrary host-binary injection.

## Concrete next implementation contract

- Keep Python authoritative for interval, enabled state, origin and color; expose
  a deliberate per-view native/RNA bridge in the patched build, with capability
  detection and ordinary Blender fallback. Do not infer state from global theme.
- Convert units once. `active_grid_step_meters` is the add-on's authoring convention;
  account for any scene display scale separately. Validate finite positive steps.
- Supply state in Grid::init_v3d and initialize disabled state for UV/Image views.
- Add per-line classification plus flat varying, retain native LOD. Highlighting
  native lines cannot make an absent snap interval appear; inserting extra lines
  is a separate design decision. Test that explicitly at every zoom range.
- Validate negative coordinates, world origin, XY/XZ/YZ, perspective, orthographic,
  multiple views/scenes, enable/disable, saved files, OpenGL and Vulkan, and timing.
- Only after successful build and visual regression tests create an exact payload
  recipe, checksum it, patch an offline copy, run launch/render tests, then deploy
  atomically with a recorded original hash and rollback. Fingerprint AppImage and
  extracted executable separately; never patch the mounted read-only runtime.

This audit downloads and fingerprints real source; it does not claim a compiled
Blender renderer patch, visual validation, or successful host injection.

## Repeat the research

`python tools/research_blender.py` fetches hash-verified excerpts from the pinned
commit into ignored `build/blender-source` and runs the read-only source probe.
`python installer/cli.py inspect /path/to/Blender.AppImage` identifies the container;
run `probe-renderer` against the extracted **blender executable** for payload data.
