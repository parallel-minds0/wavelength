# Troubleshooting and limitations

## Separate authoring, previews and engine output

A visible preview does not prove that an asset compiles in the active game.
Likewise, an asset may compile correctly while its editor representation is
unavailable. Inspect Profile Setup errors for previews and Build & Validation
logs for engine output.

## Texture assignment

In Edit Mode, choose face selection and select the intended faces before dragging
a texture. Auto/Surface scope affects that selection; Object is an explicit
override. With no selected faces the drop uses the hit face. If an asset appears
black, inspect shader realization and the referenced game content separately
from the face assignment. See [Surface tools](../SURFACE-TOOLS.md).

## Cutting and finalization

Faces mode changes surface topology. Split Solid and Subtract produce capped
volume results and require a manifold target. Apply visible modifiers or finalize
procedural geometry first. Keep Both creates separate objects by default; turn
off Separate Objects to retain a combined mesh. K and Enter apply solid cuts;
Shift+Enter retains an open guide. See [Cutter controls](../DRAWING.md).

```{screenshot} cutter-keep-options
:alt: Cutter operation, keep-side and separate-object controls
Capture Split Solid with Keep Both and Separate Objects, plus the resulting objects.
```

## Engine restrictions

Blender and future mesh-based profiles need not impose convex BSP brush rules.
GoldSrc and Source brush export do. Terrain/displacement and model workflows have
additional engine constraints. Displacement stitching still requires in-game
verification; a Blender viewport seam check alone is insufficient.

## Useful bug reports

Record the wavelength/Blender versions, profile, active mode, operation settings,
exact action, and Diagnostics error ID. Provide the smallest saved blend/MAP/VMF
that reproduces the result and the compiler log when engine output is involved.
