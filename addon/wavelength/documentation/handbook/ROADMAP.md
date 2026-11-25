# wavelength integrated project roadmap

Revised 19 November 2026, following release v0.51.0-pre.alpha.

This is the current eight-milestone product roadmap. The older
[roadmap snapshot](ROADMAP-STATUS.md) retains the original work-package history.
The [feature ledger](FEATURES.md) records existing behavioral contracts; this
roadmap describes intended work, not newly implemented capabilities. No runtime
acceptance tests were rerun for this planning revision.

## One project model

The organizing requirement is cohesive integration. Revisions are not a second
scene database bolted onto models, terrain or procedural tools. One project model
describes authored objects, reusable definitions, placements, relationships,
dependencies and their revisions. Blender remains the authoring and evaluation
environment. wavelength records identity, provenance, selection of versions and
engine interpretation around native meshes, Actions, NLA, modifiers and Geometry
Nodes. Representing these consistently does not require copying every Blender
datablock into another graph or inventing a replacement evaluator.

An object has stable identity; a revision identifies authored state; a placement
references a definition; a relationship records how objects depend on each other.
A composition selects a coherent set of revisions and evaluation choices for a
map, region or output. It is itself versioned. This is the user-facing meaning
of a meta revision. A scope limits the objects and aspects an operation affects;
it is not a separate history implementation per tool.

Keep three axes distinct within that model:

| Axis | Meaning |
| --- | --- |
| Revision history | Which authored version of geometry, recipe, material, clip or relationship is selected? |
| Evaluation time/state | Which pose, animation sample or simulation state is evaluated? |
| Composition | Which compatible choices are assembled for this output? |

A presentation timeline can sequence compositions and scoped states. It must not
silently turn animation scrubbing into design-history restoration. Arbitrary
topology revisions switch discretely unless an explicit compatible animation or
blend defines a transition.

Use Blender's existing Timeline, Dope Sheet, NLA and markers for temporal UI.
Native Actions and NLA retain animation ownership. wavelength adds references to
composition/state bindings and contextual revision controls in those editors;
it does not build a parallel timeline. Revision history remains an inspectable
history view, while a marker or supported track binding can select a composition
at a scene frame. The binding format and editor extension points must be verified
during the vertical proof rather than assuming markers provide a full track API.
A held animation sample uses a local time binding independent of the scene
playhead. Scrubbing previews the selected composition without restoring or
rewriting the working project. Existing user markers and animation tracks survive.

## The eight major milestones

| # | Milestone | Revised completion gate | Current position and revision integration |
| --- | --- | --- | --- |
| 1 | Engine-aware editor foundation | Profiles, units, interaction, persistence and diagnostics agree. Stable project identity and dependency references survive rename, duplication and reopen. | Existing foundation; general revision/composition semantics are planned. Introduce shared identity and persistence before widening history UI. |
| 2 | Core level authoring | Brushes, meshes, cutting, terrain, painting and materials have consistent selection, preview, cancel and undo. Scoped capture and comparison preserve native authoring data. | Existing tools and bounded checkpoints; integrate common scope semantics without replacing native editing or changing export inclusion. |
| 3 | Procedural level design | Inspectable relationships drive generators. Recipes, input revisions, overrides and chosen results are reproducible. Preview, apply, pin, detach and update share one dependency model. | Landing stairs, fence routes and terrain relationships provide bounded implementations. Shared revision-aware evaluation and composition integration remain planned. This is the main integration milestone, not a separate procedural history product. |
| 4 | Assets, models and native entities | Definitions and placements support shared/unique edits, materials, collision, animation and profile-aware transfer. A placement can pin a clip revision and hold/play state independently. | Source model pipeline and named model revisions exist with documented limits. General component pins, frozen animation bindings and cross-engine acceptance remain open. |
| 5 | Skies, lighting and simulation | Lighting, skies and simulation participate in the same compositions. Repeatable evaluation retains required caches and seeds; unsupported or missing inputs are explicit. | Partial preview support. Common state selection, cache retention and broader native output verification remain open. |
| 6 | Export, compile and package | Rendering, Game Preview, native builds and supported regular exports consume the same resolved composition. Each job retains exact dependencies and conversion decisions while editing continues. | Existing exporters and compiler paths; unified composition resolution and output manifests remain planned. Engine-specific limits stay explicit. |
| 7 | Migration and project consolidation | Existing model/terrain checkpoints and project bindings migrate into the common model without losing history or changing authored geometry. Old interfaces retire only after behavior and data preservation checks. | Existing checkpoint formats must remain readable. Migration is designed alongside each integration step, with consolidation completed here. |
| 8 | Installer, release and acceptance | Clean install, repair and portable handoff preserve the model and its retained dependencies. Representative workflows pass save/reopen, render, export and supported in-game acceptance. | v0.51.0 pre-release infrastructure exists; full product acceptance remains open. No completion inferred from packaging success. |

These are overlapping product milestones, not a claim that earlier rows are fully
finished. Revisions cut across them; adding a ninth isolated revision milestone
would obscure the integration requirement.

## Procedural layer within the model

A procedural relationship is authored project state. A fitted stair depends on
landing identities, selected landing revisions, the stair recipe and overrides.
Its generated mesh is an evaluated result, not the only surviving record.

During editing, a binding can follow current inputs. A pinned composition fixes
the exact recipe and dependency revisions. Updating landings then produces a
new candidate result without rewriting the pinned output. Applying a candidate
checks its expected base revision so a stale preview cannot replace newer work.

For a terrain network, capture the cage, relevant node/modifier definitions,
paint attributes, materials, anchors, seeds and external images needed to evaluate
the selected state. Network scope follows explicit membership and dependencies,
not accidental proximity. Native modifier viewport/render switches remain native
evaluation choices; toggling them does not itself create a named revision.

Follow current, pin, make unique, detach, preview, apply and bake must have the
same meanings for models, terrain and procedural assemblies. Detach creates
independent editable content with provenance and does not mutate shared sources.
Bake produces an explicit derived artifact; it need not discard the recipe.
Existing tool-specific semantics must be audited before harmonization, not
silently changed by a refactor.

## Composition and scope rules to establish first

- Inspection is read-only. Restore publishes a new change; it does not erase the
  intervening history. Ctrl-Z remains Blender's immediate editing mechanism.
- Capture both the selected objects and declared aspects: geometry, placement,
  materials, animation, entity fields or a complete assembly. State the affected
  scope before applying a shared change.
- Preserve dependency closure. A clip pin includes its compatible rig and other
  required inputs. Historical geometry cannot silently read today's mutable
  node group, image or external model and still claim reproducibility.
- Resolve a map baseline, then explicit assembly and placement overrides.
  Same-level ambiguity is an error; topology, rig and relationship compatibility
  must be checked even when override precedence is unambiguous.
- Resolve scope membership when saving a composition. Query-based working scopes
  may remain dynamic, but a frozen build records exact membership and deletions.
- Subobject references belong to a source revision. Topology changes that break
  a face/vertex/snippet binding require explicit remapping or a visible unresolved
  state. Object names and current indices are insufficient persistent identity.
- Preserve dependencies of pinned states until explicitly released. Retention,
  portable packaging and missing external resources must be visible. A missing
  retained revision never silently resolves to latest.
- Rendering, preview and export use one resolved selection. Format adapters may
  bake or reject unsupported states, recording the decision rather than changing
  the authored project or pretending engines have identical capabilities.

## Implementation sequence inside the milestones

1. **Shared contract and persistence (M1, M7).** Specify identity, revision,
   scope, component binding, composition and dependency closure. Audit current
   model/terrain checkpoints and native Blender relationships. Define migration
   and failure behavior before introducing another checkpoint format.
2. **One vertical proof (M2, M4, M6).** Two placements of one wall, five animated
   states, independent clip-revision pins and hold/play choices, two compositions.
   Editing a shared source leaves pinned outputs intact. Save/reopen, render and
   one supported engine export agree on the selected state. This validates the
   shared model; it is not a separate wall feature.
3. **Procedural integration (M3).** Use the same mechanism for fitted stairs and
   a terrain assembly. Pin recipe and input versions, inspect candidates, detect
   stale previews, update explicitly, detach and retain provenance. Verify that
   unrelated placements and compositions remain unchanged.
4. **Map-wide composition (M1–M6).** Extend the demonstrated model to whole maps,
   region overrides, component comparison and scoped restore. Add presentation
   timeline sequencing after static composition semantics work. Resolve all
   render/build inputs at job start; retain caches where evaluation needs them.
5. **Consolidation and acceptance (M7, M8).** Migrate existing checkpoints, package
   retained dependencies and validate representative workflows. Remove duplicate
   legacy interfaces only after migration and regression evidence exist.

Do not begin with a general history browser, distributed collaboration, arbitrary
mesh merging or a replacement for Blender's timeline. The next implementation
unit is the shared contract plus the smallest persisted wall proof. No such
implementation is delivered by this roadmap update.

## Preservation and evidence

### Privateer environment authoring priority

The 24 November 2026 priority adds a concrete M2/M3/M4/M6 vertical slice before
the earlier animated-wall proof: independently paintable terrain masks, reusable
prototype palettes, deterministic rules and persistent placement overrides, with
a modular Godot handoff. These are authored recipe/input/override records in the
same procedural model; instances are evaluated results. Sculpting and material
painting remain independent of object distribution.

The initial small patch implementation and its limits are recorded in
[Environment painting and distribution](user/environment-layers.md), contracts
WL-ENV-001 through 004. Existing Privateer terrain, biome shading and 103,047
scripted trees remain preserved inputs. Full adoption requires an explicit
placement/mask migration and the game's biome/streaming adapter. General revision
composition semantics and the native Blender timeline plan remain unchanged;
this vertical slice does not claim their completion.

The first implementation audit must cover WL-MODEL-027/028 (named revisions and
placement restore), WL-TERR-013/014 (terrain checkpoints and evaluated output),
WL-GEO-019/020 (landing stairs and fence routes), and WL-CTX-006 through 009
(visibility and export membership). These existing contracts remain in force.
New implementation behavior requires new stable IDs and meaningful regression
evidence; this planning document does not mark proposed capabilities delivered.

Acceptance must prove compatible dependency capture, independent/shared edits,
stale-preview rejection, save/reopen, restore-as-new-change, missing dependency
handling, source preservation and viewport/render/export agreement. Historical
artifacts or successful compilation alone do not prove current runtime behavior.
