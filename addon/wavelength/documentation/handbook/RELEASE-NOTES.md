# v0.50.0-pre.alpha — CS2 map and material IO

Published Windows update, including the accumulated authoring milestones since
v0.19.1: Geometry Nodes generation, pencil clipping, terrain tooling, entity/model
workflows, profile/context state, visual geometry diagnostics, CSG and the handbook.
Individual development milestones and remaining limitations are recorded below.

- Import editable text/binary VMAP polygon meshes; export Source 2 editable maps with half-edge topology, per-face materials and UVs.
- Reference original CS2 VMATs and decode the installed game's compiled material/texture assets through the external Source 2 Viewer CLI.
- Build thumbnail libraries in a background worker, with bounded shards and persistent decoded-material caches.
- File-menu IO opens the native file browser with a format selector; the CS2 profile defaults to VMAP rather than model assets.
- Validate against a shipped binary VMAP, Valve DMX conversion and a successful CS2 map compile/VPK pack. No entity, prefab/model-instance or playable-map workflow is claimed.

# v0.49.0-pre.alpha — inherited profile registry (local, unreleased)

- Protected shipped templates are JSON definitions with engine/game inheritance; GMod inherits Source rather than HL2.
- Register, derive, rename, reparent and remove user profiles. UUID-backed registrations store overrides, preserve legacy snapshots, and export portable parent bundles.
- Reject cycles, missing parents, template replacement and removal of parents with dependent children. Failed loads restore prior settings.
- Scene Properties and the header popover expose the registry. Profile enums retain stable template numbers and user registration numbers.
- Add a generic Source Windows parent for VMF export only; it does not claim an unsupported game compile pipeline.

# v0.48.0-pre.alpha — Godot 4 and CS2 mesh/texture exports (local, unreleased)

- Add mesh-only Godot 4 and Counter-Strike 2 / Source 2 profiles with no BSP convexity requirement or entity pipeline.
- Export evaluated geometry and UV-mapped textures to Godot GLB, or CS2 FBX + VMAT + PNG + ModelDoc source bundles.
- Temporary-scene exports preserve original meshes, generators, materials and selection; helpers and entity representations are excluded.
- Header, File Export and sidebar expose Export Meshes & Textures; BSP Build/Play is hidden for these profiles.
- Godot imported the test GLB with expected pixels, UVs, meter bounds and axes. CS2 compiled a generated model/material with expected Source-unit bounds and material reference.
- CS2 material conversion currently includes base color and scalar roughness. Entities, collision, animation, VMAP writing, game-resource indexing and automated game deployment are not implemented.

# v0.47.2-pre.alpha — discoverable geometry finalization (local, unreleased)

- Add Finalize Geometry to Object and object context menus so normal F3 menu search can find it.
- Show Finalize Active Brush in the CSG sidebar before starting a Boolean on procedural geometry.
- Verified real F3 typing and execution with developer search disabled.

# v0.47.1-pre.alpha — CSG brush assembly selection (local, unreleased)

- Resolve a finalized single-mesh brush assembly to its mesh and deduplicate wrapper/child selection for CSG.
- Pending procedural assemblies report Finalize Geometry explicitly instead of a misleading selection-count error.
- CSG finalization can be invoked while the single-mesh target assembly wrapper is active.

# v0.47.0-pre.alpha — editable CSG and convex BSP conversion (local, unreleased)

- CSG sidebar provides live Geometry Nodes Subtract, Union and Intersect with editable cutters, cancellation and explicit finalization.
- BSP profiles partition Boolean outputs into validated convex brush objects with distinct IDs, material inheritance and projected engine UVs. Mesh profiles retain one evaluated mesh.
- Pencil solid cuts reuse the same converter. Resource limits and volume checks preserve the preview if conversion fails.
- Live CSG blocks profile changes and map export until finalized or cancelled. Construction cutters remain excluded after commit.
- Initial limitations: partitions are not minimized; BSP conversion resets per-face projection offsets; detailed assets can exceed conversion limits.

# v0.46.0-pre.alpha — visual geometry diagnostics (local, unreleased)

- Geometry Problems in the viewport sidebar locates invalid BSP brush vertices, edges and faces, with markers, labels and repair hints.
- Structured export failures populate the viewport diagnostics automatically. Validate/Map Problems can scan all brushes.
- Select Geometry and Frame use native Edit Mode selection. Evaluated node meshes are marked safely without applying their indices to base meshes.
- Existing problem objects refresh after edits; fixed errors clear automatically. No destructive repair is automatic.

# v0.45.2-pre.alpha — shared profile snap mapping (local, unreleased)

- Map Snapping and the native magnet/Shift+Tab share one snap state. Disabling snap no longer switches away from the wavelength transform backend.
- Native Edit Mode grid movement and Shift+S grid commands use active profile spacing and restore native behavior outside wavelength.
- Native Selection to Grid preserves procedural assemblies through the existing wavelength operation. Boundary resize respects the same snap state.
- Grid policy is exposed through a shared context gate and derived profile-spacing RNA; native snap-target preferences remain unchanged.

# v0.45.1-pre.alpha — transform axis guides (local, unreleased)

- Move, Rotate and Scale draw theme-colored X/Y/Z constraint guides through their pivot, including gizmo-initiated transforms.
- Guides clean up on confirmation, cancellation and add-on shutdown and are scoped to the originating viewport/context.
- Verified all nine keyboard transform/axis combinations and rendered screenshots.

# v0.45.0-pre.alpha — unified transform interface (local, unreleased)

- Native Move/Rotate/Scale/Transform buttons use wavelength controllers in the engine-grid Object Mode context; duplicate engine buttons are removed.
- G/R/S route to the existing undoable backends. A Windows native event filter excludes competing native bindings per context without changing keymaps or saved preferences.
- Workspace/context transitions refresh tool runtime bindings; ordinary Blender contexts retain native transforms. Unregister restores native bindings, including inactive workspaces.
- Drawing and brush tools remain in the wavelength column.

# v0.44.1-pre.alpha — profile-aware drawing planes (local, unreleased)

- Profile-grid empty-space placement chooses a stable world-origin plane from the view rather than each perspective mouse ray.
- Pencil strokes keep their starting surface/grid depth; coplanar vertex and edge snaps remain available.
- Profile-grid snapping uses the engine grid origin, avoiding off-grid offsets from relative increments. Blender snap toggles remain effective.
- Metric/free profiles retain existing placement. Grid capability is independent of BSP brush semantics.

# v0.43.8-pre.alpha — live projection during native vertex edits (local, unreleased)

- Native Edit Mode vertex changes now update brush preview UVs directly through BMesh. The previous timer skipped Edit Mode entirely.
- Stored projection axes/scales, face metadata and selection remain intact. Temporary non-planar faces can still preview during editing. Disable/reenable is observed without requiring another geometry change.
- UV values are excluded from input signatures and unchanged mappings are not rewritten, preventing timer feedback loops.

# v0.43.7-pre.alpha — separate solid pieces and textured caps (local, unreleased)

- Keep Both creates two separately selectable capped objects by default. A Separate Objects toggle in the tool header and guide properties retains the optional combined-mesh output.
- New objects inherit the target's transform, collections and object settings; brush IDs are unique. Closed Faces-mode extrusion still creates a single mesh.
- Boolean caps inherit an actually used material and projected UVs. Single-texture targets reuse it; multi-texture targets randomly choose one used material for the cut, ignoring empty/unused slots. Existing surface assignments remain intact.
- Verified live Enter splitting, combined output, capped material/UV inheritance, single-side clipping, brush texture export and unique brush IDs.

# v0.43.6-pre.alpha — interactive clipping side controls (local, unreleased)

- Keep Both/Outside/Inside remains available in the cutter header menu. B cycles it while drawing or extruding depth; Shift+wheel cycles forward/backward without changing depth. These controls select Split Solid.
- The drawing header displays Keep mode. New paths use the settings shown in the tool header, including when a prior guide exists and its target mesh is selected.

# v0.43.5-pre.alpha — solid-cut confirmation and result clarity (local, unreleased)

- Enter now applies Split/Subtract while drawing; Shift+Enter retains an open guide without cutting. Faces mode keeps its guide-first Enter behavior. K and Enter also apply a finished guide with the pencil tool active.
- The drawing header shows Keep mode, and solid results explicitly report whether both capped components were retained or one side was removed.
- Verified Enter with finite-depth Keep Both produces two disconnected manifold volumes in one mesh, while Keep Outside removes the expected volume. The unchanged silhouette under Keep Both is intentional.

# v0.43.4-pre.alpha — independent Edit Mode texture drops (local, unreleased)

- Texture dragging has its own Asset Browser handler, independent of Click Place, avoiding Blender's Object Mode-only material drop.
- Auto/Surface drops in Edit Mode paint the selected faces across edited meshes. With no faces selected, the hit face is painted. Direct click painting still targets the hit face.
- Shift/Ctrl/Alt viewport clicks pass through for native selection/navigation. Explicit Object scope remains available.
- Verified a live native drag with Click Place stopped and two selected faces, selected-face metadata/UV preservation, undo and entity placement.

# v0.43.3-pre.alpha — cutter audit and modifier safeguard (local, unreleased)

- Verified face projection, capped through-all and finite-depth clipping, subtraction, curves, XYZ directions, keep sides, linked mesh isolation and undo in Blender.
- Added live event tests for Z/D/wheel/K clipping and closed-outline depth extrusion, plus transformed/profile depth checks for Blender, HL2 and HL1.
- Reject live viewport modifiers before cutting instead of silently cutting the underlying base mesh. Finalize procedural geometry or apply modifiers first.

# v0.43.2-pre.alpha — placement lifecycle repair (local, unreleased)

- Placement state and draw callbacks now belong to a plain Python session rather than a temporary Blender operator.
- Undo, redo, file loading and cancellation clean up timers, cursors and the active session. Removed operators are detected before toggling or automatically starting placement.
- Verified live undo while placement is active, followed by automatic entity placement without stale RNA errors.

# v0.43.1-pre.alpha — automatic placement and mode-aware texture drops (local, unreleased)

- Selecting a texture or point entity automatically arms Click Place. Esc/Stop dismisses that item until another is chosen or Click Place is enabled manually.
- Auto scope follows Blender mode: Object Mode paints the object, Edit Mode paints the hit face. Surface and Object remain explicit overrides.
- Browser texture drags use the same face-safe assignment path as clicks. Edit Mode no longer runs the legacy polygon-material synchronization handler.
- Verified live texture dragging in Edit Mode, automatic Object Mode scope, automatic entity placement, undo and context cleanup.

# v0.43.0-pre.alpha — click-to-paint and point-entity placement (local, unreleased)

- Added Click Place in the native browser header and panel. Choose a texture/entity and click repeatedly in the level; Surface paints only the clicked face in either mesh mode, Object paints the whole clicked mesh/locked brush assembly.
- Paint preserves other face materials, UVs and face selection. It changes material indices rather than replacing shared slots. Entity placement uses the hit point and Blender grid-snap controls without moving the 3D cursor.
- Added a 3D placement cursor, individual click undo steps, browser item changes while armed, and scene/profile/workspace-context cancellation.
- Use Asset and placement accept a single selected tile when Blender has no active asset. Auto model-browser switching stays paused during click placement.
- Verified live native browser texture selection and viewport clicks, per-click undo, entity placement and context cleanup; 188 regression tests pass. See [Surface tools](SURFACE-TOOLS.md).

# v0.42.0-pre.alpha — packaged SVG entity references and preview recovery (local, unreleased)

- The full HL2 audit rendered every indexed standalone model; six stale stock entity model paths now resolve against installed assets. Three legacy FGD entries still reference unavailable game models and remain explicit preview errors.
- Recovered the existing 30-icon SVG pack from the older checkout and packaged it at environment/sprites, with HL1 and compatible Source helper mappings.
- Abstract entities use the same SVG artwork for in-world helper curves and cached native Asset Browser thumbnails. Explicit models and actual physical model representations take precedence.
- Source animation-only MDLs are filtered by the worker. Source thumbnail texture decoding is bounded to 128px; normal editor materials retain full quality. Entity previews are prepared first.
- Preview assignment validates asset identity to avoid stale object-name reuse, and individual preview errors are exposed in the browser panel.
- Verified HL1/HL2 SVG helpers and native browser previews, model/SVG cache reuse, and the complete HL1 cache (256 jobs, zero errors).

# v0.41.2-pre.alpha — profile-aware nodraw textures (local, unreleased)

- GoldSrc texture sources now include SDHLT/ZHLT tool WADs beside the configured compilers. NULL is displayed as NULL (nodraw), and nodraw search/assignment resolves to the GoldSrc compiler texture.
- Source nodraw aliases resolve to tools/toolsnodraw. Verified actual HL2 preview decoding, shader realization and assignment.
- Compiler directory changes invalidate GoldSrc texture catalogs; texture workers also retry transient Windows manifest locks.
- Verified HL1 preview/assignment/export WAD and a compiled room whose rendered BSP faces contain no NULL surfaces; 188 regression tests pass.

# v0.41.1-pre.alpha — HL1 entity representations and thumbnail recovery (local, unreleased)

- Player start, coop, deathmatch and teleport markers now use the installed HL1 player model as an editor helper; spawn markers remain excluded from clean renders and export no model override.
- Expanded stock entity model aliases. Texture-only and sequence-group MDL companions are filtered from GoldSrc model choices; blank-default gib models use a visible bodygroup for library previews.
- Thumbnail manifest writes retry transient Windows file locks with unique temporary files.
- Rebuilt the local HL1 cache: 227 jobs complete, zero errors. Verified player marker geometry, Source/HL1 worker cache reuse and 188 regression tests.

# v0.41.0-pre.alpha — face textures and asset picker (local, unreleased)

- Asset Browser material assignment now uses persistent per-face mapping in Edit Mode; Object Mode applies to selected meshes/brush assemblies. Material changes retain mapping.
- Added a shared viewport texture/entity-class eyedropper and held asset action in the browser header and left panel.
- Restored Texture Settings directly in the browser: shift, signed scale, rotation, flip, copy/paste, fit, center, edge justification, Valve world/face alignment and Source lightmap scale.
- Verified real browser-to-viewport assignment and eyedropper clicks, metadata, fit, flip and held entity placement. See [Surface tools](SURFACE-TOOLS.md).

# v0.40.1-pre.alpha — Windows Half-Life profile (local, unreleased)

- Added Half-Life — GoldSrc — Windows: Steam App ID 70, Valve 220/BSP30, stock WAD discovery, SDK Half-Life FGD and native SDHLT compiler discovery.
- Steam library folders and registry paths are supported; validated compiler locations are remembered locally. WAVELENGTH_GOLDSRC_TOOLS can override compiler discovery.
- Verified installed HL1 entity geometry, texture lookup, profile switching and an exported sealed room compiled through all four Windows SDHLT stages.

# v0.40.0-pre.alpha — context state machine (local, unreleased)

- Scene-wide Level Editing, Clean Preview and Suspended contexts with separate tool, overlay, preparation and helper controls.
- Clean render helper exclusion works from every workspace, preserves game models/lights and restores previous visibility on completion or cancellation.
- Per-object visibility role overrides, saved scene state, per-view-layer restoration and preparation worker suspension.
- Verified actual Blender renders, two view layers, save/reload and setup worker lifecycle; 187 unit tests pass. See [Context guide](CONTEXT.md).

# v0.39.0-pre.alpha — profile setup and rendered asset previews (local, unreleased)

- Add automatic configured-profile setup for Source 1 and GoldSrc: indexing, preparation, progress, ready/error states and explicit start/resume/pause/cancel/refresh controls in Scene Properties.
- Render actual textured model/entity thumbnails in one hidden external Blender worker. Import cached pixels into the native asset previews in bounded updates, preserving metadata-only browser tiles and prioritizing searched assets.
- Cache by installation/profile and model variant, track model/material/texture dependencies, reuse unchanged previews and monitor content changes. Pause workers on workspace/profile changes and terminate them when their parent closes.
- Expose GoldSrc's installed Models catalog and model-property assignment. Preserve explicit manual Models browsing without an active target.
- Verify Source/HL1 rendering, shared entity/model records, persistent cache reuse, targeted material invalidation, native browser display, automatic startup/suspension, controls and existing Source/GoldSrc model workflows. See PROFILE-SETUP.md.

# v0.38.0-pre.alpha — direct HL1 entity models (local, unreleased)

- Read installed GoldSrc MDL v10 geometry, palette textures, normals, skins/bodygroups and posed bones directly. Support separate texture/sequence companions, loose files and PAKs, mod precedence and base-game fallback.
- Resolve explicit model properties, FGD studio declarations and stock entity world-model mappings. Create shared, textured viewport meshes at profile scale; exclude them from brush export and preserve entity properties.
- Support deferred browser placement, missing-reference recovery and migration from old glTF representations. Cache decoded data with dependency checks and retain textures/geometry through save/reload.
- Verify installed HL1 scientist, grunt, headcrab, crowbar and healthkit, idle/sequence poses, external companions, shared data, scale, migration and browser drops. The unit suite passes 184 tests. See GOLDSRC-MODELS.md for supported behavior and remaining limits.

# v0.37.0-pre.alpha — Source entity world representations (local, unreleased)

- Read literal studio/studioprop model declarations from the active game's FGD, with inheritance and explicit entity-model precedence. Display actual world geometry for entities such as weapon_crowbar, weapon_pistol and item_healthkit even when they expose no editable model field.
- Keep entity class/properties unchanged and exclude the visual child from brush export. Share mesh/material data across repeated placements and promote preview selection to its owning entity.
- Support direct creation and deferred entity-browser placement; recover missing representations progressively when opening saved scenes in wavelength. Validate actual installed HL2 meshes, dropped crowbars, missing-reference recovery and 181 unit tests.
- General game-code-only model resolution, GoldSrc direct decoding and the profile setup/cache lifecycle remain separate work.

# v0.36.6-pre.alpha — deleted model sources (local, unreleased)

- Exclude model source objects removed from the current scene, even when retained as Blender datablocks by the internal definition collection. Stop deleted high-detail meshes and their materials from remaining in subsequent model builds; invalidate caches from the surviving source data.
- Report a removed explicit collision source clearly. Preserve Blender's original mesh data and undo references without automatic decimation or model splitting.
- Reproduce native scene deletion and compile only the surviving geometry with StudioMDL; verify a separate rebuild of the user's actual map with its low-detail Suzanne.

# v0.36.5-pre.alpha — Source-compatible BSP asset storage (local, unreleased)

- Write BSP pakfile entries without ZIP Deflate, which the Source asset reader does not decode. Fix models loading as ERROR despite passing generic ZIP checks, and keep existing embedded assets intact while repacking.
- Verify the actual user's repaired BSP with Valve BSPZIP: extracted model, collision, material and texture bytes match the original assets exactly. Add regression checks for stored entries and repairing old Deflate packages.

# v0.36.4-pre.alpha — model-door export corrections (local, unreleased)

- Parse omitted FGD defaults as empty fields instead of literal colons. Remove old invalid colon defaults from empty entity-reference/model/sound fields during Source export, preserving custom fields and authored nonempty values.
- Generate required convex collision for custom prop_door_rotating models, including existing assignments without collision. Compile minimal door sound/surface metadata and verify all requested collision files before packaging.
- Rebuild a separate copy of the user's saved scene through StudioMDL/VBSP/VVIS/VRAD; verify the door remains in the BSP, invalid names/parents are removed, and model/PHY/door options are packed. Runtime visibility still requires an in-game check. The full unit suite passes 179 tests.

# v0.36.3-pre.alpha — brush versus model entities (local, unreleased)

- Identify brush entities such as func_door_rotating explicitly when custom-model assignment is attempted. Explain the BSP brush workflow in the error and panel instead of reporting a missing studio property.

# v0.36.2-pre.alpha — custom-model selection handling (local, unreleased)

- Resolve the single selected target entity regardless of selection order, including selection through its model preview. Exclude preview geometry from editable model sources and activate the entity after assignment. Report absent or ambiguous targets explicitly.

# v0.36.1-pre.alpha — discoverable custom-model assignment (local, unreleased)

- Add Assign Selected Model to Entity to the viewport Object menu so Blender's menu-filtered F3 search can discover it. Add a matching button directly to model-capable entities' Object Properties.

# v0.36.0-pre.alpha — editable custom Source models (local, unreleased)

- Assign editable Blender meshes and an optional armature to a Source entity. Preserve source transforms, animation and UVs; save ownership in the .blend file, exclude sources from brush export, and support detaching with native undo.
- Compile changed model dependencies with the active game's StudioMDL before map compilation. Generate reference/animation SMD, QC, basic VertexLitGeneric materials and VTF textures, plus optional convex physics collision and game-validated prop data.
- Stage compiler inputs against game mounts, cache unchanged dependencies, then embed owned files in the BSP or publish to a mounted game directory after a successful map build. Preserve the normal Blender export workflow.
- Verify real HL2 static, rigid animated, skeletal and physics compilation, full map compilation with embedded assets, deferred game-directory publication, save/reload, UVs, native assignment/undo and 178 unit tests. See CUSTOM-MODELS.md for supported materials and current limits.

# v0.35.0-pre.alpha — model assignment after file load (local, unreleased)

- Keep the entity asset-drop handler persistent across opening .blend files. Recover visible scene placements left with excluded browser-template metadata, preserving authored properties, name, identity and transform while leaving actual browser templates alone.
- Pause model catalog publication while a model tile is selected and avoid idle redraw churn. Verify model assignment to a recovered prop_static, drops after file load, and native browser assignment.

# v0.34.0-pre.alpha — entity selection and browser placement (local, unreleased)

- Make Source model preview meshes selectable and promote selection to the owning engine entity. Resolve entity properties through its preview mesh and migrate old saved references on load.
- Finalize dropped entity assets even when they retain a source-collection link; keep the browser template separate, clear asset status on the placed entity, and activate it before opening contextual model choices.
- Run the model watcher in explicit wavelength window contexts and restore it after file loads. Verify automatic selection without manually triggering the watcher, model-mesh selection, browser placement and saved model references.

# v0.33.0-pre.alpha — entity model browser and game entity definitions (local, unreleased)

- Selecting a model-capable Source entity opens the native Models asset catalog. Assign or drop a model onto that existing entity, retaining class and transform and replacing its visual reference. Handle inherited studio/*studio fields, physics/ragdoll/vehicle entities and secondary model properties.
- Publish lightweight model choices in bounded batches; load geometry/materials only on assignment. Keep Models, Entities and Textures catalogs separate, prioritize filtered model searches and restore the previous section for non-model entities.
- Replace the shared Source starter list with each installed game's complete concrete Hammer catalog and inherited defaults: 461 HL2 classes and 487 GMod classes in the tested installations. Honor explicit mod FGDs, cache included definitions, exclude base classes and avoid cross-game class unions.
- Fix FGD editor directives, legacy encoding, concrete NPC/filter/movement class recognition, inherited flag defaults and input/output separation from properties. Validate contextual native browser use, model drops, secondary fields, game isolation and 174 unit tests.

# v0.32.0-pre.alpha — Source model geometry import (local, unreleased)

- Add a native searchable Add Source Model menu reading the active profile's loose folders and VPKs. Place actual reference-pose geometry and textures instead of bounds proxies; export original engine prop references.
- Read standard MDL 44–49, VVD 4 fixups and VTX 7 triangle lists/strips, validate checksums and bounds, resolve skin/body selections, preserve UVs/custom normals and share repeated preview meshes.
- Add File Import for loose MDL files with matching companions. Refresh Source entity previews when model/skin/body properties change. Choose static/dynamic prop class from model flags.
- Validate HL2 crate/barrel/chair/character imports, GMod player geometry, material lookup, save/reload, map export, malformed companions and the native model chooser. Animation, collision and model compilation remain separate work.

# v0.31.0-pre.alpha — terrain front-face direction (local, unreleased)

- New brush-derived terrain inherits the convex brush's outward facing, including brushes whose raw mesh normals are reversed or mirrored.
- Add Flip Terrain Facing in terrain properties and F3 for selected existing surfaces. Reverse Geometry Nodes winding and Source sample axes together, preserving sculpted positions, painted blend weights and sewn joins.
- Verify front directions in actual HL2 BSPs, including a separate corrected copy of the reported cave. The original saved map remains unchanged.

# v0.30.0-pre.alpha — independent face terrain and Source seam orientation (local, unreleased)

- Convert selected quad faces into independent paintable surfaces and remove their backing brush automatically. Preserve world placement, material, base-domain data and sewn links; undo restores the brush.
- Recover orphaned legacy surfaces from saved base corners. Add Detach Displacements for existing brush-linked surfaces.
- Export every brush-derived displacement from its own surface frame, including legacy attachments. Fix transposed deformation when raw mesh winding disagrees with Source's outward brush planes.
- Verify actual compiled BSP vertices and reciprocal engine neighbour links, with an inward-winding regression fixture and a diagnostic copy of the reported HL2 map. Validate multi-face extraction, native undo, painting and save/reload.

# v0.29.0-pre.alpha — sewn displacement networks (local, unreleased)

- Sew matching full edges across separate terrain and brush-face objects, retaining original ownership and solids. Support floor/wall/ceiling networks and mixed Source powers/display resolutions.
- Add inspectable Geometry Nodes vector deformation, persistent neighbour links and exact boundary targets. Paint across connected surfaces with shared-edge constraints, optional seam relaxation and multi-object undo.
- Export vector-deformed surfaces through their UV domain and validate connected boundaries once per network. Preserve links through save/reload and finalization; Unsew retains deformation.
- Validate real mouse painting/undo, reconstructed mixed-power VMF boundaries, differing noise/resolutions, original brush-face caves, general Blender terrain and Garry's Mod compilation. Partial-edge joins remain unsupported.

# v0.28.0-pre.alpha — flat terrain creation and visible painting (local, unreleased)

- Move Terrain into the native brush primitive hold menu, with two-click flat footprint placement and no height phase.
- Add explicit flat-plane to paintable-displacement conversion. New terrain starts without noise; existing terrain remains paintable. Source displacement sampling remains an export step.
- Scale initial flat-surface paint strength to footprint dimensions, migrate the old tiny default, and paint continuously while the mouse is held still.
- Enable Material Preview for texture painting and retain the paint-type hold menu as a contextual control.
- Verify real tool placement and held-mouse deformation on new terrain and existing cube faces, plus paint undo, materials, attachment reload and Source output.

# v0.27.2-pre.alpha — displacement finalization checks (local, unreleased)

- Use the generating assembly's state instead of copied mesh-part tags when checking displacement eligibility. Ordinary static cubes need no procedural finalization.
- Identify remaining modifiers separately, with their names, rather than reporting every blocker as an unfinalized brush.
- Verify static cubes, stale metadata, actual finalized stairs and rejection of live generators/unapplied modifiers.

# v0.27.1-pre.alpha — terrain paint hold menu (local, unreleased)

- Hold the toolbar or Properties paint button to choose Raise / Lower, Smooth or Texture Blend. Show the selected type's icon; click normally to reuse it.
- Verify mode selection, popup rendering, real mouse painting and native undo in Blender.

# v0.27.0-pre.alpha — Source brush-face displacements (local, unreleased)

- Create a paintable displacement from a selected quad of an existing finalized world brush, including vertical, sloped and tapered faces.
- Preserve the source solid and attach VMF displacement data to its original side; hide only the replaced viewport face with Geometry Nodes.
- Preserve attachment ownership, base plane and parent movement through saving and terrain finalization. Reject stale source geometry and duplicate attachments.
- Verify painting, multiple displaced sides, restoration on deletion, file reload, Blender UI and Garry's Mod VBSP compilation.

# v0.26.1-pre.alpha — generated Source terrain blends (local, unreleased)

- Choose two Source materials and generate an assigned WorldVertexTransition material for terrain painting.
- Preserve generated recipes in the blend, keep project/game VMT copies, and restore missing copies on export.
- Verify generated material staging, painted VMF export and Garry's Mod VBSP compilation.

# v0.26.0-pre.alpha — terrain placement, painting and material preview (local, unreleased)

- Add flat placement preview without changing full terrain export/finalization.
- Add non-destructive height raising/lowering, smoothing and texture-layer mask painting with a visible brush cursor and native undo.
- Add Source WorldVertexTransition shader preview and displacement alpha export. General Blender terrain supports a base/paint image-color layer preview.
- Fix terrain drag-and-drop/Apply Material synchronization and add the wavelength UV layer expected by game-material shaders.
- Validate real mouse strokes, undo, rendered material color, Source painted compilation and preserved patch seams.

# v0.25.0-pre.alpha — general terrain and Source output (local, unreleased)

- Add a general Geometry Nodes heightfield tool under Add > Mesh > Terrain, with live size, resolution, elevation, amplitude, frequency and seed controls.
- Source-owned terrain exports as sampled displacement patches, independently of the general mesh resolution; preserve shared boundary samples and profile ownership.
- Add evaluated finalization and frozen Source sampling settings. Reject unsupported terrain topology and preserve existing profile ownership on switching.
- Verify Blender UI, VMF output and actual Garry's Mod VBSP compilation. Heightmaps, control-surface sculpting, alpha painting and model compilation remain future work.

# v0.24.0-pre.alpha — straight stair Geometry Nodes adapter (local, unreleased)

- New straight stairs use a versioned, inspectable Geometry Nodes group and live modifier. Existing and curved stairs retain their previous generator.
- Generate connected meshes for Blender and identifiable convex parts for BSP profiles; support landings, units, direction, UVs and material input.
- Evaluate node output for validation and BSP export. Finalization bakes evaluated geometry and retains ownership.
- Preserve Python-generated definitions. Profile/workspace state prompts and contextual relationships remain separate future work.

# v0.22.0-pre.alpha — face and solid cutter (local, unreleased)

- Add Faces, Split Solid, and Subtract operations to the line/curve cutter. Keep guides editable and separate from cut results.
- Produce capped solid pieces with exact Boolean operations; support open/curved through splits and closed-outline subtraction with optional depth.
- Add screen-radius vertex/edge targeting, geometry priority over grid targets, occlusion filtering, and highlighted targets.
- Show a surface-oriented 3D placement cursor before and during drawing. Follow Blender snap settings, Ctrl inversion and profile grid spacing.
- Test manifoldness, volume conservation, curved splits, linked mesh isolation, UV retention, failure cleanup, face cuts, undo and native mouse gestures.

# v0.21.0-pre.alpha — line/curve cutter reset (local, unreleased)

- Replace the array/terrain pencil UI with an editable line/curve cutter in Object and Mesh Edit modes.
- Click creates corners, drag creates curve handles, Enter finishes open, and first-point click/C closes. Closing creates only a guide; scrolling navigates again.
- Keep drawing and native Curve Edit Mode adjustments non-destructive to the target mesh. Explicit actions are Apply Cut (K), Create Geometry and Keep Guide.
- Apply Cut uses Blender's native knife projection along the guide plane normal. Support open paths, curved paths, closed loops and optional cut-through. Retain the guide, restore the viewport and preserve UVs/materials.
- Isolate shared mesh data before cutting and roll back missed/failed projections. Undo restores the target while retaining the guide.
- Create Geometry makes a separate mesh as edges, a closed planar face or an explicit extrusion. It does not automatically change the target mesh or mark engine brushes.
- Remove parallel copies, array, scatter and displacement controls from this tool. Previously created scene objects are preserved.
- Validate actual mouse/key gestures, curved/open/closed knife projection, Edit Mode, UV/material preservation, linked-data isolation, rollback and normal restricted addon registration.

# v0.20.1-pre.alpha — restore normal addon startup (local, unreleased)

- Defer drawing-object discovery until Blender leaves its restricted addon-registration context. This fixes startup failure that prevented the wavelength workspace tab from appearing.
- Defer workspace-flag cleanup during addon disable. Test the pencil through addon_utils enable/disable, rather than direct register calls.

# v0.20.0-pre.alpha — pencil drawing, curves and parallel networks (local, unreleased)

- Add a pencil beside Create Brush. Click places corners, click-drag creates Bezier tangents, wheel changes the active segment's parallel-copy count, Enter finishes open, and first-point click/C closes and enters extrusion.
- Closing ignores arrays; reopening the editable guide restores saved segment counts. E extrudes an existing open/closed drawing; numeric heights, cancellation and native Curve Edit Mode are supported.
- Open drawings use real Array and Curve modifiers, with per-segment counts, profile-unit spacing, left/right/center spreading and connected equal-count corners. Surface output creates quad strips; Geometry Nodes can distribute a selected object across the surface.
- Live guide edits rebuild outputs after leaving Edit Mode. Rebuilds preserve material assignments and original guides; committed previews are cached and there is no idle rebuild polling.
- Source terrain creates power 2/3/4 displacement grids and exports them in VMF. Folded/invalid grids, unsupported profiles and missing materials are rejected. A sealed fixture compiled successfully with GMod's Windows VBSP. General displacement VMF import remains unsupported.
- Engine movement/rotation/scaling and pencil placement now obey Blender's snap toggle, transform snap options and targets. Ctrl inverts snapping. Rotation uses Blender's angle increments; grid spacing comes from the active engine profile. Non-grid transform snapping delegates to Blender.
- See DRAWING.md for controls and output editing.

# v0.19.2-pre.alpha — engine toolbar cleanup (local, unreleased)

- In the wavelength workspace, place a dedicated vertical engine tool column beside Blender's native viewport tools: Create Brush, Move, Rotate, Scale, Transform.
- Keep brush shapes in a hold-menu with Blender's green primitive icons; arch and stairs use the cube icon. Remember the last brush shape.
- Add world-axis rotation (15-degree drag increments) and dimension snapping for scale, numeric degrees/factors, Ctrl free adjustment, cancellation and undo. Combined Transform exposes move, rotate and scale handles.
- Confirm gizmo drags on release. Other workspaces retain the native toolbar layout.
- Extend the Windows native patch to reserve room for two full-size tool columns with a gutter in the wavelength workspace. Remove compact icon rasterization. Upgrade installer-owned native patches from their verified original backup, preserving rollback.

# v0.19.1-pre.alpha — Garry's Mod profile

- Add a dedicated Windows Garry's Mod Source profile with Steam App ID 4000.
- Discover GarrysMod/garrysmod, Garry's Mod's win64 VBSP/VVIS/VRAD tools and garrysmod.fgd without falling back to HL2 setup.
- Verified the installed game, all three compiler startup banners, 564 FGD definitions and 6,016 indexed materials. The private cache contains 5,516 supported previews and reports 500 unsupported materials.

# v0.19.0-pre.alpha — Windows authoring and interactive sun

Includes the following development milestones since v0.16.2: Blender-native UI,
external texture libraries, debounced search and material drops, Windows Steam
discovery, and interactive sun lighting. The native Windows patch is unchanged
and remains restricted to the exact Blender 5.2.3 candidate executable below.

- Add a real Blender Sun preview to light_environment entities, including existing entities and imported maps. Preserve the entity identity and hierarchy.
- Add viewport heading/elevation rings and a direction arrow, plus Object Properties controls for direction, color, preview strength and sun size.
- Synchronize native light edits and engine pitch/angles/_light fields in both directions; keep the loaded inspector fields current.
- Add Shift+A → Light → wavelength Sun and Preview Scene Lighting for Material Preview with scene lights/world.
- Export exactly one engine entity; exclude generated light previews. Restore on load/undo and remove orphan previews when the entity is deleted.
- Brightness uses an editor preview conversion (engine brightness / 100), not a reproduction of VRAD's baked lighting. Ambient/HDR compilation fields remain intact.
- Verified real-time viewport shadows, two-way direction/color/strength, export, deletion and reload; 152 unit tests pass.

# v0.18.2-pre.alpha — Windows Steam discovery (local, unreleased)

- Honor a configured Steam executable and locate Windows Steam through its registry/install folders, without requiring PATH edits.
- Preserve Steam App ID and map/game launch arguments. Verified both configured and registry discovery without starting Steam or the game.

# v0.18.1-pre.alpha — native search and material drops (local, unreleased)

- Debounce texture search by 250 ms in the wavelength native Asset Browser; other browsers keep their existing header behavior.
- Append editable preview materials rather than importing read-only packed placeholders. Repair linked placeholders when assigned.
- Realize dropped shaders on ordinary meshes, including unselected drop targets. Preserve existing UV coordinates and provide mapping for UV-less meshes.
- Synchronize face records and engine UVs on a brush's first material drop.
- Verify real dependency-graph updates, linked-material repair, displayed brick pixels in Material Preview, and 13 typed characters producing one native filter update.

# v0.18.0-pre.alpha — external texture libraries (local, unreleased)

- Build preview-only texture assets in a separate, low-priority Blender worker, saved in bounded external .blend shards.
- Browse cached assets in Blender's native external Asset Browser; importing/applying a texture creates only the selected material in the map.
- Cache the index and previews across sessions. Worker-side source fingerprints detect archive/WAD/loose-material changes; explicit Reload rechecks them.
- Remove legacy gallery decoding from profile refresh and defer entity templates until the entity section is requested.
- Stop the worker monitor after completion. Dependency handlers inspect changed objects instead of scanning all brushes on material events.
- Migrate unused generated in-map thumbnail materials in bounded batches; preserve assigned, realized and customized materials.
- Full HL2 check: 6,885 indexed, 6,519 previews, 366 unsupported; ~74 seconds first cache generation in worker, ~2.2 seconds warm validation, ~0.13 seconds profile activation. No map material growth while browsing.

# v0.17.0-pre.alpha — local Blender-native UI (unreleased)

- Replace the giant sidebar with Scene/Object Properties, contextual geometry and face actions, and a compact workspace tool header.
- Keep profile management and maintenance in a small wavelength menu; expose map grid controls through viewport popovers.
- Use the native Outliner for hierarchy, native File import/export menus, and active tool settings for drawing parameters.
- Follow entity selection in Object Properties, preserve brush-entity membership tools, and retain searchable operators.
- Keep face mapping in the Edit Mode Item sidebar, and show build progress, errors and validation targets in Scene Properties.
- Verify real Blender UI drawing, workspace isolation, inspector binding and repeated add-on registration; fix operator cleanup on reload.

# v0.16.4-pre.alpha — local Asset Browser display fix (unreleased)

- Select all catalogs with Blender's empty catalog ID and ALL visibility. The nil UUID selected an empty catalog and hid loaded materials.
- Retry editor configuration until its Asset Browser parameters exist; preserve user catalog/search choices after initial configuration.
- Report ready and skipped material counts separately instead of presenting unsupported materials as unfinished loading.
- Apply saved profile fields as one transaction, then refresh textures once.
- Verified real visible/selectable material entries and texture pixels in the native Asset Browser, plus profile refresh and progress regressions.

# v0.16.3-pre.alpha — local texture-loading fix (unreleased)

- Time-budgeted thumbnail loading with cached lookups and constant-time queues.
- Thumbnail assets do not retain default shader nodes; applying a material builds its complete shader on demand.
- VTF previews remain bounded for single-mip textures, with decoding restricted to sampled pixels/blocks.
- Old oversized previews regenerate, and unused generated shader graphs are cleaned in bounded batches. Assigned, realized and customized shaders are preserved.
- Checks cover single-mip RGBA/DXT previews, cleanup safety, full installed HL2 material loading and UI timer progress.

# v0.16.2-pre.alpha — tested Windows native-grid installer

Builds and installs wavelength's native grid for the exact Blender 5.2.3 LTS Release Candidate Windows x64 build `32ede9dba158` (original executable SHA-256 `19e60200c51e981aa48a515ffc22c46d9192ea0538e249b2891394a425bd855b`). Other Blender executables require their own matching patch.

- Compiles the native Blender renderer with MSVC and reuses the candidate's existing oneAPI AOT kernel DLL, fixing the earlier missing JIT DLL startup failure.
- Fixes Windows installer file flushing and loose Source material path enumeration.
- Includes the Python add-on, editable source, native binary patch, and pinned private Python runtime. No separate Blender runtime is distributed.
- Verified native RNA startup, real OpenGL grid rendering on AMD Radeon(TM) Graphics, yellow parent lines, grey subdivisions, orthographic/perspective occlusion, workspace restoration, installed add-on loading, and brush creation.
- Verified a real install/uninstall/reinstall cycle; uninstall restored the original executable byte-for-byte. Original backups and receipts are retained by the installer.

Close Blender, extract the Windows installer ZIP, and run:

```powershell
.\wavelength-installer.cmd install --force --require-native --blender "C:\path\to\blender.exe" --yes
```

To keep the add-on inside that Blender folder, additionally pass `--addons "C:\path\to\5.2\scripts\addons_core"`. Otherwise the installer uses Blender's normal user add-on directory. Enable wavelength in Preferences and enter its workspace.

The previous Windows 5.2.2 preview remains available in historical releases; this release does not certify or repair that build. Linux retains its existing source and compatibility entry; no newly tested Linux installer or Vulkan certification is claimed here.


# v0.16.1-pre.alpha â€” current authoring tools and Blender diagnostics

- Incorporates v0.16.0 authoring updates: brush creation, editable primitives,
  asset and entity browsing, texture handling, and transform synchronization.
- Blender Diagnostics includes persistent rotating logs and View, Copy, Clear,
  and Export controls with error references and tracebacks.
- Updates the Linux native grid's parent-line color and opacity from v0.16.0.
- Corrects the Linux patch download URL to match its updated checksum.
- Synchronizes shared source and the Windows launcher into the private Pro tree.

Linux x86_64 installer and add-on/source downloads are supplied. This release
does not rebuild Blender. The Windows v0.15 preview has a reported missing
`cycles_kernel_oneapi_jit.dll` failure during startup verification and remains
blocked; no new Windows installer is supplied. The Windows installer executable
fingerprint also differs from the supported ZIP fingerprint. Do not bypass checks.

Earlier validation claims below describe their respective historical releases.

# v0.15.0-pre.alpha â€” Windows native-grid patch preview (historical)

The Windows package now includes a native Blender grid binary patch, not just the
standalone grid-math helper. It bundles Windows Python and installs through
`wavelength-installer.cmd`. Linux retains the tested v0.14 native patch.

**Windows is published for manual verification:** the C++ code is compiled and
binary patch reconstruction is checked, but Windows installation, injection, and
rendering have not been tested. No Wine/Proton or Windows Blender runtime tests
were run by the maintainer.

## Windows x86_64

Target: official **Blender 5.2.2 Windows x64 ZIP executable**, with the exact hash
recorded in `patches/native/manifest.json`. Close Blender, extract the Windows
installer ZIP, and run PowerShell in the extracted folder:

```powershell
.\wavelength-installer.cmd install --force --blender "C:\path\to\blender.exe" --yes
```

Use an Administrator terminal for a Program Files target, or install into a writable
portable Blender folder. Reopen the same executable, enable wavelength, and enter
its workspace. Follow [the Windows verification guide](https://github.com/parallel-minds0/wavelength/blob/v0.15.0-pre.alpha/documentation/WINDOWS-INSTALL.md) and report errors.

```powershell
.\wavelength-installer.cmd status
.\wavelength-installer.cmd repair --force --yes
.\wavelength-installer.cmd uninstall --yes
```

## Linux x86_64

```sh
./wavelength-installer install --force --blender /home/moe/Applications/blender-5.2.2-linux-x64/blender --yes
```

The Linux native payload is unchanged from v0.14.0, where real install, repair,
byte-exact uninstall, native grid spacing, occlusion, and workspace restoration passed.

## Installation behavior

Both packages contain source, a private platform-specific Python runtime, and native
binary differences. No replacement Blender distribution, system Python, or compiler
is required. The installer checks input/output hashes and probes native API startup
before committing installation. It retains the original executable for rollback and
uninstall. `--force` does not bypass binary matching or the startup check.

Only listed executable fingerprints are supported. Other Blender versions, modified
executables, ARM64, and macOS need separate patches. The read-only `diagnose` command
now recognizes native patch fingerprints on both platforms.
