# Wavelength installer

The end-user distribution bundles its own standalone CPython. It does not use
system Python or Blender's embedded Python. The current bundle targets Linux
x86-64; macOS and Windows bundles are not provided yet.

Extract the installer archive and run `./wavelength-installer --help`.

```sh
./wavelength-installer install --blender /path/to/blender --addons /path/to/scripts/addons
./wavelength-installer status
./wavelength-installer remove
./wavelength-installer recover
```

`--state /path/to/receipt-directory` before the subcommand selects a separate
installation record when managing multiple Blender installations. Keep this
folder: it contains the original executable/add-on backup and removal receipt.
Quit Blender before installing/removing and restart it afterward. Removal
restores the original Blender and the add-on that existed before installation,
or removes Wavelength if there was no previous add-on. Blender preference
activation is not changed by this version.

Python owns discovery, verification, patch application, rollback and removal.
C++ owns the native behavior being patched, not the injector. Both native and
Python components are one product: unsupported native builds stop before either
component is installed. The journal supports recovery; external Blender updates,
edited add-on source, or damaged backups stop removal rather than overwriting
those files. Python bytecode caches are ignored when checking for user edits.

## Current limitation

There is still **no verified native grid patch for Blender** in the manifest.
Consequently this distribution runs without system Python, offers status/removal,
and exercises the complete lifecycle in tests, but it will refuse a fresh real
Blender installation. It is an installer-development milestone, not a working
native-grid release. An AppImage requires an exact verified deployment recipe for
its container/payload; no AppImage extraction/repack backend is shipped yet.
The math `.so` prototype is not silently installed as a pretend renderer patch.

## Build and patch contract

`python3 tools/build_installer.py` downloads the exact runtime from
`installer/runtime-lock.json`, checks its SHA-256, preserves its license files,
packages the current add-on and patch manifest, and smoke-tests the launcher.
Runtime binaries are release artifacts, never Git source files.

A trusted release manifest identifies each supported Blender artifact by SHA-256
and references a recipe with exact original bytes and expected output SHA-256.
Only releases containing a renderer-validated recipe may claim native support.
The current recipe backend supports same-length verified byte changes; it does
not synthesize function detours, link arbitrary C++, or increase ELF sections.
Future backend changes must retain this same paired lifecycle and receipt format.
