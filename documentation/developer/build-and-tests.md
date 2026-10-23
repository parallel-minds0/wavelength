# Build, package and verify

## Verification layers

Run pure Python tests without importing Blender:

```console
python -m unittest discover -s tests -v
```

Run Blender fixtures for scene adapters, operators and geometry. GUI gestures need
a visible temporary Blender process with `--enable-event-simulate`; a background
geometry test alone does not prove keymaps or modal controls work.

```console
blender --background --python tests/blender_cutter_solid.py
blender --background --python tests/blender_cutter_separate_materials.py
blender --enable-event-simulate --python tests/blender_cutter_volume_controls.py -- --confirm-enter --keep-both
```

Blender may return zero even after a Python exception. Inspect fixture PASS/FAIL
markers and tracebacks in the log. Engine integration checks also need the real
game/compiler versions. Do not present mocked compilation as an in-game test.

## Installer and release boundaries

`installer/entry.py` provides source installation. `source_bundle.py` packages a
filtered add-on payload; native compatibility is checksum-bound. `tools/release.py`
validates/packages, and publication is a distinct requested action. Do not bypass
compatibility by renaming a binary or treating `--force` as permission to patch
another build. Refer to [Installer](../INSTALLER.md) for details.

## Documentation checks

```console
python tools/docs.py check
python tools/docs.py build --format all
python tools/docs.py sync
```

The first command checks source links, excerpt markers, screenshot IDs and AST
parsing without Sphinx. Builds use strict warnings and generate both references
and an inventory of pending screenshots. CI builds HTML and PDF and uploads them
as artifacts; it does not publish a website automatically.
