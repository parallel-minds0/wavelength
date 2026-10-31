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
