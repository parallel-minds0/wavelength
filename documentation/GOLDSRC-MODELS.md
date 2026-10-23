# HL1 / GoldSrc entity models

Choose a GoldSrc profile. In **Scene Properties → Project & Toolchain**, set
**Game Directory** to the installed game/mod directory, such as
`C:\Program Files (x86)\Steam\steamapps\common\Half-Life\valve`.
Use your mod's FGD when appropriate.

Placing supported entities now loads actual textured viewport geometry directly
from GoldSrc MDL version 10 files. No decompilation or preconverted glTF library
is needed. Examples include `monster_scientist`, `monster_human_grunt`,
`monster_headcrab`, `weapon_crowbar` and `item_healthkit`.

Resolution prefers an explicit `.mdl` model property, then the active FGD's
literal studio representation, then known stock model mappings. Weapon
representations use world models rather than first-person view models. The
selected mod's loose files take precedence over its PAK archives, then configured
fallback content and base `valve` content. Separate texture MDLs and pose sequence
companions are loaded when needed. Missing models report their path/class rather
than silently substituting a different game's asset.

Meshes include decoded palette textures, UVs, normals, skin selection and encoded
bodygroups. An idle pose is preferred when available; an explicit `sequence`
property selects that sequence's first frame. This is a posed representation,
not imported animation playback or a rig-editing workflow. Masked/fullbright
material basics are supported; chrome and additive effects are approximations.

The entity remains the exported engine entity. Its visual mesh is parented,
selectable through the entity workflow, and excluded from brush export. Geometry
uses the profile's meters-per-unit setting once, preserving the original model
origin. Repeated placements share meshes and materials. Changing and applying
model, skin, body or sequence properties refreshes the representation.

Decoded models are cached in a bounded in-memory cache; dependency changes
invalidate entries. Textures and reference meshes survive .blend save/reload.
Missing and legacy glTF entity representations are prepared progressively when
opening a scene in the active wavelength workspace.

The [profile setup system](PROFILE-SETUP.md) now prepares persistent entity/model
thumbnails through an external worker. Placed geometry still uses the bounded
in-memory decode cache. Custom GoldSrc model compilation remains separate work.
