# Module inventory

Generated from the current checkout. Source links open local line-anchored viewers.

## addon/wavelength/source/__init__.py

wavelength Blender add-on. Core format modules import without Blender.

{source}`addon/wavelength/source/__init__.py`

## addon/wavelength/source/asset_browser.py

Native Asset Browser publishers using existing WAD/VPK/FGD backends.

{source}`addon/wavelength/source/asset_browser.py`

## addon/wavelength/source/asset_index.py

Local, incremental engine asset metadata. No game data enters releases.

{source}`addon/wavelength/source/asset_index.py`

## addon/wavelength/source/asset_placement.py

Click-to-paint surfaces and click-to-place entities from the native browser.

{source}`addon/wavelength/source/asset_placement.py`

## addon/wavelength/source/asset_search.py

Debounce the native texture filter without replacing Blender's browser.

{source}`addon/wavelength/source/asset_search.py`

## addon/wavelength/source/authoring.py

High-level engine authoring workflows for Wavelength 0.10 pre-alpha.

These operators deliberately compose the existing brush/entity/texture/export systems.
They do not replace the canonical geometry, grid, transform or MAP paths.

{source}`addon/wavelength/source/authoring.py`

## addon/wavelength/source/axis_guides.py

Temporary world-axis guides shared by keyboard and gizmo transforms.

{source}`addon/wavelength/source/axis_guides.py`

## addon/wavelength/source/brush_create.py

Profile-aware interactive cube/brush creation.

All profiles expose the same click-click prototyping interaction. Blender mode snaps
to Blender's viewport grid and creates an ordinary mesh; engine profiles snap to
their profile grid and create brush-tagged meshes.

{source}`addon/wavelength/source/brush_create.py`

## addon/wavelength/source/bsp_decompose.py

Bounded, exact-plane convex partition of closed Boolean meshes.

Partition the bounding solid by the input face planes, then retain cells whose
centres lie inside the oriented input surface. No voxelization or grid rounding:
the surface planes survive conversion. This deliberately favours correctness
over brush count; complex assets should use the model pipeline instead.

{source}`addon/wavelength/source/bsp_decompose.py`

## addon/wavelength/source/build/__init__.py

External compiler/toolchain integration.

{source}`addon/wavelength/source/build/__init__.py`

## addon/wavelength/source/build/pipeline.py

Polled subprocess pipeline; no Blender API and no shell command strings.

{source}`addon/wavelength/source/build/pipeline.py`

## addon/wavelength/source/build/toolchains.py

Resolve supported compiler names without assuming Windows executable suffixes.

{source}`addon/wavelength/source/build/toolchains.py`

## addon/wavelength/source/context_policy.py

Context capabilities and object meaning; independent of Blender execution.

{source}`addon/wavelength/source/context_policy.py`

## addon/wavelength/source/context_state.py

Scene context transitions, reversible helper visibility and clean render hooks.

{source}`addon/wavelength/source/context_state.py`

## addon/wavelength/source/csg.py

Editable node Booleans and transactional, profile-owned BSP finalization.

{source}`addon/wavelength/source/csg.py`

## addon/wavelength/source/custom_models.py

Editable custom Source models owned by map entities and built as dependencies.

{source}`addon/wavelength/source/custom_models.py`

## addon/wavelength/source/cutter_snap.py

Screen-radius geometry targeting and surface-oriented placement cursor.

{source}`addon/wavelength/source/cutter_snap.py`

## addon/wavelength/source/cutter_solid.py

Capped solid operations from a planar cutter path.

{source}`addon/wavelength/source/cutter_solid.py`

## addon/wavelength/source/diagnostics.py

Persistent, bounded add-on diagnostics and CLI/error log; imports without Blender.

{source}`addon/wavelength/source/diagnostics.py`

## addon/wavelength/source/diagnostics_ui.py

Blender-only controls for inspecting and sharing add-on diagnostics.

{source}`addon/wavelength/source/diagnostics_ui.py`

## addon/wavelength/source/draw_displacement.py

Export structured drawing grids as exact Source displacement brush faces.

{source}`addon/wavelength/source/draw_displacement.py`

## addon/wavelength/source/draw_geometry.py

Curve sampling and outline validation independent of Blender.

{source}`addon/wavelength/source/draw_geometry.py`

## addon/wavelength/source/editor.py

Reusable editing operations for convex brushes and engine texture previews.

{source}`addon/wavelength/source/editor.py`

## addon/wavelength/source/engine_tools.py

Workspace-scoped engine tool column and undoable grid transforms.

{source}`addon/wavelength/source/engine_tools.py`

## addon/wavelength/source/entity/__init__.py

Entity catalogs, editor representations, and the Wavelength Asset Browser.

{source}`addon/wavelength/source/entity/__init__.py`

## addon/wavelength/source/entity/browser.py

Wavelength Asset Browser backed by Blender's native Asset Browser.

Python add-ons cannot register a new Blender Space type.  We therefore publish
active-profile entity templates as Current File assets.  Blender supplies the
thumbnail/name tile UI and native drag from the Asset Browser into a 3D View.
A depsgraph finalizer turns dropped templates into normal Wavelength entities.

{source}`addon/wavelength/source/entity/browser.py`

## addon/wavelength/source/entity/catalog.py

No module docstring yet.

{source}`addon/wavelength/source/entity/catalog.py`

## addon/wavelength/source/entity/fgd.py

Read common FGD classes/properties without evaluating FGD content as code.

{source}`addon/wavelength/source/entity/fgd.py`

## addon/wavelength/source/entity/goldsrc.py

Built-in Half-Life/GoldSrc entity property fallback.

This is intentionally a pragmatic authoring catalog, not a replacement for a
mod's FGD. Loaded FGD data wins; these definitions fill missing inherited or
stock HL1 fields so the UI remains useful out of the box.

{source}`addon/wavelength/source/entity/goldsrc.py`

## addon/wavelength/source/entity/icons.py

Editor-only SVG icon references for abstract Half-Life point entities.

The Wavelength HL1 icon pack is parsed directly.  Do not depend on Blender's
optional SVG import extension: entity visualization must work in a stock build.

{source}`addon/wavelength/source/entity/icons.py`

## addon/wavelength/source/entity/models.py

Editor-only GoldSrc glTF and Source studio-model entity references.

{source}`addon/wavelength/source/entity/models.py`

## addon/wavelength/source/entity/source_schema.py

Use the selected game's installed Hammer schema, never a Source-wide union.

{source}`addon/wavelength/source/entity/source_schema.py`

## addon/wavelength/source/external_library.py

Native external asset-library integration; no catalog materials in the map.

{source}`addon/wavelength/source/external_library.py`

## addon/wavelength/source/formats.py

Bounded classic/Valve 220 MAP reader and deterministic writer.

{source}`addon/wavelength/source/formats.py`

## addon/wavelength/source/geometry.py

Convex-brush geometry, independent of Blender.

All coordinates in this experiment use one Blender unit per engine unit.
This is not an engine profile or a complete MAP importer.

{source}`addon/wavelength/source/geometry.py`

## addon/wavelength/source/geometry_debug.py

Viewport mesh diagnostics: explicit scans, automatic failure capture and live repair feedback.

{source}`addon/wavelength/source/geometry_debug.py`

## addon/wavelength/source/geometry_diagnostics.py

Locate the mesh elements responsible for the convex validator's first error.

{source}`addon/wavelength/source/geometry_diagnostics.py`

## addon/wavelength/source/goldsrc_import.py

GoldSrc entity model resolution and shared Blender geometry/materials.

{source}`addon/wavelength/source/goldsrc_import.py`

## addon/wavelength/source/goldsrc_model.py

Bounded GoldSrc MDL v10 decoding, using installed game/mod assets directly.

{source}`addon/wavelength/source/goldsrc_model.py`

## addon/wavelength/source/goldsrc_tools.py

Discover Windows Half-Life assets and an existing compatible GoldSrc toolchain.

{source}`addon/wavelength/source/goldsrc_tools.py`

## addon/wavelength/source/grid.py

Native grid state bridge. Python never submits grid geometry or GPU shaders.

The patched Blender renderer owns plane intersection, coverage, native depth and
compositing. This module only supplies per-viewport settings and restores them.

{source}`addon/wavelength/source/grid.py`

## addon/wavelength/source/identity.py

Assign object identities after native Blender duplication, without changing mesh data.

{source}`addon/wavelength/source/identity.py`

## addon/wavelength/source/keyvalues.py

Bounded Valve KeyValues text parser; retains order and repeated keys.

{source}`addon/wavelength/source/keyvalues.py`

## addon/wavelength/source/launcher.py

Locate the Steam client without requiring Windows users to edit PATH.

{source}`addon/wavelength/source/launcher.py`

## addon/wavelength/source/library_prepare_worker.py

Profile indexing and incremental thumbnail preparation outside the editor.

{source}`addon/wavelength/source/library_prepare_worker.py`

## addon/wavelength/source/library_worker.py

Isolated Blender process: build preview-only external material libraries.

{source}`addon/wavelength/source/library_worker.py`

## addon/wavelength/source/mesh_assets.py

Static mesh/texture handoff for mesh engines, isolated from BSP and entities.

Evaluate into a temporary scene, bake world transforms and normalize physical
units there. Never apply modifiers, rewrite shaders or change selection in the
authoring scene. Completed bundles contain only meshes, materials and images.

{source}`addon/wavelength/source/mesh_assets.py`

## addon/wavelength/source/model_browser.py

Contextual entity model choices in Blender's native Asset Browser.

{source}`addon/wavelength/source/model_browser.py`

## addon/wavelength/source/model_formats.py

Small deterministic Source model/material packaging primitives.

{source}`addon/wavelength/source/model_formats.py`

## addon/wavelength/source/model_import.py

Source render meshes for imported models and engine prop previews.

{source}`addon/wavelength/source/model_import.py`

## addon/wavelength/source/model_materials.py

Convert supported Blender model materials to owned VMT/VTF dependencies.

{source}`addon/wavelength/source/model_materials.py`

## addon/wavelength/source/model_smd.py

Evaluate editable Blender sources into reference SMD and scene-frame clips.

{source}`addon/wavelength/source/model_smd.py`

## addon/wavelength/source/model_thumbnail_worker.py

Render a small batch of Source model thumbnails in a separate Blender process.

{source}`addon/wavelength/source/model_thumbnail_worker.py`

## addon/wavelength/source/native_ui.py

Blender editor integration: editing in context, setup in a small menu.

{source}`addon/wavelength/source/native_ui.py`

## addon/wavelength/source/node_pencil.py

Curve-driven pencil geometry and capped cutting volumes generated by nodes.

{source}`addon/wavelength/source/node_pencil.py`

## addon/wavelength/source/node_primitives.py

Versioned parametric Geometry Nodes generators; Python never builds shape vertices.

Node graphs own mesh construction. This adapter validates scalar parameters,
selects profile output parts and evaluates/attaches graphs at Blender boundaries.

{source}`addon/wavelength/source/node_primitives.py`

## addon/wavelength/source/node_stairs.py

Versioned straight-stair Geometry Nodes assets. Python builds graphs, not vertices.

{source}`addon/wavelength/source/node_stairs.py`

## addon/wavelength/source/paths.py

Filesystem locations inside the installed Wavelength package.

{source}`addon/wavelength/source/paths.py`

## addon/wavelength/source/pencil.py

Editable line/curve guides with explicit knife projection and mesh creation.

{source}`addon/wavelength/source/pencil.py`

## addon/wavelength/source/precision_move.py

One undoable map-unit transform, without settle-time corrections.

{source}`addon/wavelength/source/precision_move.py`

## addon/wavelength/source/primitive_ui.py

Persistent parameter controls with transactional regeneration and Blender undo.

{source}`addon/wavelength/source/primitive_ui.py`

## addon/wavelength/source/primitives.py

Profile-aware primitives: convex brush parts only when BSP validation is requested.

{source}`addon/wavelength/source/primitives.py`

## addon/wavelength/source/procedural.py

Generator-independent definitions, evaluation and profile validation.

No Blender data mutation belongs in this module. Adapters return local-space
mesh parts; Blender owns committing them and baking evaluated objects.

{source}`addon/wavelength/source/procedural.py`

## addon/wavelength/source/profile_registry.py

Protected shipped template inheritance; no Blender dependency or executable JSON.

{source}`addon/wavelength/source/profile_registry.py`

## addon/wavelength/source/profile_setup.py

Profile library lifecycle and bounded import of worker-rendered asset previews.

{source}`addon/wavelength/source/profile_setup.py`

## addon/wavelength/source/profile_store.py

Registered profiles: inherited overrides, legacy migration and dependency safety.

{source}`addon/wavelength/source/profile_store.py`

## addon/wavelength/source/profile_ui.py

Register, inherit, inspect and remove user profiles without editing templates.

{source}`addon/wavelength/source/profile_ui.py`

## addon/wavelength/source/profiles.py

Engine authoring profiles.  Tools read units/behavior from the active profile.

{source}`addon/wavelength/source/profiles.py`

## addon/wavelength/source/resize_gizmo.py

Engine-mode brush boundary resize gizmos.

Unlike Blender's proportional Scale transform, these handles move one brush
boundary while the opposite boundary remains fixed.  The dragged boundary is
quantized to Wavelength's engine grid during the interaction.

{source}`addon/wavelength/source/resize_gizmo.py`

## addon/wavelength/source/scene.py

Blender scene adapter. Geometry and MAP data remain independent of bpy.

{source}`addon/wavelength/source/scene.py`

## addon/wavelength/source/source2_assets.py

CS2 VMAT library: private, fingerprinted, on-demand VRF texture decoding.

Archive indexing stays pure Python. Source 2 Viewer is an external dependency,
not redistributed with the addon. Original material paths survive preview and
map export; a viewport approximation never replaces the engine's shader.

{source}`addon/wavelength/source/source2_assets.py`

## addon/wavelength/source/source2_dmx.py

Typed DMX KeyValues2 and editable VMAP polygon topology.

VMAP stores destination-vertex half edges, with explicit opposite and next
indices. UVs belong to half-edge corners, not shared mesh vertices. This module
has no Blender dependency so malformed input can be rejected before allocation.

{source}`addon/wavelength/source/source2_dmx.py`

## addon/wavelength/source/source2_map.py

Static editable Source 2 VMAP meshes with CS2 material references.

Transforms are baked in Source inches, Z-up. Entity metadata and model instances
are excluded. Binary DMX conversion is delegated to the installed CS2 tools.

{source}`addon/wavelength/source/source2_map.py`

## addon/wavelength/source/source_assets.py

Read local Source VPK/VMT/VTF assets without extracting game archives.

{source}`addon/wavelength/source/source_assets.py`

## addon/wavelength/source/source_tools.py

Source 1 toolchain boundaries; runtime platform is separate from compiler host.

{source}`addon/wavelength/source/source_tools.py`

## addon/wavelength/source/studio_model.py

Bounded Source 1 MDL44–49 + VVD4 + VTX7 reference-pose mesh reader.

Layout reference: Valve source-sdk-2013 public/studio.h and optimize.h.
No game data or third-party importer code is bundled.

{source}`addon/wavelength/source/studio_model.py`

## addon/wavelength/source/sun.py

Interactive light_environment previews using real Blender Sun lights.

{source}`addon/wavelength/source/sun.py`

## addon/wavelength/source/surface_tools.py

Asset Browser surface editing and a shared scene asset eyedropper.

{source}`addon/wavelength/source/surface_tools.py`

## addon/wavelength/source/system_tree.py

Derived engine/system view of Wavelength objects.

Blender Collections remain artist-owned.  This module never moves or links objects;
it only derives engine-facing categories from existing Wavelength metadata.

{source}`addon/wavelength/source/system_tree.py`

## addon/wavelength/source/terrain.py

General Geometry Nodes heightfields with a Source displacement export adapter.

{source}`addon/wavelength/source/terrain.py`

## addon/wavelength/source/terrain_blend.py

Deterministic Source terrain blend recipes and bounded asset staging.

{source}`addon/wavelength/source/terrain_blend.py`

## addon/wavelength/source/terrain_face.py

Source brush-face displacement attachments; preserve the original solid.

{source}`addon/wavelength/source/terrain_face.py`

## addon/wavelength/source/terrain_paint.py

Non-destructive height/mask painting on a normalized terrain control surface.

{source}`addon/wavelength/source/terrain_paint.py`

## addon/wavelength/source/terrain_sew.py

Persistent quad-surface adjacency, world-space sewing and Source UV sampling.

{source}`addon/wavelength/source/terrain_sew.py`

## addon/wavelength/source/textures.py

Local WAD libraries, paged previews, material assignment and build texture sets.

{source}`addon/wavelength/source/textures.py`

## addon/wavelength/source/tool_snap.py

Blender owns snap enable/targets; the profile supplies engine grid spacing.

{source}`addon/wavelength/source/tool_snap.py`

## addon/wavelength/source/tool_textures.py

Profile-specific names for equivalent compiler surfaces.

{source}`addon/wavelength/source/tool_textures.py`

## addon/wavelength/source/transform_bridge.py

Native toolbar identities with wavelength controllers and exclusive G/R/S.

The native event filter skips competing transform keymap entries only when this
module's route operator polls. No user keymap flags or preferences are mutated.
Tool definitions are adapted per context; the original definitions remain intact.

{source}`addon/wavelength/source/transform_bridge.py`

## addon/wavelength/source/transform_sync.py

Settle-time engine-grid snapping for Blender-native brush transforms.

This never replaces G/S/R.  It waits until Blender has stopped changing a brush,
then resolves translation and scale through the active engine profile grid.

{source}`addon/wavelength/source/transform_sync.py`

## addon/wavelength/source/ui.py

wavelength: Blender-native Quake and GoldSrc level authoring.

{source}`addon/wavelength/source/ui.py`

## addon/wavelength/source/validation.py

Engine-facing scene validation for the pre-alpha.

{source}`addon/wavelength/source/validation.py`

## addon/wavelength/source/vmf.py

Source 1 VMF brush/point/brush-entity interchange. No displacement conversion.

{source}`addon/wavelength/source/vmf.py`

## addon/wavelength/source/wad.py

Bounded WAD2/WAD3 mip-texture and Quake PAK/BSP readers.

Independent implementation using id's published WAD/miptex/PAK structures.
No game assets or palettes are distributed with this module.

{source}`addon/wavelength/source/wad.py`

## addon/wavelength/source/workspace.py

Workspace lifecycle; no transform-correction timers or global editing hooks.

{source}`addon/wavelength/source/workspace.py`

## installer/wavelength_installer/__init__.py

Standalone installer framework; no binary patching enabled.

{source}`installer/wavelength_installer/__init__.py`

## installer/wavelength_installer/app.py

Bundled-runtime entry point: add/remove both Wavelength components together.

{source}`installer/wavelength_installer/app.py`

## installer/wavelength_installer/binary_patch.py

Offline, exact-build binary patch engine.

Never modifies the original executable. Recipes must be explicitly verified and
match the exact SHA-256 of the input. A patch recipe is not a renderer hook.

{source}`installer/wavelength_installer/binary_patch.py`

## installer/wavelength_installer/core.py

Wavelength installer foundation. Deliberately refuses unsupported binary patching.

{source}`installer/wavelength_installer/core.py`

## installer/wavelength_installer/delta_patch.py

Apply checksum-bound BSDIFF40 patches using the bundled Python standard library.

Release payloads contain differences, never a Blender runtime. Every patch is
bound to both the original and resulting executable; --force cannot waive either.

{source}`installer/wavelength_installer/delta_patch.py`

## installer/wavelength_installer/deployment.py

Prepare experimental payloads in isolation; Python owns deployment.

{source}`installer/wavelength_installer/deployment.py`

## installer/wavelength_installer/discovery.py

Local discovery without executing candidate applications.

{source}`installer/wavelength_installer/discovery.py`

## installer/wavelength_installer/experimental.py

Structural shader classification and bounded, idempotent ELF replacements.

Unknown instructions are never stripped speculatively. Each whole NUL-delimited
string is replaced once, even when it contains both shader stages.

{source}`installer/wavelength_installer/experimental.py`

## installer/wavelength_installer/forced.py

Forced installation with explicit ownership and retained reconciliation backups.

{source}`installer/wavelength_installer/forced.py`

## installer/wavelength_installer/grid_source_probe.py

Read-only probe for Blender 5.2.x overlay grid shader source.

No binary patch is produced. A source match is not a compatible executable patch.

{source}`installer/wavelength_installer/grid_source_probe.py`

## installer/wavelength_installer/instances.py

Instance addresses. The historical root receipt remains the default instance.

{source}`installer/wavelength_installer/instances.py`

## installer/wavelength_installer/lifecycle.py

One transaction owns the Python add-on and compiled Blender patch together.

The installer applies verified build-specific bytes; the C++ payload does not
perform injection. A journal and original backup support recovery and removal.

{source}`installer/wavelength_installer/lifecycle.py`

## installer/wavelength_installer/management.py

Lifecycle coordination layered over the validated installer transaction engine.

{source}`installer/wavelength_installer/management.py`

## installer/wavelength_installer/native_bridge.py

ctypes bridge for the compiled native prototype; no Blender internals accessed.

{source}`installer/wavelength_installer/native_bridge.py`

## installer/wavelength_installer/renderer_probe.py

Read-only Blender binary reconnaissance. No injection or modification.

An ELF binary fingerprint is NOT a verified renderer hook. Grid shader strings
may be absent because Blender embeds or transforms shader sources at build time.

{source}`installer/wavelength_installer/renderer_probe.py`

## installer/wavelength_installer/source_bundle.py

Run the installer directly from the source tree without a separate add-on ZIP.

{source}`installer/wavelength_installer/source_bundle.py`

## tools/build_installer.py

Package platform-specific installers with pinned private Python runtimes.

{source}`tools/build_installer.py`

## tools/build_native_blender.py

Apply the native grid patch to matching Blender sources and build a separate executable.

{source}`tools/build_native_blender.py`

## tools/build_windows_candidate.py

Build the exact candidate in an x64 Visual Studio Developer shell.

{source}`tools/build_windows_candidate.py`

## tools/build_windows_cpp.py

Cross-compile the standalone Wavelength C ABI library on Linux; never run it.

This library exposes grid math only. It is not the Blender renderer patch.

{source}`tools/build_windows_cpp.py`

## tools/docs.py

Validate Markdown/source contracts; build HTML/PDF; sync packaged Markdown.

{source}`tools/docs.py`

## tools/grid_demo.py

Interactive native-shader experiment; only use with blender-grid-test.

{source}`tools/grid_demo.py`

## tools/launch_workspace.py

Load this source tree into a temporary Blender session without installation.

{source}`tools/launch_workspace.py`

## tools/make_binary_patch.py

Generate an installer delta from original and internally built executables.

Requires bsdiff4==1.2.6 in the maintainer environment only. End-user installation
uses the standard-library decoder, and never invokes a compiler or downloads Blender.

{source}`tools/make_binary_patch.py`

## tools/package_native_blender.py

Package a compiled native Blender with a session-local wavelength launcher.

{source}`tools/package_native_blender.py`

## tools/prepare_windows_delta.py

Generate a Windows native patch; do not execute Blender or test injection.

{source}`tools/prepare_windows_delta.py`

## tools/prototype_grid.py

Experimental native-shader patch for one exact Blender payload; outputs a copy.

This tests the grid mechanism, not the future C++ per-view state bridge. Do not
add its recipe to the production support manifest based on a screenshot alone.

{source}`tools/prototype_grid.py`

## tools/provision_pro.py

Create/verify private Pro remote; never print credentials or push unverified visibility.

{source}`tools/provision_pro.py`

## tools/release.py

Validate/package by default; --publish commits, tags and atomically pushes this repo.

{source}`tools/release.py`

## tools/sync_editions.py

Copy explicitly shared source, detect drift, and preserve Pro extensions.

No runtime dependency, symlink, submodule, game assets or build outputs are used.

{source}`tools/sync_editions.py`
