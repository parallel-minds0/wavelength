# Source 1 models

```{screenshot} entity-model-assignment
:alt: Selected model-capable entity and the native Models catalog
Capture a placed prop entity, model thumbnails, and the assignment control.
```

[Profile Setup](PROFILE-SETUP.md) prepares rendered entity/model thumbnails in the
background. Configure the game paths and open Scene Properties → wavelength Map
→ Profile Setup to view progress or pause/resume preparation. The native browser
imports cached images progressively without loading every model into your scene.

Entities with fixed world models also display actual viewport geometry. For
example, placing `weapon_crowbar` loads `models/weapons/w_crowbar.mdl`; pistol and
healthkit placements resolve through the selected game's FGD in the same way.
Literal `studio(...)` declarations and inherited defaults supply editor visuals
without adding fake `model` properties to the map. Explicit model properties take
precedence. Clicking the visual selects its owning entity. Missing representations
in older scenes are prepared progressively when the wavelength workspace is active.
This supports FGD-defined world models; entities whose visuals are chosen only by
game code still need a game-specific resolver.

For editable Blender meshes compiled into map entities, see
[Custom Models](CUSTOM-MODELS.md). Select your sources, select the entity last,
then use **F3 → Assign Selected Model to Entity**. Build Map compiles and deploys
the result, either inside the BSP or into the mounted game directory.

Activate an HL2 or Garry's Mod profile with its game directory configured.
Create or select an engine entity with a studio-model property, such as
`prop_physics`, `prop_dynamic`, `prop_static`, a vehicle or a ragdoll. In the
wavelength workspace the native Asset Browser opens/switches to **Models**.
Search its model choices, select a tile and press **Assign Model**. A dragged
model choice also assigns to the previously selected entity. The entity keeps
its class, transform and other properties; its existing visual reference is
replaced rather than creating another prop or a loose mesh.
Clicking a model's visible geometry selects its owning entity, so moving it
moves the engine prop rather than only the preview. Existing saved model previews
are made selectable when the file loads. Dropped entity assets become the active
entity before the browser switches to its model choices.
Older scene placements left as excluded browser templates are recovered on load
and add-on initialization. Their names, properties, identities and transforms are
retained. Background model publication pauses while a model tile is selected.

Capability comes from inherited game FGD property types, including GMod's
`*studio` fields. Entities without such properties do not enter model context.
If there are several model fields, use **Model Property** to choose which one to
edit. Fields such as `env_shooter.shootmodel` set that property without pretending
the spawned model is the entity's own body. Model changes reset existing skin/body
selection to zero. Physics props require the matching `.phy`; static props reject
models not compiled for static-prop use.

Model tiles are lightweight metadata choices, published in short batches;
geometry and textures load only when a model is chosen. Filtered searches
prioritize matching pending choices and pause unrelated publication. Selecting
a non-model entity restores the previous browser section.

Alternatively, **Shift+A → Add Source Model**, or **F3 → Add Source Model**, creates
a new engine prop directly. Search the
mounted game's model paths and select one. It appears at the 3D cursor with
actual geometry, UVs, normals and available Source materials. Use Material
Preview to see textures. Loose game folders and VPK archives use the profile's
existing mount order; no archive extraction is necessary.

The selected parent is the engine prop. Move and rotate it with Blender's tools.
Its child mesh is an editor reference, excluded from brush export. A model built
for static props uses `prop_static`; other models use `prop_dynamic`. Map export
retains the original `models/...mdl` path. Edit entity properties to change the
model, skin or body, then Apply to refresh its preview. Repeated placements share
mesh and material data.

**File → Import → Source Model (.mdl)** imports a loose file as a standalone,
editable reference mesh. Keep its matching `.vvd` and `.dx90.vtx` companions beside
it. The import options include skin and body selection. Materials resolve through
the active game's mounts. This standalone mesh is excluded from map export;
use Add Source Model when placing an engine prop.

This first implementation reads reference-pose geometry in the standard Source
MDL 44–49 / VVD 4 / VTX 7 layouts, tested with installed HL2 props/characters and
a GMod player model. Animation, rigs, facial flexes, collision meshes, LOD switching
are separate from reference-pose importing. Compiling authored Blender models is
available through the custom-model workflow above. Specialized engine
shaders use the available base-texture preview; unsupported materials are marked
with a magenta fallback rather than preventing geometry import. Missing or
mismatched companions report an error before a prop is created. Source 2 model
formats and GoldSrc MDL version 10 use different formats and are not handled by
this importer.

Format references: Valve's [studio.h](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/studio.h)
and [optimize.h](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/optimize.h).

## Game entity catalog

Source profiles load the installed game's own Hammer definitions: `bin/halflife2.fgd`
for HL2 and `bin/garrysmod.fgd` for GMod, following their includes and inheritance.
All concrete FGD class types are listed, including NPC, filter and movement classes;
base definitions are excluded. Point and brush entity kinds remain distinct:
brush classes require brushes and **Make Brush Entity**, rather than an empty point.

The tested installations expose 461 HL2 classes and 487 GMod classes. Counts depend
on the installed game's definitions. GMod-only classes are not added to HL2, and
future Source profiles must declare their own definition file. These are each
game's mapping definitions, not a union of runtime/internal classes across Source
branches. A configured project/mod FGD explicitly overrides automatic detection;
it should include that mod's intended game bases. Missing definitions report an
error rather than silently substituting another game's entity list. Included-file
changes invalidate the schema cache automatically.
