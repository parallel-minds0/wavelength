# Civilization V: experimental cell editing

Civ V uses a high-level hex-cell workflow. Cell records, not editable brush or
vertex geometry, are authoritative. The hex mesh is a colored visualization of
terrain and flat/hill/mountain elevation; blue edges show rivers. It does not use
Civ V's terrain shaders or unit models.

1. Select **Civilization V — Experimental Hex Cells**, or import a `.Civ5Map`
   through **File > Import > wavelength IO** to select the profile automatically.
2. Use the **Civ V Cells** tool in Object Mode. Click or drag to select cells;
   Shift toggles cells. Selected cells have cyan outlines.
3. In the viewport sidebar's **Civ V Cells (Experimental)** panel, choose Select
   or Paint. Select the property and its value: terrain, elevation, feature,
   resource, quantity, natural wonder, or river edges. Apply to the selection,
   or paint directly by dragging over cells. Resource placement supplies a
   nonzero quantity; removing a resource clears its quantity.
4. Export through **File > Export > wavelength IO**, selecting Civilization V.
   Save to a new `.Civ5Map` while testing. Save the `.blend` to preserve the editable
   cell document as well as the original map bytes.

[SCREENSHOT: top-down hex map with selection, river edges and cell controls]

Brush/CSG and shape-handle operations are disabled for this profile. Mesh topology
or vertex changes are rejected during painting/export, rather than silently
turning arbitrary Blender geometry into a tile map.

The initial implementation edits geography only. Header tables, mod data,
scenario/city/unit/player records and all unknown trailing bytes are retained.
Cities, units, diplomacy, start positions and scenario rules are not exposed as
editable tools. Continent and reserved river bits are preserved. This version
also does not enforce every terrain/feature/resource rule from Civ V or mods.

Validation covered 90 installed maps with exact byte-for-byte unchanged round
trips, selected-cell-only edits, saved Blender scenes, and real viewport
selection/painting. The legacy version-6 UnitBenchmark map is unsupported. Game
loading/WorldBuilder acceptance of edited maps is not yet verified, so this remains
experimental.
