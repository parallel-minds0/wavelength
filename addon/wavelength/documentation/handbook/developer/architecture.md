# Architecture and ownership

## Package boundaries

`addon/wavelength/__init__.py` is the Blender entry point. `source/` owns add-on
registration, UI, scene adapters, tool behavior and engine integration.
`environment/` contains bundled definitions, fixtures and SVG helpers.
`installer/wavelength_installer/` owns installation, fingerprints, source bundles
and restoration. `patches/` describes exact native compatibility. `tools/`
contains development and packaging commands. `tests/` separates pure Python
checks from scripts that require Blender or installed engine tooling.

The native Blender patch and Python add-on form one installation. Compatibility
is exact-build-specific; a Python version declaration is not proof that a native
patch can be applied to another Blender binary. Historical grid prototypes under
`native/` are distinct from the current patched Blender delivery path.

## Responsibility map

| Responsibility | Main source owners |
| --- | --- |
| Profile units, families and constraints | `profiles.py`, `authoring.py`, `procedural.py` |
| Workspace and context capabilities | `workspace.py`, `context_policy.py`, `context_state.py` |
| Persisted brush faces and format conversion | `scene.py`, `formats.py`, `vmf.py` |
| Asset indexing, selection, assignment and drag handling | `asset_index.py`, `asset_browser.py`, `asset_placement.py` |
| Setup, caches and external preview workers | `profile_setup.py`, `library_worker.py`, `model_thumbnail_worker.py` |
| Entity definitions and representations | `entity/`, `entity/source_schema.py`, `model_browser.py` |
| Procedural geometry and node adapters | `procedural.py`, `node_stairs.py`, `primitive_ui.py` |
| Pencil paths, snapping and solid operations | `pencil.py`, `cutter_snap.py`, `cutter_solid.py` |
| Compiler stages and output publication | `build/pipeline.py`, `build/toolchains.py`, `source_tools.py` |

See the [module inventory](../reference/modules.md) for exact paths, current module
docstrings and source links. Module summaries are not declarations that every
function is a stable public API.

## Keep computation separate from Blender mutation

Profiles, format records and geometry algorithms can be inspected/tested outside
Blender. Scene adapters and operators manipulate Blender data and must run in an
appropriate context. Background workers isolate expensive content preparation;
they do not load the entire game model library into the authoring scene.

Avoid adding a dependency on `bpy` to a format/parser module merely to reach a UI
setting. Pass the required engine, scale or record explicitly.

## Context mapping contract

A native interface is an entry point, not an authority for engine units or grid
spacing. Resolve workspace/context and active profile first, then use its backend
or profile-aware native adapter. Toggling an option such as snapping changes that
option, not which system owns the operation. Outside the active context, retain
normal Blender behavior; avoid global keymap/preferences mutations and post-hoc
geometry correction timers.

The snap adapters query `WAVELENGTH_OT_profile_grid_context` synchronously and
read `scene.wavelength.profile_grid_spacing`, a derived RNA value backed by the
profile policy. Native transform grid initialization and viewport grid commands
share that source. Grid target conversion is local to the running transform and
does not rewrite the user's Snap Element selection. Assembly-aware native menu
routing reuses the existing wavelength mesh/object operation.

New integrations should document their native entry points, profile-owned inputs,
context gate, unsupported-mode fallback and cleanup/undo behavior. This contract
applies to future integrations; it does not imply every Blender operator already
has an engine adapter.

## Profile registry and inheritance

`profile_registry.Templates` loads the protected
`environment/profiles/templates.json` graph. It resolves parent fields by deep
copy, rejects cycles/missing parents and keeps abstract/backend aliases local to
their defining node. `profiles.PROFILES` exposes resolved concrete templates for
existing backend consumers. Shared Source constraints and discovery data no
longer require duplicating an HL2 profile to define another game.

`profile_store.Store` owns UUID-backed schema-2 user records outside the addon.
Each record references a shipped template or user parent and stores settings
overrides. Schema-1 snapshots acquire their existing engine as parent and retain
their UUID. The store checks the entire affected registry graph before writes,
rejects backend replacement through settings, protects template IDs and blocks
parent removal while children depend on it. Bundles include user ancestors in
dependency order. Imported JSON is configuration data, not executable code.

Backend RNA enum numbers remain stable. User picker numbers are persisted and
checked for collisions. `profile_ui` resolves missing fields through RNA defaults,
runtime path discovery and inherited overrides; same-backend loads cannot retain
unrelated settings from the prior profile. Failed application restores the prior
scene settings. Selection is reconstructed from the stable active profile ID on
load, and handlers/timers are removed during unregister.

Registration is not engine implementation. The generic Source Windows template
supports VMF export and deliberately disables Build/Play. New game compilation
requires an adapter supporting that engine branch, not merely a JSON name change.
Finalized geometry retains its captured definition/ownership; registry edits do
not regenerate objects. Source bundles and release archives explicitly include
the protected JSON registry.

## Source 2 map and material adapters

`source2_dmx` parses typed KeyValues2 documents and resolves element references.
Its editable polygon representation uses destination-vertex half edges: adjacent
faces share opposite edge pairs, open borders have explicit void half edges, and
UVs remain per corner. Topology and stream indices are checked before Blender
objects are allocated. Unsupported subdivision surfaces fail explicitly.

`source2_map` bakes evaluated Blender geometry to Source inches and Z-up, preserving
the original scene. Native VMAT paths survive export; new Blender materials get
generated VMAT/PNG sidecars under the content root. Map publication occurs after
mesh evaluation. The installed CS2 DMX converter handles binary VMAP input and
reads the installed editor scaffold, so auxiliary map metadata follows the
installed engine version. No stock geometry/entities are copied into output.

`source2_assets` indexes loose VMATs and VPK entries, decodes compiled resources
through the separately installed Source 2 Viewer CLI and fingerprints the source
archive/material. Viewport shaders approximate decoded material inputs while
retaining the original game-relative VMAT as the export authority. The existing
external-library worker builds preview shards in bounded batches and drops unused
image data between batches; full-resolution realization is deferred until use.
Preparation can be paused while retaining cached previews.
