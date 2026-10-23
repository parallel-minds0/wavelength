# wavelength TODO

Updated: 21 October 2026. Current local build: **v0.50.0**.

## Profile registry

- [x] Protected shipped template hierarchy and inherited user registrations.
- [x] Register/remove/reparent, stable identities, legacy migration and portable bundles.
- [ ] Implement and verify additional Source game compiler adapters before enabling their Build/Play workflows.

## Mesh engine adapters

- [x] Godot 4 GLB export with textures/UVs and verified physical scale/orientation.
- [x] CS2 FBX/VMAT/ModelDoc handoff, verified through the installed resource compiler.
- [x] CS2 material indexing, compiled texture decoding and background thumbnails.
- [ ] Full custom Source 2 normal/metalness/opacity and layered-shader conversion.
- [ ] Optional collision export for Godot and Source 2.
- [x] Source 2 editable VMAP polygon mesh import/export, with per-face materials and UVs.
- [ ] Source 2 subdivided surfaces, prefab references and compiled-map decompilation.
- [ ] Engine-specific entities and scene integration after mesh workflows stabilize.

## CSG follow-up

- [x] Editable Geometry Nodes Subtract, Union and Intersect with cancellation.
- [x] Bounded, validated convex BSP partition and shared pencil solid conversion.
- [ ] Merge adjacent convex cells to reduce brush count without changing volume.
- [ ] Preserve custom per-face engine UV offsets/scales through BSP conversion.
- [ ] Add draw-a-cutter entry from the CSG panel; current workflow uses two existing finalized meshes.
- [ ] Verify generated CSG maps in each supported engine compiler and runtime.

This is the working backlog. Checked items have recorded verification; unchecked
items are remaining work, not claims of existing support. Release history is in
[RELEASE-NOTES](docs/RELEASE-NOTES.md). The older
[roadmap snapshot](docs/ROADMAP-STATUS.md) retains the original milestone plan.

## Next: stabilize model authoring

- [ ] Show the assigned source objects in the entity's properties, with triangle
  counts and explicit Add/Remove Source actions. Make it obvious what will compile.
- [ ] Add model preflight diagnostics: evaluated geometry counts, compiler limits,
  UVs, bone influences, collision and material compatibility. Name the offending
  object and offer actionable guidance before StudioMDL runs. Do not silently
  reduce geometry or change the user's mesh.
- [ ] Verify runtime behavior in HL2 and GMod for custom static props, physics
  props, animation and model doors. Check visibility, collision, interaction,
  hinge placement and map reloads; successful compilation alone is insufficient.
- [ ] Verify source deletion and undo/redo across save/reload, multiple scenes,
  entity duplication, detachment and reassignment. Keep ownership consistent and
  expose missing sources clearly.
- [ ] Make brush-entity versus model-entity workflows clear during entity creation
  and browser placement. Prevent brush-only classes becoming misleading empty
  placements; provide a direct path to attaching valid brush geometry.
- [ ] Turn the manual Valve BSPZIP byte checks into a repeatable integration
  fixture. Validate packed assets with the engine tools, not just Python ZIP.
- [ ] Improve failed-build feedback: identify the asset, source object, compiler
  stage and relevant log excerpt. Preserve the last usable output.

## Model pipeline expansion

- [x] Implement the profile content-library setup lifecycle: configuration,
  validation, indexing, progressive preparation, pause/cancel and incremental
  invalidation. Keep it separate from geometry and workspace state machines.
- [x] Generate cached thumbnails from real model geometry in an external worker;
  prioritize requested assets and avoid loading the whole library into the scene.
- [ ] Extend preparation beyond the implemented disk thumbnail cache: persist
  decoded geometry for on-demand placement as well. GoldSrc geometry currently
  uses a bounded in-memory cache; its thumbnail preparation now runs externally.
- [ ] Extend entity-model resolution for game-code-selected variants beyond FGD
  literals, with game/mod-specific rules and explicit editor overrides.

- [ ] Provide a dedicated standalone compiled-model export using the same build
  definition, materials and dependencies as map builds.
- [ ] Define reusable model assets and instances, with clear shared versus unique
  editing and rebuild behavior.
- [ ] Add richer Source material controls/baking, with an honest viewport preview
  of supported effects and explicit handling of dependencies from custom content.
- [ ] Add model-specific support where needed: concave collision decomposition,
  articulated ragdolls, attachments, LODs, flexes and richer animation export.
  Validate each against the selected game's actual capabilities.
- [ ] Improve model asset thumbnails, search responsiveness and selection feedback
  without eagerly loading every model into Blender.

## Profiles, ownership and Geometry Nodes

- [ ] Complete hierarchical profile capabilities: inherit only relevant tools,
  UI, geometry constraints, compilers and backend behavior.
- [ ] Implement profile-switch lifecycle: detect unfinished/procedural content,
  request explicit finalization where required, and preserve finalized geometry
  and its original ownership. Do not silently reinterpret existing geometry.
- [ ] Implement workspace Active/Suspended lifecycle separately from profile
  switching, preserving authored state when leaving Wavelength.
- [ ] Migrate remaining generative geometry to Geometry Nodes, starting with
  arches and curved stairs; straight stairs and terrain already have node paths.
- [ ] Replace remaining procedural modal previews with node-driven previews and
  keep parameter editing, finalization, materials and export consistent.

## Terrain and Source displacements — paused for now

- [ ] Finish in-game acceptance for standalone terrain, converted brush faces,
  caves and sewn networks: winding, visibility, collision and visible gaps.
- [ ] Verify painting, texture blending and mesh deformation survive Source
  export and compilation, including mixed-power seams.
- [ ] Support partial-edge stitching; current sewing targets matching full edges.
- [ ] Keep general Blender terrain separate from the Source displacement adapter.

## Engine coverage and release readiness

- [ ] Record a capability matrix for Quake/idTech, GoldSrc, HL2 and GMod:
  authoring, textures, entities, models, compilation, packaging and runtime tests.
  Distinguish implemented features from tested workflows.
- [ ] Implement missing GoldSrc and Quake model workflows through their own
  adapters. The current custom StudioMDL pipeline is Source 1 only.
- [ ] Recheck Linux and Windows workflows after the recent editor changes.
- [ ] Update the README/version summary, user guides and milestone status to
  reflect the current local feature set and its limitations.
- [ ] Package and smoke-test a clean installer; verify install, upgrade, repair
  and uninstall against the supported Blender build.
- [ ] Prepare release notes/assets and publish the next GitHub release when
  requested. Recent v0.36.x changes are local and not yet a published release.

## Later research

- [ ] Design the contextual engine on top of Geometry Nodes after ownership,
  profiles and dependency boundaries are stable.
- [ ] Define a future Godot profile without inheriting BSP-only restrictions.

## Recently verified

- [x] Direct installed HL1 entity meshes and palette textures, mod/PAK lookup,
  profile units, posed bones, bodygroups, separate companions, shared data,
  save/reload and migration from old glTF representations.

- [x] Source FGD-defined world models for crowbar/pistol/healthkit entities, without
  editable model fields or changes to their exported entity properties.

- [x] Custom Source model assignment from either selection order and entity previews.
- [x] Assignment is reachable through Object menu, F3 and entity properties.
- [x] Real StudioMDL compilation for static, rigid animated, skeletal and physics models.
- [x] Custom model dependencies compile before map stages; BSP and mounted-directory
  deployment paths have verification fixtures.
- [x] Correct omitted FGD defaults and clean old invalid reference defaults on export.
- [x] Generate model-door collision and basic door metadata.
- [x] Store BSP assets in a Source-compatible format; Valve extraction matches
  packaged model/material/texture bytes.
- [x] Exclude deleted sources retained only by internal collections. The reported
  low-detail Suzanne compiles at 968 triangles and its map build succeeds.

Maintenance rule: update this list as work lands, and record what was actually
tested before checking an item. New features should carry their remaining gaps here.

## Context policy

- [x] Central context capabilities, workspace gating, clean viewport/render helper visibility, per-object role overrides and reversible transitions. See [Context guide](docs/CONTEXT.md).
- [ ] Expand engine-specific utility classification as additional profiles are supported; verify full production scenes and linked library workflows.

## Surface workflow

- [x] Face-aware Asset Browser material assignment, texture/entity-class eyedropper, held asset use and browser mapping settings.
- [ ] Further Hammer 2 surface editing parity: interactive UV handles, additional material channels and profile-specific advanced attributes.
