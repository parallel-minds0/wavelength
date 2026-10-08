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
