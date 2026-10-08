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

## 0.10.31: source tree is the installer

Download `wavelength-v0.10.31-pre.alpha-linux-x86_64.tar.gz`, extract it, and run
`./wavelength-installer` at the source root. It contains the editable Python,
C++, installer, tests and documentation plus the pinned private Python runtime.
There is no separate installer-only source layout. A Git checkout or GitHub's
automatic source archive runs through the same launcher, which downloads and
checksum-checks that runtime on first use (curl, tar and sha256sum required).
Use the release archive when offline; GitHub's automatic source archives cannot
contain generated, untracked runtime binaries.

### Experimental installation

Verified mode remains the default. Menu option **5** enables experimental mode.
CLI equivalent:

```sh
./wavelength-installer install --blender /path/to/Blender.AppImage --addons /path/to/scripts/addons --allow-unverified
```

Read the printed limitations and type `INSTALL EXPERIMENTAL`. For unattended
use, explicitly add `--accept-experimental-risk`. `--force` aliases
`--allow-unverified`; it does not bypass byte, format, backup or transaction checks.

Experimental mode does not require the whole executable SHA-256 in the verified
manifest. The current generator accepts Linux x86-64 ELF payloads containing
**both complete, fingerprinted grid shaders** from the researched Blender source.
It discovers their offsets separately, validates ELF table bounds and unique
anchors, keeps string/binary lengths unchanged, and verifies exact precondition
bytes and the resulting checksum. It also starts the patched payload headlessly
before deployment. A similar version string or matching short marker is insufficient.
Different shader sources are rejected with a compatibility error; force cannot
make an incompatible binary work.

The native component installed by this mode is explicitly the **experimental
embedded GPU grid shader**, not the unfinished C++ per-view state bridge. It
requires scene units NONE and subdivisions 10; the installed add-on configures
those in engine mode. It also colors applicable non-engine views. Native LOD
still hides fine intervals at distant zoom. Startup and structural tests do not
certify all graphics backends, layouts or unknown builds. The receipt records
`installation_mode`, `native_component`, `validation`, and `limitations`; status
reports component checksums, not a claim of renderer certification.

For an AppImage, the installer extracts into temporary storage, patches its
internal Blender executable, and stores the complete runtime in the installer
state directory. The original AppImage path becomes a small launcher to that
managed runtime. The original AppImage is backed up byte-for-byte and restored
by Remove/Recover. ELF bytes are never patched into the AppImage container.
Allow disk space for extraction, original backup and managed runtime. Keep the
state directory at its original location while installed. Backups and runtime
files are retained after removal for inspection; removal restores both host
components and does not discard user-modified files.

This section supersedes the earlier statement that every real installation must
refuse. The verified manifest is still empty. The experimental mode is usable
only when structural compatibility and patched startup checks pass.
