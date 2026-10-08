# Milestone 6 — Blender 5.2.1 native grid source investigation

Blender source: https://github.com/blender/blender (use the **v5.2.1** tag).

Relevant files:

- `source/blender/draw/engines/overlay/overlay_grid.hh` — C++ draw pass, grid UBO, and zoom-dependent steps.
- `source/blender/draw/engines/overlay/shaders/overlay_grid_vert.glsl` — line positions and grid levels.
- `source/blender/draw/engines/overlay/shaders/overlay_grid_frag.glsl` — final line colors, opacity and AA.
- `source/blender/draw/engines/overlay/overlay_shader_shared.hh` — shared `OVERLAY_GridData` layout.

The fragment shader blends `theme.colors.grid` and `theme.colors.grid_emphasis` based on a per-line emphasis. **That is not the same as selecting the user's Wavelength snap interval.** Exact matching requires carrying a world-space line coordinate or spacing classification from the vertex stage, and providing the Wavelength snap interval to the GPU without changing Blender's native LOD logic. This is a *source-level design*, not an established binary patch.

Read-only source inspection:

```bash
python -m installer.wavelength_installer.grid_source_probe /path/to/blender-5.2.1 --report grid-source-report.json
```

The report fingerprints each of the four relevant source files and records line-number anchors. It never modifies Blender and **never authorizes binary patching**.

## Implementation plan (not yet complete)

1. Verify the exact v5.2.1 shader input/output declarations and `OVERLAY_GridData` layout.
2. Prototype C++-side snap state and shader-side per-line selection on a locally built Blender, preserving axes, AA, alpha fading, grid LOD, and depth.
3. Verify communication from Wavelength's Python snap setting to the native component.
4. Only then derive a build-fingerprinted injection or patch method for a released Blender executable. A modified GLSL file alone cannot be assumed to be present as replaceable text in the Blender binary.

No renderer hook or binary recipe is shipped by this milestone.
