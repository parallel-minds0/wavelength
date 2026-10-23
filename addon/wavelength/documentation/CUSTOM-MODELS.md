# Editable custom Source models

In the Wavelength workspace, choose a Source 1 game profile and configure its
game directory and compiler directory. The compiler directory must include that
game's StudioMDL as well as the map compilers. This workflow currently targets
Source 1; GoldSrc and Quake model compilation are not implemented here.

1. Model normally in Blender, UV unwrap it and assign materials. Mesh modifiers
   are evaluated during compilation. Use ordinary Blender export whenever desired.
2. Place an appropriate engine entity: `prop_static` for static geometry,
   `prop_dynamic` for animation, or `prop_physics` for a rigid physical object.
3. Select the source meshes and any armature together with one placed entity.
   Either selection order works; clicking the entity's model preview also works.
   If multiple entities are selected, make the intended entity active.
   In Object Mode, use **Object → Assign Selected Model to Entity**
   in the viewport, or search the same name with F3. The entity's Object
   Properties also has an **Assign Selected Model to Entity** button.
4. Open **Object Properties → Wavelength Custom Model** on the entity or a source
   mesh. Set collision, animation clips and deployment as needed.
5. **Build Map** compiles changed custom models before the map, validates the
   results, then publishes their dependencies with the completed map.

The source objects stay visible and editable. They become children of the entity
and are excluded from brush export. Move/rotate the entity to place the complete
model; edit its source meshes to reshape it. Keep entity scale at 1 and resize the
sources instead. Assignment preserves existing world-space source placement,
so place sources around the intended entity origin before assigning them.
Deleting a source object from the scene removes it from the next model build,
even if Blender retains an internal reference for undo or saved ownership.

Select more meshes and the same entity, then use **Add Selected Sources** to add
them. **Detach Custom Model** restores independent source objects and the entity's
previous stock model. An ordinary parent preserves their transforms and animated
placement. Assignment and detachment support Blender undo. Ownership and settings
are saved in the .blend file and remain tied to the originating engine/game profile.

## Materials

Brush entities such as `func_door_rotating` cannot reference MDL models. They
require convex BSP solids and the **Make Brush Entity** workflow. A model-based
door uses `prop_door_rotating`, where the game supports it; its model must also
satisfy that entity's door-specific requirements. Wavelength generates a convex
collision hull and basic silent door sound/surface metadata. Set sounds through
the entity's sound overrides if desired. Place its entity origin at the intended
hinge; Source rotates this door around the entity's vertical axis. Existing
custom door assignments without collision acquire a convex hull on their next
map build.

Supported Blender materials use a directly connected Principled BSDF with a
constant base color or a directly connected image texture. Images must have
power-of-two dimensions, up to 4096 pixels per side. One UV set per material is
supported. Tangent-space normal maps at strength 1 and base-image alpha are
supported. Export generates Source VertexLitGeneric materials and VTF textures.
This is a basic Source shader conversion, not a complete Blender PBR match;
constant roughness is not reproduced. Bake procedural textures, complex shader
graphs and unsupported PBR effects first.

Source textures assigned through Wavelength use the game's existing texture
dependencies. The tool preserves unwrapped UVs rather than projecting brush UVs
onto model sources. Blended terrain materials must be baked to one model texture.

## Animation and collision

Animation clips sample the current scene/NLA evaluation over inclusive frame
ranges. Clips have a sequence name, start/end frames, FPS, loop option and optional
game-specific Source activity. An assigned animation creates an initial clip using
the scene's range; add further ranges in Object Properties. Actions must be active
or arranged on the NLA timeline: unused actions are not exported automatically.

Rigid object animation and one weighted armature are supported, with up to 128
exported nodes and three bone influences per vertex. Apply object/armature scale
before animated export. Animated shape keys, animated scaling and arbitrary
time-dependent mesh deformation need a separate baking/export workflow.

Physics props default to a convex collision hull. Optionally choose another mesh
among the assigned sources as the collision input; it is also converted to one
convex hull and omitted from render geometry. Configure mass, surface property and
the game's physics prop-data base (default `Metal.Small`). Custom articulated
ragdolls, concave collision decomposition, flexes, attachments and LOD generation
are outside this implementation. A physics prop cannot use shape animation.

## Deployment

- **Inside BSP** is the project default. Generated MDL/VVD/VTX/PHY files and owned
  VMT/VTF files enter the BSP's pakfile. Compilation uses a staged game directory
  with the original game mounts; this mode does not write models into the game.
- **Game Directory** writes generated files into the active game or a directory
  already mounted by it. Leave the directory blank to use the profile's game
  directory. Publishing happens after a successful map build. Models remain
  ordinary entity references in the map.

Each custom asset has a stable `models/wavelength/<id>/model.mdl` path and a
project-local `.wavelength/models` cache. Geometry, material, animation or compiler
changes invalidate the cache; moving the entity does not force recompilation.
Existing game textures referenced by a Source material remain game dependencies.
Generated models can be copied from the cache for standalone distribution along
with their companion files and owned materials.
