# Native Source 1 asset backend

The native backend reads original mounted VPK, VMT, VTF and MDL/VVD/VTX assets.
Python binds a resolved mount order and asset name to an object or material. It
does not decode preview pixels, build shader graphs, or create model meshes for
this path. Stock Blender keeps the portable preview backend.

## Runtime and ownership

`native/source1/assets.hh` implements bounded binary readers, VPK CRC checking,
VMT patch includes, VTF mip layout and reference-pose model topology. It uses no
game DLLs or third-party importer. Model material slots, skin/body variants,
normals and UVs remain engine data.

`draw_source_assets.cc` owns a single decoding thread. The draw thread queues each
unique request once; missing assets are negatively cached. Archive directories
are indexed once per mount generation. Identical textures share CPU payloads and
GPU textures; repeated props share vertex/index buffers. The cache has a 512 MiB
CPU payload budget and a 4096-request limit. It fails with a diagnostic when full
rather than silently increasing its allocation. GPU copies add memory beyond the
CPU budget. Cache resources are released while Blender's GPU context is valid.

DXT1/DXT3/DXT5 VTF blocks go directly to compressed GPU textures. Uncompressed
formats receive only the channel swizzle required for GPU upload. There is no
PNG/JSON preview intermediate and no Blender Image. UV orientation is handled in
the native shader, keeping the original compressed blocks intact.

The Workbench renderer draws engine materials on Blender's existing editable
brush batches. A model reference is an Empty carrying an engine path; its native
model buffers use the instance transform and profile unit scale. Native bounds
participate in viewport culling. Asset completion invalidates accumulated
Workbench samples without editing scene geometry or invoking Python per frame.

Solid defaults to untextured material colors, including native props. Material
Preview uses Blender's normal preview engine; Rendered uses the chosen scene
engine. Neither mode is redirected to Workbench. After map import,
`render_support.py` preloads all referenced materials and model variants in one
background preparation job, including when the viewport is Solid. The worker
writes one dependency-closed Blender library with shared images and meshes.
The main thread reads that library once and binds all assets in one transaction.
There are no per-material library reads/copies or repeated live-map publications.
The initial library read, binding and shader/GPU initialization still have a
one-time cost. Subsequent mode switches retain the same datablocks. Saved maps
with prepared model meshes reuse them on opening instead of rebuilding props.
F12/background renders prepare any remaining bindings before rendering. The
viewport header reports background preload progress without repeatedly writing
progress text into Scene RNA. Cached texture previews remain limited to 512
pixels; this bridge does not implement full Source shader parity.

## Browser isolation

Entity and model asset templates live in persistent, unlinked collections rather
than the level scene graph. Entity catalogs reuse their IDs until the profile or
catalog changes, or the user explicitly refreshes them. Thumbnail PNGs are loaded
through ImBuf buffers in the native Blender build, avoiding temporary Image IDs
and the resulting map-wide shading invalidations. Unrelated shading notifications
skip brush face checks when material bindings and geometry have not changed.

Model choices publish in pages of 96 while Models is open. More Models requests
another page; search prioritizes matches from the entire index. Switching away
pauses publication, so an unseen model catalog cannot keep rebuilding scene state.

## Persisted bindings

- Materials: `wl_source_native_material`, `wl_source_mounts`,
  `wl_source_revision`; `wl_width`/`wl_height` retain engine UV dimensions.
- Models: `wl_source_native_model`, `wl_source_mounts`, `wl_source_revision`,
  `wl_source_unit`, `wl_source_skin`, `wl_source_body`.
- Existing `wl_texture`, entity pairs and export exclusions remain authoritative
  for map export. GPU-only Solid does not embed model geometry. After requesting
  Blender material/render mode, the shared rendering meshes and images are saved
  with the blend file.

Saved bindings retain original game paths and require the corresponding local
game files. Existing converted preview data is retained on migration; no user
material graph or packed image is deleted automatically. Reload Map Asset
Previews checks mounted file revisions and refreshes bindings.

## Current coverage and limits

The initial native preview covers base/tool textures, alpha-tested materials,
VMT patch includes and static reference-pose models (MDL versions 44–49, VVD4,
VTX7, LOD zero). Unsupported pixel formats, invalid companions and missing files
produce native diagnostics. Animation, Source shader proxies, full material
lighting/effects, translucent blending, and displacement layer blending are not
implemented by this initial Workbench path. This is an engine-file renderer, not
Valve's original Direct3D material system. Explicit editable model import remains
a separate conversion operation.

## Verification

`native/source1/tests.cc` tests original compressed payload preservation, parser
bounds and malformed inputs, and can read an installed game's model/material
companions directly from its ordered mounts. `tests/blender_native_source_bindings.py`
asserts that native binding never calls Python pixel/model decoders or allocates
preview mesh/image data. A native viewport run is additionally required before
installation; binding tests alone cannot verify GPU rendering.

<!-- Screenshot placeholder: native textured brush and repeated Source props. -->
