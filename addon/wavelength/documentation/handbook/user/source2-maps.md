# CS2: Source 2 maps and materials

The CS2 profile imports and exports editable **VMAP polygon meshes**, with
per-face material assignments and UV coordinates. Source 2 is a mesh pipeline:
it does not impose Source 1 convex BSP brush rules. Entities, placed model
instances, prefab references and runnable-map setup are outside this workflow.

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

The result is an editable map source, not a playable map. Open it in Hammer to
add entities, lighting and game-specific setup, then compile it with the CS2
tools. The separate **CS2 model bundle (.vmdl)** format still exports model assets;
it is not the map format.

## Validation

The local verification imports a shipped CS2 binary VMAP, round-trips generated
geometry through Valve binary DMX conversion, checks transforms/materials, reads
compiled CS2 VMAT/VTEX assets and saves an external material-library shard with a
thumbnail. A generated mesh map using a stock CS2 material compiled successfully
with the installed resource compiler and produced a packed map VPK.
