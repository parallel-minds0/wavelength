# Model pipeline adapters

`source/model_pipeline.py` has no Blender or engine imports. It registers adapters
by stable ID, queries profile/extension support, and returns an `ImportedModel`
containing ordinary Blender objects and warnings. A backend implements:

- `id`, `extensions`, and `supports(engine)` for dispatch;
- `import_model(context, path, skin, body)` for editable source creation;
- `prepare(context, asset_collection, work_directory)` for a build job with an
  ordered `commands` list and `finish()` validation/deployment step.

`model_io.py` owns the asset collection's source/profile/game/backend metadata,
selection, FileHandler, common properties panel, and cancellable subprocess job.
The Source adapter reuses `custom_models` StudioMDL generation and transactional
resource deployment, with an explicit entity subset so a standalone build does
not rebuild unrelated models from the map. Its private compiler origin is excluded
from map export: publishing an asset does not instantiate a prop.

`studio_animation.py` decodes supported binary animation samples independently
of Blender, following Valve's public studio/compressed-vector layouts.
`model_skeleton.py` creates native bones, weights, actions and NLA clips. Preview
mesh caches remain separate from editable imports. Unsupported animation graph
features fail before source geometry is committed.

The native `FILE_OT_publish_model_asset` drop bridge only accepts objects tagged
with the engine-neutral `wl_model_asset` collection pointer. It delegates to the
Python publishing operator, whose poll restricts the action to the Models asset
browser. This has no engine-specific format or compiler knowledge. The viewport's
existing game-model-to-entity assignment path remains separate.

Checks: `blender_model_pipeline.py` (actual StudioMDL static round trip),
`blender_model_pipeline_animation.py` (weighted bone poses and animated rebuild),
and `blender_model_drop_ui.py` (native bridge, Models-only context, modal job,
no prop placement). Test deployment is redirected inside the workspace.

## Phase-one asset lifecycle

`model_lifecycle.py` separates persistent asset collections from entity placements.
`wl_model_schema` and `wl_model_id` identify the definition; source profile, game,
unit scale and source path retain provenance. Mesh/material/image/rig/action
references stay live Blender datablocks rather than duplicate serialized lists.
Source 1 supplies mounted-reference decoding and placement validation/binding
through adapter methods. Existing SMD/compiler/deployment paths remain in use.

Detach copies out a placement into an independent definition and does not edit
its original entity. Make Unique changes only the selected placement. Attach is
an explicit replacement/link operation. When an authoring origin is replaced,
a remaining placement becomes the source origin without moving its visible
geometry. Linked placements use collection references with inverse-origin
transforms; the persistent depsgraph hook touches these inverses only for anchor
updates. Native identity duplication supplies references through the existing
entity duplication hook. Compile-only private origins are excluded from the
placement list and can be replaced by the first real placement.

Static image copies own their dirty pixel buffers, have no original writable
filename and are packed from explicit newly encoded bytes. A persistent save
hook repacks only dirty images marked `wl_model_owned_image`. Original game/image
files are never saved by this hook. Blender modelling controls, rather than a
custom curve UI, remain the geometry-authoring mechanism.

Regression evidence: `blender_model_asset_lifecycle.py` checks mounted import,
pose/units, linked/unique replacements, copy-out detachment, independent texture
pixels across save/reload, export exclusion and operator discoverability.
`blender_model_asset_rigs.py` checks weights, NLA/action independence, edited clips
and remapped native curve dependencies. Existing compiler, world-orientation,
collision, native duplication and legacy detach tests remain required.

## Build snapshots, target adapters and portable models

`model_transfer.py` resolves shipped/registered targets without applying them to
the authoring scene. Each job clones into an isolated scene, normalizes its anchor,
uses stable compiler object names and captures editable data before conversion.
Source→Source delegates to existing SMD/StudioMDL generation and validated caches.
Source→Godot uses Blender's GLB exporter; Source→Source2 emits static FBX/ModelDoc
and compiles in a unique temporary CS2 addon. Reference-only FBX materials use
content-relative VMAT paths rather than Blender suffixes or packed-image names.

`model_materials.realize` owns full-resolution images and resolved VMT/raw texture
bytes. Native preview recovery skips editable model materials. Source compilation
rewrites texture dependencies into the managed namespace and uses edited base/normal
buffers. Cross-engine native shader features without an equivalent need explicit
approximate-conversion acceptance and appear in the report. Procedural shader baking
and universal engine shader parity are not implemented.

Compiler subprocesses are cancellable. Output, package and deployment destinations
use a rollback-capable multi-root commit. Cleanup removes only staged IDs captured
before yielding, preserving objects created while the compiler runs. One build per
asset is allowed at a time. Source geometry, profile and bindings remain intact.

`model_pipeline.register_route` separates conversion capability from import formats.
Unimplemented family pairs fail explicitly. CS2 is static only; Godot collision is
a stub and looping is an importer setting. Source activity/IK/runtime graphs are
not universal interchange semantics. Editable packages retain original clip metadata.

`model_bundle.py` writes schema/hash-inventoried `.wlmodel` ZIPs transactionally.
It rejects traversal, duplicate paths, symlinks, unlisted/missing files and checksum
mismatches before loading the editable collection blend. Imports get a fresh UUID.
Packed images/actions/owned controls travel with the asset; foreign level objects,
collection instances and driver dependencies must be realized or baked explicitly.

Checks: `blender_model_transfer.py` exercises real Source1/CS2 compilers, edited VTF
pixels, source-free GLB, authoring-scene preservation and commit rollback.
`blender_model_transfer_animation.py` covers clip names/FPS, native animation,
unsupported-animation rejection, collision ownership and edits surviving cleanup.
`godot_model_transfer.gd` verifies native Godot skeleton/clip import.
`test_model_bundle.py` checks integrity and route stubs. Existing lifecycle,
legacy compiler, collision, duplication and native publishing tests remain required.


## Local HL2 runtime acceptance investigation

The 2026-11-18 acceptance run compiled an editable static model using StudioMDL,
then built its test room using VBSP, VVIS and VRAD. The BSP contained the model,
material and texture dependencies. A collision mismatch was corrected under
WL-MODEL-031 so Collision None exports solid=0 without changing authored keys.

Runtime outcomes on the installed HL2 combined game were:

| Input | Result |
| --- | --- |
| Stock d1_trainstation_01 | Loaded and displayed the introductory scene |
| wavelength room with packed custom model | Process exited with access violation |
| wavelength room with all custom models excluded | Same startup failure |
| Original minimal_source.vmf compiled directly with Valve tools | Same startup failure |

Steam recorded exit code -1073741819 for the failing processes. Removing the
custom model and bypassing wavelength export both retained the failure.
The crash was subsequently captured with Microsoft ProcDump. Its actual
exception was C00000FD (stack overflow), with repeated calls at server.dll
offsets 0x11671b and 0x10ccc9. The recurring key string was angle. The original
fixture used the legacy scalar key `"angle" "90"` on info_player_start.

Changing only that key to `"angles" "0 90 0"` made the directly compiled room
load and display successfully. Source scene export and the standalone VMF
writer now canonicalize scalar orientation keys, including -1/-2 vertical
sentinels. The shipped fixture uses vector angles. Legacy authoring pairs remain
stored in Blender. This behavior is recorded under WL-IO-047.

The wavelength room was rebuilt with its packed custom model and loaded in the
same test instance. Client sign-on completed, and the blue cube and its packed
material were visually observed. The corrected generated map used its ordinary
lighting build, so HDR-only changes were not needed to resolve this failure.
Collision interaction, animation and broader HL2/GMod acceptance remain pending.
Compiler success is recorded separately from runtime acceptance.

Local fixtures and compiler logs are under build/custom-models in the release
checkout. Runtime logs in the installed hl2_complete directory are
wavelength_model_acceptance.log, wavelength_room_baseline.log and
wavelength_direct_baseline.log. These local files are diagnostic evidence and
are not distributed as part of the handbook.

The isolated test game and additional logs are under build/hl2-runtime-clean.
Its first configuration attempt had unquoted asset paths, which caused a
startup-image error. Correcting those paths restored asset mounting and exposed
the same angle-key failure. The installed game configuration was not edited.
The captured dump and debugger output remain local under its dumps directory.
