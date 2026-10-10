# wavelength roadmap — original plan and current position

**Snapshot:** 10 October 2026  
**Published baseline:** `v0.12.1-pre.alpha`  
**Plan:** [init.txt](../../init.txt), revision 5, including the later interaction addendum.  
**Scope:** Nine original milestones and **101 work packages**, WP-001 through WP-101. The heading that says 91 packages predates the addendum.

This is a status document, not authorization to implement the remaining plan. Milestone names, package groups and exit gates below follow Part 17 of `init.txt`. Status is based on the current source, release history and recorded validation; this review did not rerun Blender or game acceptance tests.

## Latest grid update

v0.12.1 implements the later user clarification: wavelength owns the parent grid and profile-relative grey subdivisions inside its workspace, including a one-meter Blender/metric profile. Leaving restores native grid visibility. This supersedes the earlier requirement to retain Blender’s adaptive grid underneath the overlay. Bracket shortcuts adjust spacing; 133 unit tests and Blender UI checks cover the current update.

## Where we are now

We have a usable early level-authoring foundation, not the complete product described in `init.txt`.

- **Milestone 1:** Delivered foundation; broader snapping and platform validation remain.
- **Milestone 2:** Usable native Asset Browser and profiles; model previews are placement proxies and the complete asset system remains unfinished.
- **Milestone 3:** Full prop creation → compilation → placement → rebuild pipeline is still pending.
- **Milestone 4:** Stairs, arches and spheres are delivered. Basic Source geometry can compile and run in HL2. CSG, displacements and advanced face workflows remain.
- **Milestones 5–7:** Some existing engine/content features, but their complete acceptance workflows remain open.
- **Milestone 8:** Separate Pro repository exists; the advanced Pro generators are not delivered.
- **Milestone 9:** Installer and release work was brought forward. The v0.12.0 lifecycle milestone is published; overall stable-product acceptance remains open.

**The next major milestone in the original sequence is Milestone 3: the full prop pipeline**, alongside closing the outstanding Milestone 1–2 acceptance gaps. Completing installation work does not mean Milestones 3–8 are complete.

## What is already in the past

| Delivered stage | What it established | What it did not establish |
| --- | --- | --- |
| Earlier Quake / GoldSrc work | Engine units, MAP authoring/export, WAD textures, entity tools, compiler paths and configurable output destinations | Complete engine parity or a fresh certification of all game workflows |
| Earlier Source 1 work | HL2 Linux/Windows profiles, VMF handling, VPK/VMT/VTF material access, entity outputs and staged map compilation | Complete Hammer parity, decoded model geometry, displacement editing or certified Windows/Proton execution |
| v0.11.0 workspace / assets / primitives milestone | Persistent wavelength workspace, scoped switches, independent yellow map-unit overlay, transactional Object Mode movement, native Asset Browser integration, persistent profiles, editable stairs/arches/spheres, separate Free/Pro trees and synchronization | Universal interaction framework, complete Edit Mode snapping, full prop production or all native asset workflows |
| v0.11.2 installer force milestone | Python-only fallback, structural native-state detection, discovery, diagnostics and retained reinstall backups | General compiled C++ injection into Blender or certified native rendering |
| v0.11.3 playable HL2 milestone | Recorded Blender export and real VBSP/VVIS/VRAD compilation; a sealed textured room containing the primitives reached visible HL2 gameplay; renamed-BSP safeguards | Automated movement/collision acceptance, Build & Play or launch monitoring |
| v0.12.0 installer lifecycle milestone | Replace/reinstall, independent instances, full uninstall including adopted shader patches, repair/recover, updated menu, bundled Python and source ZIP; Free and Pro releases | Completion of the remaining editor roadmap or real-Blender native compatibility certification |

### Older statements that are now superseded

- “Installer only supports a fresh installation” is obsolete: replacement and repair now exist.
- “Uninstall preserves adopted native patches” is obsolete: recognized adopted patches are now structurally removed.
- “The grid is only a yellow text indicator” is obsolete: the workspace has an independent map-unit highlight overlay.
- The transform-settling timer is no longer the registered snapping solution; the dedicated engine move operator and gizmo use transactional Object Mode movement.
- The legacy custom texture gallery is no longer the intended browsing workflow. Its backend still exists, so **WP-017 is not finished**.
- Older “custom HL2 gameplay not confirmed” notes predate the successful v0.11.3 fixture. That success does not prove every custom map or Windows launch works.
- The optional embedded-shader patch is not a finished C++ renderer bridge. The current workspace grid does not require that patch.

## The nine milestones from init.txt

### 1. Establish a safe foundation

**Packages:** WP-001, WP-002, WP-003, WP-005, WP-006, WP-007, WP-008, WP-009, WP-010, WP-056.  
**Status:** Delivered baseline; acceptance remains bounded to tested configurations.

**Already present:** Repository audit, independent Free/Pro repositories, shared-code synchronization, persistent workspace, workspace-scoped controls, entity browsing, independent world-aligned engine-grid highlights, stable object identity, Object Mode precision movement and regression tests.

**Remaining:** Broader multi-window/platform/backend testing; complete smooth snapping behavior across native tools, Edit Mode, transforms and undo. Current Edit Mode uses Blender's native transforms plus an explicit Snap Selection to Grid operation, not the same replacement transform system as Object Mode.

**Original exit gate:** wavelength editing works reliably without interfering with other Blender workspaces.

### 2. Establish native asset workflows

**Packages:** WP-012, WP-013, WP-014, WP-015, WP-016, WP-018, WP-019, WP-020, WP-071.  
**Status:** Usable subset; not fully complete.

**Already present:** Native Asset Browser publishing, material previews from game assets, material application, entity/model/sound placement proxies, category filtering, stable asset metadata and persistent user profiles with create/edit/duplicate/import/export operations.

**Remaining:** Real model mesh/animation decoding and previews, full dependency tracking, separate persistent asset-library caches, broader asset/category support and a complete engine-independent entity registry. Material previews are not full engine shader rendering.

**Original exit gate:** Core assets can be discovered and used without the legacy gallery.

### 3. Establish the full prop pipeline

**Packages:** WP-023, WP-047, WP-048, WP-065, WP-077, WP-079.  
**Status:** Pending as an end-to-end workflow; next major milestone in the original sequence.

**Existing building blocks:** Blender modeling, model placement proxies, paths/tool discovery and map compilation infrastructure.

**Remaining:** Model source metadata, pivot/collision/LOD/skin/bodygroup configuration, appropriate SMD/DMX export, QC generation, real model compiler invocation, material/dependency publishing, automatic Asset Browser registration and rebuilding from the editable Blender source. Map compilation is not model compilation.

**Original exit gate:** A Source-compatible prop can be created, compiled, placed, modified, and rebuilt from Blender.

### 4. Establish proper world geometry

**Packages:** WP-027, WP-028, WP-029, WP-030, WP-031, WP-034, WP-064, WP-080, WP-081, WP-082.  
**Status:** Partial; requested standard primitives delivered.

**Already present:** Brush/plane/face geometry and validation foundations; MAP/VMF serializers; editable stairs, arches and polyhedral spheres; Source material projection and a representative compiled, playable HL2 room.

**Remaining:** Complete BSP-aware union/difference/intersection/clipping/splitting/decomposition; comprehensive canonical conversions and round trips; displacement terrain; level-aware face/edge/vertex editing; hotspot materials; modular tilesets; validated real-time texture behavior during all mesh edits.

**Primitive limits:** Parameters regenerate the assembly and preserve materials by part/face index. Arbitrary manual child-mesh edits are replaced on regeneration. Spheres currently expose controlled 20/80-face polyhedral detail.

**Original exit gate:** A representative Source 1 level can be modeled, textured, exported, and compiled. A small fixture has demonstrated this narrow path; the entire package group is not complete.

### 5. Establish complete level workflows

**Packages:** WP-066, WP-072, WP-073, WP-083, WP-085, WP-086, WP-087, WP-088, WP-089, WP-090, WP-091.  
**Status:** Partial foundations; full workflow pending.

**Already present:** Supported map parsing/export, entity properties, Source output rows, target/path helpers, scene classification, validation messages and staged map compilation.

**Remaining:** Reliable metadata-preserving import/edit/rebuild for representative existing levels; visgroups; map instances and compile regions; smart prefabs; integrated lighting/environment editing; visual entity I/O; complete path tools; visibility diagnostics; dependency-aware incremental builds; navigation; cameras, cables and selection/layer tools. Installer instances are unrelated to map instances.

**Original exit gate:** A representative level can be imported, modified, populated, validated, and rebuilt without losing supported metadata.

### 6. Expand engine integrations

**Packages:** WP-021, WP-022, WP-024, WP-025, WP-026, WP-032, WP-033, WP-035, WP-036, WP-037, WP-038, WP-039.  
**Status:** Classic-engine implementations exist; expansion and public SDK remain pending.

**Already present:** Quake, GoldSrc/HL1 and Source 1 profile/tooling foundations. HL2 Linux has recorded real compilation and gameplay evidence. HL2 Windows profile/configuration exists, without equivalent Windows/Proton execution certification.

**Remaining:** Honest per-engine capability matrices and representative regression maps; complete structured engine dictionaries and provenance; public adapter/entity APIs and documentation; Source 2 including lighting controls; Unity, Unreal and Godot 4 integrations using their actual workflows.

**Original exit gate:** Each supported engine has an honest capability matrix and representative real-engine tests.

### 7. Complete world-content workflows

**Packages:** WP-067, WP-070, WP-074, WP-075, WP-076, WP-017.  
**Status:** Partial asset plumbing; complete workflows pending.

**Already present:** WAD/VPK access, sky/decal material categories, sound proxies and example map fixtures.

**Remaining:** Full sky/environment authoring, projected decals/detail placement, soundscape authoring, user-facing archive inspection, curated starter templates and removal of obsolete gallery code. Finding a sky or decal material does not complete its authoring workflow.

**Original exit gate:** Common world-content workflows are available through native Blender interfaces.

### 8. Develop Pro systems

**Packages:** WP-040–WP-046, WP-068, WP-069.  
**Status:** Infrastructure ready; advanced product features pending.

**Already present:** Independently installable private Pro source tree, shared baseline/version tracking, safe synchronization and matching releases.

**Remaining:** Procedural framework, roads, intersections, terrain-aware roads, tunnels/bridges/rails/pipes and architecture; specialized Geometry Nodes/modifier integration; scattering; spline prop placement. The Pro repository alone does not mean these features exist.

**Original exit gate:** Pro systems are deterministic, editable, validated, and genuinely additive to free.

### 9. Installation, polish, and release

**Packages:** WP-004, WP-011, WP-049, WP-050, WP-051–WP-055, WP-057–WP-063, WP-078.  
**Status:** Installer/release milestone delivered early; overall stable release gate remains open.

**Already present:** Complete source-tree installer downloads, pinned private Python runtime, unknown-build/force modes, strict native requirement, replacement, independent instances, uninstall/repair/recovery, diagnostic output, test/build/release automation and matching Free/Pro releases.

**Remaining:** Broader platform and actual-native compatibility validation; continuing source reorganization and context-sensitive UI polish; complete edition/workflow acceptance; dependency/licensing review coverage; engine and Wall Worm parity tracking. No certified renderer builds are established by synthetic installer tests.

**Current validation:** 129 tests passed with both system and bundled Python for v0.12.0; two deliberate lifecycle mutations were detected. The new native lifecycle checks used synthetic ELF fixtures with mocked startup probes. Separate earlier Blender/HL2 tests provide only the narrower evidence described above.

**Restoration boundary:** An intact original backup allows byte-exact restoration. Structural removal of an adopted patch restores original shader behavior but may differ in formatting. Changed/unknown runtimes and user backups are retained and reported.

**Original exit gate:** Both products install independently, core workflows pass end-to-end tests, and repository boundaries are verified. Installer success alone does not satisfy all core workflows.

## Added interaction roadmap: WP-092–WP-101

These are additional cross-cutting requirements from the end of `init.txt`, not a tenth original milestone.

| Package | Current position | Remaining requirement |
| --- | --- | --- |
| WP-092 Universal direct-manipulation framework | Separate move/creation/resize tools exist | Shared extensible interaction interface across geometry, entities and procedural content |
| WP-093 Context-sensitive tool discovery | Shift+A entries, panels and operators exist | Consistent contextual menus, tool discovery and relevant controls across object types |
| WP-094 Unified precision editing | Engine-unit Object Mode movement and numeric entry exist | Consistent snapping, constraints and precision across all editing tools |
| WP-095 Universal non-destructive editing and live regeneration | Primitive parameters can regenerate geometry | General live regeneration, dependency updates and parameter preservation |
| WP-096 Universal viewport handles | Move and resize gizmos exist | Shared handle system for all supported authored content |
| WP-097 Unified editing shortcuts and modal operations | Modal creation/movement tools exist | Consistent shortcuts, cancel/confirm and undo behavior throughout the product |
| WP-098 Advanced BSP editing integration | Basic brush editing/export exists | Direct face/edge/vertex manipulation, clipping, texture lock and invalid-brush prevention through the shared framework |
| WP-099 Procedural editing interaction adapters | Pending | Viewport interaction adapters for the Pro generators |
| WP-100 Unified diagnostics and visual feedback | Validation and compiler diagnostics exist | Linked viewport highlights and actionable diagnostics across subsystems |
| WP-101 Workflow consistency and usability validation | Individual regression tests exist | Representative cross-tool usability, latency, discoverability and undo acceptance |

## Recommended continuation, without changing the original roadmap

1. Close foundation/asset gaps that would block prop production: model representation, dependency tracking and clear engine capability reporting.
2. Deliver one complete Source 1 static-prop workflow for Milestone 3: model → collision/materials → compile → register → place → edit → rebuild.
3. Extend Milestone 4 with BSP-aware CSG and direct face editing, using the interaction framework instead of more isolated tools.
4. Complete Milestone 5 round-trip and gameplay workflows, with real-engine acceptance maps.
5. Expand engines and world-content tools before claiming full integrations; then deliver the genuinely additional Pro systems.
6. Keep installer safety, regression tests and publication work continuous rather than postponing them until the end.

## Complete package index

**Delivered baseline** means a concrete implementation is shipped, not that every future/platform acceptance condition is closed. **Partial** means supporting functionality exists but the package's complete scope is open. **Pending** means completion is not established by this implementation review; it does not assert that no exploratory code exists.

| Package | Original title | Position |
| --- | --- | --- |
| WP-001 | Complete repository audit | Delivered baseline |
| WP-002 | Establish wavelength pro repository | Delivered baseline |
| WP-003 | Shared-code synchronization | Delivered baseline |
| WP-004 | Source-tree reorganization | Partial |
| WP-005 | Dedicated wavelength workspace | Delivered baseline |
| WP-006 | Workspace-scoped activation | Delivered baseline |
| WP-007 | Toggleable customization | Delivered baseline |
| WP-008 | Restore entity browser | Partial |
| WP-009 | Correct map-unit grid | Delivered baseline |
| WP-010 | Stabilize snapping | Partial |
| WP-011 | Improve viewport colors | Partial |
| WP-012 | Audit legacy gallery | Delivered baseline |
| WP-013 | Native Asset Browser foundation | Delivered baseline |
| WP-014 | Material and texture assets | Partial |
| WP-015 | Model assets | Partial |
| WP-016 | Entity assets | Partial |
| WP-017 | Remove obsolete gallery | Partial |
| WP-018 | Profile naming | Delivered baseline |
| WP-019 | Persistent custom profiles | Delivered baseline |
| WP-020 | Central entity registry | Partial |
| WP-021 | Structured engine data | Partial |
| WP-022 | Documentation ingestion | Pending |
| WP-023 | Engine adapter SDK | Pending |
| WP-024 | Custom entity API | Pending |
| WP-025 | Modern engine entity bridges | Pending |
| WP-026 | SDK documentation | Pending |
| WP-027 | Canonical geometry | Partial |
| WP-028 | BSP-aware CSG | Pending |
| WP-029 | Parametric arches | Delivered baseline |
| WP-030 | Parametric spheres | Delivered baseline |
| WP-031 | Parametric stairs | Delivered baseline |
| WP-032 | Quake/id Tech | Partial |
| WP-033 | GoldSrc | Partial |
| WP-034 | Source 1 VMF repair | Partial |
| WP-035 | Source 2 integration | Pending |
| WP-036 | Source 2 lighting UI | Pending |
| WP-037 | Unity | Pending |
| WP-038 | Unreal | Pending |
| WP-039 | Godot 4 | Pending |
| WP-040 | Procedural framework | Pending |
| WP-041 | Spline roads | Pending |
| WP-042 | Road intersections | Pending |
| WP-043 | Terrain-aware roads | Pending |
| WP-044 | Advanced structures | Pending |
| WP-045 | Geometry Nodes interoperability | Pending |
| WP-046 | Modifier interoperability | Pending |
| WP-047 | Thirdparty consolidation | Partial |
| WP-048 | Toolchain validation | Partial |
| WP-049 | Installer parity | Delivered baseline |
| WP-050 | Experimental unverified installation | Delivered baseline |
| WP-051 | Menu reorganization | Partial |
| WP-052 | Context-aware UI | Partial |
| WP-053 | Inspector improvements | Partial |
| WP-054 | Edition capabilities | Partial |
| WP-055 | Cross-edition compatibility | Partial |
| WP-056 | Automated tests | Partial |
| WP-057 | Real-engine validation | Partial |
| WP-058 | Documentation | Partial |
| WP-059 | Publication | Delivered baseline |
| WP-060 | End-to-end acceptance | Partial |
| WP-061 | Wall Worm research | Pending |
| WP-062 | Edition policy | Partial |
| WP-063 | Additional Pro opportunities | Pending |
| WP-064 | Displacement terrain | Pending |
| WP-065 | Complete model production | Pending |
| WP-066 | Visgroups | Partial |
| WP-067 | Sky authoring | Pending |
| WP-068 | Procedural scattering | Pending |
| WP-069 | Spline prop placement | Pending |
| WP-070 | Decals and detailing | Partial |
| WP-071 | Expanded Asset Browser | Partial |
| WP-072 | Bidirectional map import | Partial |
| WP-073 | Instances and compile regions | Partial |
| WP-074 | Soundscapes | Partial |
| WP-075 | Archive inspection | Partial |
| WP-076 | Starter templates | Partial |
| WP-077 | Asset compilation | Pending |
| WP-078 | Wall Worm parity tracking | Pending |
| WP-079 | End-to-end Blender-native game asset authoring | Pending |
| WP-080 | Level-design-aware mesh editing | Pending |
| WP-081 | Hotspot materials | Pending |
| WP-082 | Face-based modular tilesets | Pending |
| WP-083 | Smart procedural prefabs | Pending |
| WP-084 | Physics-assisted placement | Pending |
| WP-085 | Integrated lighting and environment workflow | Partial |
| WP-086 | Visual entity I/O | Partial |
| WP-087 | Gameplay paths | Partial |
| WP-088 | Visibility and optimization tools | Partial |
| WP-089 | Incremental and staged compilation | Partial |
| WP-090 | Navigation authoring | Pending |
| WP-091 | Cables, layers, selection sets, and cameras | Partial |
| WP-092 | Universal direct-manipulation framework | Partial |
| WP-093 | Context-sensitive tool discovery | Partial |
| WP-094 | Unified precision editing | Partial |
| WP-095 | Universal non-destructive editing and live regeneration | Partial |
| WP-096 | Universal viewport handles | Partial |
| WP-097 | Unified editing shortcuts and modal operations | Partial |
| WP-098 | Advanced BSP editing integration | Partial |
| WP-099 | Procedural editing interaction adapters | Pending |
| WP-100 | Unified diagnostics and visual feedback | Partial |
| WP-101 | Workflow consistency and usability validation | Partial |

## Evidence and historical reading order

- [Current state](CURRENT-STATE.md): read newest release sections first; older audit text is historical.
- [Foundation/assets/primitives milestone](MILESTONES-1-2.md): implementation scope and explicit limits.
- [Installer instructions](INSTALLER.md): current lifecycle behavior.
- [Release notes](RELEASE-NOTES.md): chronology; earlier limitations may be superseded.
- [Source 1 notes](SOURCE1.md): format/tooling details; the later v0.11.3 gameplay result supersedes its older runtime-status paragraph.
- Source modules under `addon/wavelength/source/`: workspace, grid, precision movement, assets, profiles, primitives, entities, geometry and build pipeline.
- `installer/wavelength_installer/`: current lifecycle, native preparation, structural patching, repair and instance management.

No new engine or native compatibility claim is made by this document.
