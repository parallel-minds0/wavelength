# CS2: Source 2 maps and materials

The CS2 profile imports and exports editable **VMAP polygon meshes**, with
per-face material assignments and UV coordinates. Source 2 is a mesh pipeline:
it does not impose Source 1 convex BSP brush rules. Verified Source 1 entities can be converted on export; placed model instances,
prefab references and other unsupported entities need manual conversion. See
[Cross-profile level compilation](cross-compiling.md) for coverage and reports.

## Configure the profile

Choose **Counter-Strike 2 — Source 2 — Windows**. In **Scene Properties →
wavelength Map → Project & Toolchain**, verify:

- **Game Directory:** the installed `game/csgo` directory with `gameinfo.gi`.
- **Compiler Directory:** the installed `game/bin/win64` directory with
  `dmxconvert.exe` and `resourcecompiler.exe`.

wavelength uses CS2's installed map scaffold and DMX converter. Its material
decoder is [Source 2 Viewer CLI](https://github.com/ValveResourceFormat/ValveResourceFormat).
On this Windows installation it lives in
`%LOCALAPPDATA%/wavelength/tools/source2viewer/`. Other installations can put the
CLI and its companion DLLs there, or set `WAVELENGTH_SOURCE2_VIEWER` to its full
executable path. The decoder is a separate tool, not embedded in addon releases.

## Use CS2 materials

Press **Browse CS2 Materials** in Project & Toolchain or the Meshes & Textures
sidebar. The Asset Browser uses the selected CS2 installation's VMAT library,
including the compiled materials and textures inside its VPK archives.

Indexing and thumbnail generation run in a background Blender worker. The first
pass can take considerable time; cached decoded assets are reused. Thumbnail
shards appear progressively. Apply a material with drag and drop or the existing
texture placement controls. Object Mode targets objects; Edit Mode targets
faces, using the same controls as other wavelength texture libraries.
Use **Start / Resume** or **Pause** in the Meshes & Textures sidebar to control
background preparation while retaining existing cached assets.

The viewport approximates base color, normal, roughness and metallic inputs.
Layered or specialized CS2 shaders may look different in Blender. Native VMAT
paths remain authoritative: VMAP export references the original CS2 material,
preserving the complete engine shader rather than exporting the preview shader.

```{screenshot} cs2-material-browser
:alt: CS2 profile and native Asset Browser showing decoded CS2 materials
Capture a CS2 material thumbnail, a textured mesh and the material library status.
```

## Import a map

Open **File → Import → wavelength IO**, choose **Source 2 (.vmap)** or automatic
format detection, and select an editable `.vmap`. Text and binary DMX encodings
are supported. Binary VMAPs pass through the installed Valve DMX converter.

Imported geometry enters a new collection. Group transforms are baked; Blender
coordinates use meters while Source coordinates use inches with Z up. Per-face
VMAT references and corner UVs survive the conversion. Missing materials retain
their reference and produce a warning so exporting the geometry does not replace
them with an unrelated material.

This does not read compiled `.vmap_c` files or map VPKs. Resolve model instances
and prefabs to editable meshes in Hammer first. Convert subdivision surfaces to
ordinary meshes before importing; unsupported subdivision data is rejected
rather than flattened silently.

## Export a map

Open **File → Export → wavelength IO**. The file browser opens directly. Choose
**Source 2 map (.vmap)** in **Format**, optionally enable **Selected Objects Only**,
and choose the destination filename. The CS2 profile defaults to this format.

Visible mesh geometry, including evaluated procedural geometry, is written as
editable map meshes. Helpers and point-entity model representations are excluded.
Original meshes, modifiers, materials and selection are preserved. Finalize or
cancel live CSG before export. Nonmanifold or inconsistently wound topology must
be corrected before it can become a Source 2 editable mesh.

Native CS2 materials remain game-relative VMAT references. Blender-authored
materials export a generated VMAT and PNG base-color texture, with scalar
roughness. Other custom shader inputs need baking or native VMAT authoring.

For an addon layout, save under `content/<addon>/maps/`. Generated material assets
go under the sibling `materials/wavelength/<map-name>/` directory. For a standalone
file outside a `maps/` tree, that directory is placed beside the VMAP. Copy the
map and generated material directory into the matching content layout together.
Stock CS2 materials are referenced and are not copied into the export.

```{screenshot} cs2-vmap-export
:alt: Export file browser with Source 2 map format selected
Capture the Format dropdown, Selected Objects Only and the VMAP destination.
```

The result is editable map source. Review converted entities and add unsupported
entities, lighting and game-specific setup in Hammer, then compile it with the CS2
tools. The separate **CS2 model bundle (.vmdl)** format still exports model assets;
it is not the map format.

## Validation

The local verification imports a shipped CS2 binary VMAP, round-trips generated
geometry through Valve binary DMX conversion, checks transforms/materials, reads
compiled CS2 VMAT/VTEX assets and saves an external material-library shard with a
thumbnail. A generated mesh map using a stock CS2 material compiled successfully
with the installed resource compiler and produced a packed map VPK.

## Port Source 1 textures

VMAP export converts Source 1 materials into generated VMATs and PNG texture
sources under `materials/wavelength/<map-name>/`, beside the destination `maps/`
folder. Base color and bump textures are decoded from original mounted VTFs at
full resolution, not viewport previews. The original game location stays with
the material when switching profiles. For older files, reload materials in their
Source 1 profile before switching if export cannot locate the source game.
Missing textures stop export. Two-layer terrain exports native CS2 layers; other Source
shader effects need review in Hammer and produce a conversion warning.

Save into your CS2 addon's `content/<addon>/maps/` directory. The VMAP references
the generated material assets; it does not embed pixels. Include the generated
`materials/` folder when transferring source files. Compile and package through
CS2 Hammer for game distribution. Export alone does not build a playable map.

### Continue when a material cannot be converted

In **File → Export → wavelength IO**, select **Source 2 map (.vmap)** and
enable **Ignore Material Conversion Errors** in the export options. Failed
Source 1 materials receive a generated neutral placeholder and a warning.
Geometry is still exported; source materials remain unchanged. The option is
off by default and does not bypass geometry or map-format errors.

## Unified material conversion

Use **Project & Toolchain → Cross-Compile Level**. Material conversion and
legacy texture-scale correction run automatically in that export pipeline.
There are no separate conversion/repair buttons to run first.

The source profile, cached source settings and installed source game are
resolved independently from the CS2 target directory. **Source Game Directory**
provides an explicit override. **Use Loaded Textures if Source Game Is Missing**
is an optional fallback; **Ignore Material Conversion Errors** permits
placeholders with warnings. The cross-compile report includes material mappings
and warnings as well as entity results.

Advanced scripts can still use the standalone conversion and repair operators;
they remain available through F3 for compatibility. Standalone material
assignment retains its original optional assignment behavior.

## Package for another installation

In the VMAP export options, enable **Package Project for Sharing**. Export
creates `<map-name>.project.zip` beside the VMAP. It includes `maps/<name>.vmap`,
referenced generated materials and texture sources, a manifest, and instructions.
Previously converted materials are copied from their recorded content folder
when exporting to a new location. Stock CS2 assets remain installation-provided
references. This package covers the current mesh/material workflow, not props,
entities or other unsupported map content.

The recipient extracts the ZIP into their CS2 addon's content folder, opens
the map in CS2 Hammer, and compiles it. This shares editable project sources;
it does not produce a compiled playable map VPK.

### Convert without the original game

Enable **Use Loaded Textures if Source Game Is Missing** in the conversion
file browser. This opt-in fallback converts base-color images available to
Blender even when the original game is absent. It uses the available image
resolution, which may be a reduced viewport preview, and reports that limitation.
Other shader channels need review. Materials without usable image pixels still
fail individually; their original assignments stay intact. The explicit
**Source Game Directory** override takes priority over stored game locations.

### Automatic texture-scale recovery

Export reconstructs legacy converted brush projection from its retained source
material dimensions and face axes. This happens in export memory without
changing the authoring mesh, UVs or materials. It does not resize geometry or
texture images. Keep original material metadata for this recovery.

### Tool materials during Source 1 ports

Known Source tool materials (including sky, nodraw, trigger and supported clip
types) reference their stock CS2 VMAT equivalents. Their preview images are not
converted into ordinary surface materials. Previously converted materials are
recognized through their retained original material. Unknown tool equivalents
require an explicit mapping. Brush entities and their gameplay behavior remain
outside the mesh-only map exporter; a trigger material alone does not create
a trigger entity. Re-export older maps to apply these mappings.

## Visibility compile quality

VMAP export defaults to **Visibility Quality → Balanced (64 units)**. It adds
an editable `visibility_hint` covering exported mesh bounds, using CS2's lower
resolution mode with fewer initial clusters. This avoids excessively expensive
8-unit visibility solves on dense brush-map ports without resizing geometry.
Finer 16-unit and 32-unit modes and a coarser 256-unit mode are available.
**CS2 Native (No Hint)** omits the generated hint entirely.

The hint is compiler metadata, not a gameplay entity. It stays in shared project
packages and can be edited or removed in Hammer. Coarser visibility can weaken
runtime occlusion culling; inspect the compiled result in game. Lighting quality
and lighting-bake options are independent of this setting. Re-export existing
VMAPs to apply it.

### Legacy tool variants

Known `tools/toolsclip_*` surface variants (including concrete, metal and
metalgrate) map to stock CS2 `toolsclip`, retaining the clipping role. The report
warns that Source 1 surface-specific sounds/physics need review. Source 1
`toolsskybox2d` maps to the stock CS2 sky boundary; review the sky environment
setup separately. These are deliberate semantic mappings, not ordinary texture
image conversions. Unknown tool materials still require an explicit equivalent.

WorldVertexTransition materials now export native CS2 color/normal layers,
optional blend modulation and terrain vertex blend weights, including the four
blended materials in de_dorms_d.vmf. No placeholder or bake is required for this
conversion. Packages and VMAP roundtrips preserve these inputs. Advanced detail,
modulation appearance, roughness and surface physics require review in Hammer.

## Applying textures to imported meshes

Imported VMAP geometry uses native mesh faces and corner UVs. Apply, drag-and-drop
and click placement assign the chosen CS2 material directly: Object Mode affects
the object, while Edit Mode affects the selected faces. Material-only application
preserves the imported UV layout. **Texture Settings → Apply Mapping** explicitly
projects UVs using the current shift/rotation/scale and profile engine units.
These operations do not require Source 1 brush face IDs or convex geometry.

[SCREENSHOT: Applying a CS2 material to selected faces on an imported VMAP mesh]
