# wavelength installer

Download and extract `wavelength-v0.11.2-pre.alpha-linux-x86_64.tar.gz`, then run
`./wavelength-installer`. The archive contains the editable source tree and a
pinned private Python runtime. The smaller `wavelength-v0.11.2-pre.alpha-source.zip`
contains the same source and installer; it downloads and verifies that runtime on
first use (requires curl and network access). System Python is not required.
Linux x86-64 is currently the supported installer platform.

## Install on an unknown or already-patched Blender

Quit Blender, then run:

```sh
./wavelength-installer install --force
```

Local discovery prefers the previous installation and then local Blender builds.
If discovery is ambiguous, supply the paths explicitly:

```sh
./wavelength-installer install --force \
  --blender /home/moe/Applications/blender-5.2.2-linux-x64/blender \
  --addons /home/moe/.config/blender/5.2/scripts/addons
```

Restart Blender and enable wavelength in Preferences → Add-ons. Existing
activation preferences are preserved. The current Python workspace grid works
without the experimental native shader patch.

`--force` bypasses the verified-build allowlist and attempts native preparation.
It recognizes original, current, and known legacy shader blocks. Already-current
patches are kept without rewriting the executable. Unknown layouts, startup
failures, missing executables (with explicit target paths), and native write
failures allow a Python-only installation, with native support reported as
unavailable. Add-on permission/checksum errors still fail the installation.

`--force` no longer aliases `--allow-unverified` and requires no typed risk
confirmation. Add `--require-native` to roll back if native support is unavailable.
The older `--allow-unverified --accept-experimental-risk` mode still requires both
components. A plain install requires a verified recipe for the exact binary;
there are currently no certified builds in the allowlist.

The native component remains an experimental embedded-shader patch, not a C++
renderer bridge. Structural compatibility and successful startup do not certify
rendering. The legacy native yellow overlay affects all native 3D grids and still
uses native level of detail. AppImages are extracted to prepare and probe their
payload; when changed, a reversible launcher uses the retained extracted runtime.

## Diagnose, recover, and remove

```sh
./wavelength-installer diagnose --blender /path/to/blender
./wavelength-installer status
./wavelength-installer recover
./wavelength-installer remove
```

`diagnose` reads bytes without modifying or running Blender. For AppImages it
reports that payload extraction is required; install performs extraction and
startup validation. `recover` leaves an installed transaction intact and rolls
back a prepared transaction. Status reports external changes for inspection.

Use `--state /path/to/state` **before** the subcommand to manage another
installation record. Keep this directory: it contains the journal and backups.
Force installation archives stale/corrupt/relocated/replaced state under
`state/stale/<timestamp>-<reason>/`. Earlier target installations remain intact
when switching targets; their archived receipt can be managed separately with
`--state`. Repeated installs preserve the original executable/add-on backup chain.
Edited add-ons are backed up before a forced replacement. Removal refuses to
discard later user edits or overwrite an external Blender update. Missing Blender
executables are not recreated by forced-install removal.

A preexisting patch that this installer did not apply is **adopted**. Removal
leaves that executable unchanged. Receipts distinguish `native_state`,
`native_changed` (this transaction), `native_ownership` (`owned`, `adopted`, `none`),
and `installation_mode='forced'`. Original backups are retained after removal.
Never delete installer state while an owned patch still needs removal.

Human summaries go to stderr; structured JSON goes to stdout. `-v` / `--verbose`
works before or after subcommands. Interactive option 6 selects forced install.
Exit codes: **0** success (including forced Python-only installation), **1** general
failure, **3** state/recovery problem, **4** required native support unavailable.

## Validation and build

`python3 -m unittest discover -s tests` covers synthetic shader states, including
both stages in a shared string, bounded replacement, transactions, fallback,
rollback, discovery, and CLI behavior. On the available Blender 5.2.2 executable,
structural diagnosis and two startup probes succeeded. An isolated force install,
reinstall, and removal adopted the existing patch and preserved the executable's
SHA-256 throughout. Fresh native patch rendering and AppImage deployment were not
validated on a real installation in this release.

`python3 tools/build_installer.py` checks the pinned runtime SHA-256, builds the
full source/runtime archive and lightweight source ZIP, and smoke-tests the
bundled launcher. Binary recipes retain exact input/output hashes, equal-length
spans, and non-overlap checks. Force mode does not disable these checks.
