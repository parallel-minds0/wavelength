# v0.11.3 verified milestone

A fresh sealed room containing stairs, an arch and an 80-face sphere compiles through Blender's Build Map operator and reaches visible gameplay in the installed Linux HL2. The fixture is `addon/wavelength/environment/maps/wavelength_playable.vmf`; regenerate the local textured .blend/BSP with `tests/blender_hl2_playable.py` using Blender in background mode. This opt-in test requires the installed game and Source compiler tools.

Open the local `maps/hl2-playable/wavelength_playable.blend`, select the HL2 Linux profile, use Build Map, then Launch Game. Keep the compiled basename unchanged. Renamed BSPs with mismatched embedded default cubemap paths now ask for a rebuild. This verifies loading and rendering, not a completed automated collision test. Earlier runtime notes below are historical; full Source parity remains outside this milestone.

# Half-Life 2 / Source 1 — initial support

Choose **Half-Life 2 — Source 1 — Linux** or **Windows**. Both use VMF, inch-like
0.0254-meter authoring units, Source entity names, and Steam App ID 220. Windows
profile on Linux requires the user to enable the appropriate Proton compatibility
selection in Steam; selecting a profile does not change Steam's compatibility
settings. Compiler host/platform is configured independently of game runtime.

## Working features

- Convex world brushes, brush entities, point entities, material paths and Valve
  texture axes through VMF import/export. Unique numeric VMF IDs are regenerated.
- Repeated entity connection outputs are retained using `__vmf_output__<output>`
  keys in the existing property data, emitted into VMF `connections` blocks.
  This is preservation, not a full Hammer-style I/O editor.
- Lightmap scale/smoothing groups survive face round-trips. Editor-only metadata,
  cameras and visgroups are not recreated as Blender UI state.
- Source starter entity catalog, with project FGD properties where supported by
  the existing FGD reader. Source light defaults use `_light`.
- VBSP → VVIS → VRAD commands receive `-game <directory containing gameinfo.txt>`.
  `level.vmf` is generated without a WAD. BSP output checks `VBSP`, version20,
  and lump bounds before publishing to the selected destination.
- Windows compiler EXEs require the compiler wrapper on Linux, for example
  `["wine"]`. Host absolute game paths use Wine's default Z: mapping. Custom
  prefixes/mappings must provide matching access; Proton wrapper setup is not
  automatic. Native `vbsp` and `vbsp_linux` names are accepted.
- Launch copies the BSP to the configured game `maps` directory and requests
  Steam App ID220. Linux and Windows runtime choice remains Steam configuration.

## Setup

Once HL2 is installed in the default Steam library, choose the profile and click
**Use Local Toolchain** to refresh discovered paths. Verify **Game directory**
points to `Half-Life 2/hl2` and contains `gameinfo.txt`. Set **Compiler directory**
to your matching SDK tools; owning/installing the game does not guarantee those
compilers are installed. Set your FGD explicitly if discovery did not find it.
Use **Export MAP** to choose a `.vmf` destination in Source mode, or Build Map.
The import chooser accepts `.vmf` as well as the original `.map` files.

Enter a Source material path such as `dev/dev_measuregeneric01b` or
`tools/toolsnodraw`, without `materials/` and `.vmt`, then Apply to Selected.
Material names and projection export correctly; gray placeholder previews use a
512×512 assumption. Actual material dimensions and VTF/VPK texture previews are
not yet implemented. Source materials are not converted from WAD texture names.

A self-authored sealed-room fixture is in
`addon/wavelength/environment/maps/minimal_source.vmf`.

## Unsupported or unverified

Displacements, hidden/unsupported geometry blocks and active cordons are rejected
rather than silently discarded. Model rendering, full FGD dialect support,
instances/prefabs, overlays/side-ID remapping, Source I/O authoring UI, VPK/VTF
asset rendering, automatic Proton prefixes and Source 2 are not provided.

Validation: pure VMF/plane/axis/output round-trips and malformed-header tests;
Blender import/export/material/profile smoke checks; build orchestration with
explicit fake compilers. These do not establish real Valve compilation or HL2
runtime behavior. Real testing awaits the installed game and SDK toolchain.

Schema references: Valve's [VBSP VMF reader](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/utils/vbsp/map.cpp)
and [BSP header definitions](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/bspfile.h).

## 0.10.31 update — real HL2 brush workflow

- **Browse Source Materials** searches material names from the configured game's
  VPKs and loose files. Apply Face Texture now creates a real base-texture preview
  and uses the VTF's actual dimensions for UV projection, rather than 512×512.
  Load Map Texture Previews resolves imported faces; Show Textures in Viewport
  enables textured display. Private previews can be packed in your `.blend`.
- Asset mounts follow gameinfo SearchPaths order, including HL2 custom folders,
  VPK split archives and inline/preload data. Entries are bounded and CRC-checked.
  VMT Patch include/insert/replace are supported with cycle limits. VTF 7.0–7.5
  previews cover DXT1/3/5 and common RGB/RGBA/intensity formats, using a mip up to
  512 pixels but retaining original dimensions for projection.
- **Source Entity Outputs** adds, edits and removes repeated outputs for point
  and brush entities: output, target, input, parameter, delay and fire-once.
  It preserves the standard HL2 comma-separated connection syntax.
- Imported side IDs are remapped when writing overlays/cubemap `sides` references.
  Missing or duplicated referenced IDs now cause an explicit error instead of
  silently pointing at a different face. Reassign affected references after duplication.
- VBSP/VVIS/VRAD each have configurable argument arrays. Compiler discovery accepts
  `vbsp++`, `vvis++`, `vrad++`; `WAVELENGTH_SOURCE_TOOLS` supplies a tools directory.
  On this development host the local tools live outside the repository under
  `../bin/source-tools-plusplus/tools++_linux`.

Validated against the installed Linux HL2 game: 5,293 indexed materials; real VTF
previews and dimensions; Blender import/export and output editing; successful
native VBSP++ → VVIS++ → VRAD++ compilation of the six-brush room to the selected
BSP destination. The Steam-launched game logged `Spawn Server` for that BSP.
The fixture and `.blend` are under the outer workspace's `maps/source1-smoke`.
The native [Tools++ publisher](https://ficool2.github.io/HammerPlusPlus-Website/tools.html)
provides a separate download. The locally downloaded compilers are **not**
redistributed in Wavelength source or release archives.

Run `tests/blender_source_game_smoke.py` through Blender for the opt-in real-game
integration test. Set `WL_HL2_GAME`, `WAVELENGTH_SOURCE_TOOLS`, and
`WL_SOURCE_TEST_OUTPUT` to override discovery and destinations. The ordinary unit
suite does not need proprietary game files.

### Remaining scope, not full Hammer parity

The new features supersede the previous VTF-preview, I/O-editor and side-ID-remap
limitations above. Displacements, model mesh/animation previews, instance expansion,
full FGD dialect coverage, visual overlay placement, advanced shader rendering
(blends/proxies/reflections), volume/cubemap/unsupported VTF formats and automatic
Proton-prefix provisioning remain incomplete. Unsupported displacement imports
are still rejected, not flattened. The Windows profile's VMF/build argument paths
are tested; Windows/Proton game execution has not been certified by Linux tests.

Format references: [Valve VTF structures](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/vtf/vtf.h),
[Valve image formats](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/bitmap/imageformat.h),
and the [VPK reader implementation](https://github.com/ValvePython/vpk/blob/master/vpk/__init__.py).

## 0.10.32 corrections and verification boundary

Source materials now use the same three-column thumbnail gallery as WADs. Its
native list row height matches the cards, so the scrollbar spans the gallery.
The gallery was visually checked in Blender. Project files retain Source stage
arguments. Source builds retain their final basename through VMF, BSP and launch;
renaming a temporary `level.bsp` could invalidate map-specific embedded assets.
Current installations prefer `hl2_complete` when available and Tools++ receives
explicit singleplayer mode.

Runtime success is **not yet confirmed**. A stock HL2 map reached gameplay and
returned player coordinates. Custom-map test processes exited before the gameplay
marker, including a Vulkan retry. The earlier Spawn Server message was insufficient
proof of a working map. Investigation stopped at the user's requested milestone;
do not claim this release resolves every HL2 load failure.
