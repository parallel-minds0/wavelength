# Runtime asset cache and progressive import

`scene.import_map(..., defer_assets=None)` defers asset previews in interactive
Blender by default. Background import stays synchronous for exporters and tests.
Explicit `defer_assets=True` exercises the progressive path headlessly.

- `source_assets.Assets.fingerprint()` resolves mount precedence without reading
  payloads. VMT caches track included files. VPK index/gameinfo changes refresh
  the mount library; loose overrides are checked when resolving each asset.
- `source_assets.decoded_preview()` caches bounded VTF previews. The vector DXT
  path uses Blender's NumPy and is tested against the portable decoder.
- `model_import.decoded()` checks the LRU/disk cache before parsing MDL/VVD/VTX;
  cached JSON is bounded and validated before creating Blender meshes.
- `runtime_cache` uses atomic, compressed, bounded files, never pickle. Cache
  failures rebuild from game assets instead of blocking import.
- `asset_loading` deduplicates worker requests, keeps original UV dimensions on
  placeholders, applies completed previews in timed batches, and shares finished
  meshes among repeated props. Scene/profile/entity changes discard stale tasks.
- `asset_runtime_worker` only decodes requested assets. It does not create scene
  objects. Decode errors are reported on the corresponding material/entity.
- Pending markers survive save/reopen. Addon unload terminates its own worker.
  The thumbnail-preparation worker tracks cache-hit dependencies as well as reads.

Validation: `tests/test_source_assets.py`, `tests/blender_source_asset_cache.py`,
`tests/blender_source_models.py`, and the real-map progressive viewport check.
The cache suite covers edited VTF/model companions, inherited VMT changes, loose
mount overrides, corrupt pixels, disk reuse, pending save/reload, and shared props.

### Idle viewport indexes

The System Tree caches engine-category membership and category eye states. Assembly
and pencil timers share role indexes which do not expire merely because time passes.
Dependency-graph updates, file loading, undo and redo invalidate these caches; object
count and profile changes also invalidate category membership. Scripts that alter raw
object ID properties should call `object.update_tag()` so Blender and these indexes
observe the edit. Visibility still uses the current view layer.

In a fixed Garry's Mod fork.vmf camera test on 2026-10-29, removing repeated idle
scans improved Material Preview from 2.05 to 3.29 FPS. This is not a claim of smooth
large-map rendering: significant native renderer/scene cost remains. Solid, Material
Preview and Rendered retain Blender's normal shading behavior.

Source entity model reassignment uses asset_loading.entity after renderer preload,
so a prepared map receives a mesh representation rather than a native-only Empty.
Decode work runs in the isolated asset worker. The existing reference survives until
a replacement is ready; the newest request supersedes older requests for that entity.
The model browser observes only the active entity's model/skin/body keys, rather than
rescanning the whole map. Removing an active reference activates its owning entity.

Native AssetRepresentation labels read wl_entity_browser_template for entity assets;
object ID names and relative asset paths remain unique and unchanged. File Browser
banner updates must tolerate a null layout on first draw, before layout initialization.
