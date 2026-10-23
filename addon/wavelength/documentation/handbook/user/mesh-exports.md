# Godot 4 and Counter-Strike 2: meshes and textures

These profiles provide a static mesh/material export path. They do not export
entities, collision, animations or runnable maps. The CS2 profile also supports
[editable VMAP meshes and installed CS2 materials](source2-maps.md).

## Shared workflow

Blender's **File → Export → wavelength IO (.map, .vmf, .vmap, .glb, .vmdl)**
opens the file browser directly. Choose **Format** in its options panel.
Godot GLB writes the chosen file and a companion asset package. CS2 ModelDoc
writes a named bundle folder containing its ModelDoc, FBX, VMAT and PNG files;
the completion message reports the generated ModelDoc path.

**File → Import → wavelength IO (.map, .vmf, .vmap)** opens the import file browser.
GLB is available through Blender's native glTF importer. wavelength has no
ModelDoc reader; CS2 model bundles and editable VMAP maps are separate formats.

1. Open wavelength and choose **Godot 4 — Meshes & Textures** or
   **Counter-Strike 2 — Source 2 — Windows** in Scene Properties → wavelength Map.
2. Create or edit ordinary meshes, including procedural wavelength primitives.
   Concave geometry is permitted. Procedural primitives evaluate directly during
   export; their generators are not applied to the authoring scene.
3. Use UV-mapped image textures connected to a **Principled BSDF** material's
   Base Color, or a constant base color. Bake procedural base-color graphs first.
   Explicit UV Map nodes are supported; bake generated/object/mapping coordinates
   into UVs before export. Images are written as PNGs.
4. Open **N → wavelength → Meshes & Textures**, choose **Export Directory**, and
   optionally enable **Selected Meshes Only**. The viewport header also has Export.
5. Press **Export Meshes & Textures**. The package is created in a sanitized
   map-name subfolder of the directory. Re-export updates that generated package.

Only visible, renderable mesh content is included. Excluded objects, editor
helpers, entity preview models and meshes parented to point entities are skipped.
Mesh geometry carrying old brush-entity metadata exports as ordinary static
geometry; metadata itself is not exported. Selection and original mesh/material
data are preserved. Live CSG still requires finalization or cancellation.

```{screenshot} mesh-export-panel
:alt: Godot or CS2 profile selected, with Meshes and Textures export settings
Capture the profile selector, export directory and Selected Meshes Only control.
```

## Godot 4

The package contains **map_name.glb**, with mesh primitives, normals, UVs,
materials and embedded images. The manifest is `wavelength-export.json`. The
accompanying texture folder contains PNG sources as well.

Choose a directory inside your Godot project's resource folder, or copy the
exported package into the project. Godot imports the GLB automatically; instance
it into your scene. Geometry is exported in metres with glTF's Y-up convention.
There are no cameras, lights, spawn points, physics bodies or collision shapes.

The local profile discovers Godot's console executable under
`C:\Users\user\Applications\Godot`; exporting does not require the editor to run.
The executable can be changed in Project & Toolchain. Existing shaders still
need to fit Blender's glTF material export support; arbitrary Blender shader
graphs are not baked automatically.

[Godot's supported 3D formats and Blender glTF workflow](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/available_formats.html).

## Counter-Strike 2 / Source 2

The package is a **content-source bundle**, not a VMAP or compiled game model:

```text
map_name/
  models/wavelength/map_name/map_name.fbx
  models/wavelength/map_name/map_name.vmdl
  materials/wavelength/map_name/*.vmat
  materials/wavelength/map_name/*.png
  wavelength-export.json
```

Copy the `models` and `materials` directories into your CS2 addon's **content**
directory, normally:
`...\Counter-Strike Global Offensive\content\csgo_addons\your_addon`.
Open the VMDL in ModelDoc from that addon, compile it, and inspect the mesh and
materials. The VMDL remaps FBX materials to the exported VMATs. Meshes retain Z-up
orientation; one Source unit represents 0.0254 metres.

CS2's first-pass material conversion includes base-color image/constant and
scalar roughness. Normal maps, metallic/roughness texture graphs, transparency
and engine-specific shader effects are not converted. Linked unsupported channels
are noted in the manifest and export report. Adjust advanced materials in CS2's
Material Editor. No collision or physics nodes are generated in ModelDoc.

The profile discovers the installed CS2 game and resource compiler under the
default Steam library. Those paths appear in Project & Toolchain and can be
changed. Compilation in ModelDoc remains an explicit handoff; wavelength's BSP
Build/Play pipeline is disabled for these mesh-only profiles.

The implementation was verified with an isolated `wavelength_export_smoke` addon:
CS2 compiled the generated VMDL and VMAT and reported the expected material
reference and physical bounds. This is asset compilation validation, not a
claim that a complete level or gameplay system is supported.
