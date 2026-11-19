# Cross-compile a level between profiles

Cross-compiling adapts a level for another engine profile while leaving the
Blender authoring scene and its active profile unchanged. Geometry export,
material conversion, entity conversion, visibility settings and project
packaging share the target backend. Support is explicit: a profile pair with a
stub backend refuses the operation before writing an output.

## Source 1 to CS2

1. Import the VMF with its Source 1 profile and mounted assets.
2. Open **Scene Properties → wavelength Map → Project & Toolchain →
   Cross-Compile Level**.
3. Check **Source Profile**, choose the CS2 **Target Profile**, and select a
   `.vmap` destination. Optional target game/compiler directory fields override
   the detected CS2 installation. You do not have to change the source profile.
4. Material conversion and legacy texture-scale repair are automatic. Optionally
   set **Source Game Directory**, enable **Use Loaded Textures if Source Game Is Missing**
   or **Ignore Material Conversion Errors**, and choose selection/package options.
5. Export, then review **wavelength Cross-Compile Report** in Blender's Text
   Editor or the adjacent `<map>.crosscompile.json` file.

Regular VMAP export also offers **Convert Compatible Entities**, enabled by
default. Turn it off for mesh-only output. Cross-profile export uses Balanced
64-unit visibility sampling by default; regular VMAP export exposes all
visibility quality settings. See [CS2 maps and materials](source2-maps.md) for
material conversion and deployment requirements.

```{screenshot} cross-compile-profiles
:alt: Cross-compile file browser with source and target profiles
Capture the source/target profiles, target directories and package option.
```

## Current entity coverage

| Source 1 entity | CS2 result |
| --- | --- |
| `info_player_start` | Same class and world pose |
| `info_player_terrorist`, `info_player_counterterrorist` | Same class, pose, name, priority and enabled state |
| `info_target`, `info_landmark` | Same class, pose and name |
| `func_detail` | Editable meshes with Exclude From VIS enabled, preserving detail geometry without structural visibility blocking |
| `func_buyzone` | Entity containing its brush meshes, with team assignment |
| `func_bomb_target` | Entity containing its brush meshes and supported bomb-site properties |

Point transforms use current Blender world transforms, including edits since
import. Brush entity geometry remains grouped under its converted entity rather
than becoming solid world geometry. Export inclusion checkboxes still apply.

Props/model conversion, lighting, complex logic, entity I/O, and other classes
are currently manual/stub cases. Entities with Source I/O connections are not
presented as fully converted. The report retains original property pairs and
object transforms, material mappings and warnings, identifies unsupported classes and lists unconverted
properties on partially converted entities. Unsupported entities are omitted
from the VMAP; their originals remain in the Blender scene. Unsupported brush
geometry is not silently flattened into the world. The report is not a complete
geometry backup: keep the source VMF or Blender file for manual work.

## Other engine pairs

The common backend registry has explicit stubs for other profile families.
Selecting one shows that the route is not implemented; it does not claim a
successful cross-compile. This does not remove existing ordinary native exports
such as Godot mesh export or Source 1 VMF export.

Shared project ZIPs include the cross-compile report with the map and generated
material assets. Recipients still need their engine tools to compile the map.

## Geometry and texture fidelity

Clip/nodraw-only brushes remain in map exports even when their automatic role
marks them as helpers for clean Blender renders. Explicit export checkboxes and
explicit helper overrides still apply. Source 1 detail brushes become editable
CS2 meshes with `visexclude` enabled. Doors and breakables still require manual
entity conversion; the report lists these omissions.

The exporter preserves corner UVs and native editable face axes/scales, converting
projection scales from profile units to Source 2 inches. Ordinary meshes do not
reference empty subdivision UV streams. In the dorms regression, 492 world and
utility brushes plus 85 detail brushes and three supported brush-entity meshes
produce 580 meshes, with 3,505 world/detail face UVs checked against the source.
Native compiler UV checks passed on an isolated asymmetric test surface; complete
visual parity in Hammer remains a separate review.

## Selecting the source material installation

For legacy CS:GO maps, choose **CS:GO Legacy** as the source profile even if the
map was originally imported while Half-Life 2 was active. The selected source
profile's game directory is searched first. Recorded material roots are fallback
candidates only when they contain the requested mounted VMT; having a valid
`gameinfo.txt` alone is insufficient. **Source Game Directory** can explicitly
select another installation. For the standard Steam legacy install this is
`Counter-Strike Global Offensive/csgo`, not CS2's `game/csgo` directory.

Material provenance in the authoring scene is preserved. Missing original games
still require the existing explicit loaded-texture or placeholder options.
