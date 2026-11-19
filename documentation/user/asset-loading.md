# Map asset loading and caching

Source 1 maps load their brush/displacement geometry first. Materials retain
native texture sizes, names and projection data immediately; images and entity
models fill in progressively. You can edit geometry while previews are pending.
A separate background Blender process decodes game assets. Blender datablocks
are created on the main thread in small batches.

Decoded texture pixels and model geometry are cached across Blender sessions.
Repeated props share one mesh and repeated materials share images. Cache keys
include the game installation, mounted source file stamps, VPK CRC/archive
stamps, model companions and requested skin/body. Source units are applied when
creating the mesh. Included VMT files and newly added loose overrides invalidate
cached materials. Cached previews remain private local game data.

The cache is under Blender's user configuration directory:
`wavelength/runtime-assets`. Corrupt entries are discarded and rebuilt. Cached
images are packed into the saved `.blend`, so completed textures survive reopening.
Saving before previews finish also works: pending previews resume on reopen.

Use **System Tree > Reload Asset Previews**, or **F3 > Reload Map Asset Previews**,
to retry unavailable textures/models after fixing the game profile or installing
missing content. This checks game files again without re-importing geometry.
Missing assets do not prevent export of the original material/model references.

Some decompiled entities contain unsupported skin/body values. Their preview
uses the default model variant and records a warning; the original entity keys
remain unchanged for export.

> Screenshot placeholder: editable imported map while previews appear, System
> Tree reload button, and completed textured map.

## Retry scene placeholders after assets become available

Missing scene materials retain their engine texture identity, which can allow
the picker to find an asset even while the scene still shows a placeholder.
Source material recovery now retries those failed bindings on file load and
Source profile changes, rather than requiring an existing successful cache key.
Newly resolved texture dimensions refresh live brush projection once. Existing
working bindings are not rebuilt on every redraw. Use F3 → **Reload Map Asset
Previews** for an explicit retry; it also starts renderer preparation when needed.
