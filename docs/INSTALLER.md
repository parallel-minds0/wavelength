# wavelength installer

Download and extract `wavelength-v0.12.0-pre.alpha-linux-x86_64.tar.gz`, then run
`./wavelength-installer`. The archive contains the editable source tree and a
pinned private Python runtime. The smaller `wavelength-v0.12.0-pre.alpha-source.zip`
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

## Install, replace, and select instances

```sh
./wavelength-installer install --force --existing replace --yes
./wavelength-installer install --force --existing side-by-side --yes
./wavelength-installer status --instance default
./wavelength-installer status --instance INSTANCE_ID
```

The existing-install policy is `replace`, `side-by-side`, or `abort`. Without a
policy, interactive installs ask; non-interactive installs replace. `--yes`
suppresses prompts but does not accept experimental risk. Use the explicit
`--accept-experimental-risk` flag with `--allow-unverified` for that mode.

Replacement preserves pristine backups across upgrades, downgrades and
reinstalls. Edited add-ons, damaged backups or externally replaced executables
stop ordinary replacement. `--force` retains edits under `backups` and archives
stale state under `stale` before proceeding.

Side-by-side creates a separate state subdirectory, add-on directory and Blender
executable copy next to the original. It does not change the first instance's
executable. Use the new executable path printed in the result. Enable only one
wavelength add-on at a time: the registered Blender classes would otherwise clash.
If an independent copy cannot be made (including AppImage/launcher layouts), use
`--force` for Python-only fallback. `--require-native` never permits that fallback.

When several instances exist, specify `--instance default` or the generated ID.
Interactive commands can ask for a selection; non-interactive commands list IDs
and exit 3 without guessing. `--state /path/to/state`, placed before the command,
selects a different installation-state root.

## Repair, recover, and uninstall

```sh
./wavelength-installer repair --instance default
./wavelength-installer uninstall --instance default
./wavelength-installer remove --instance default
./wavelength-installer recover --instance default
./wavelength-installer diagnose --blender /path/to/blender
```

Repair leaves healthy installs unchanged. Missing or edited add-on files are
restored; edits are backed up. Recognized pristine, partial and legacy native
shader states are repaired. If experimental startup validation fails, repair
reverts identifiable shader patches fully and reports native unavailable;
`--require-native` instead fails without deploying that fallback. Unknown external
binary replacements require `--force`. For a corrupt receipt, give repair
`--force --blender /path/to/blender --addons /path/to/addons` to quarantine state
and reinstall. For a relocated executable, give its new path explicitly.

Recover rolls back interrupted installation/removal. It never uninstalls a healthy
installed instance. Diagnose is read-only; it does not launch Blender.

Uninstall now removes adopted native patches as well as installer-owned patches.
An intact original backup permits byte-exact restoration. Without a pristine
backup, recognized shaders are structurally reverted and checked as pristine;
this restores original behavior but may retain different whitespace. Missing
Blender executables stay missing, and the result reports the limitation.

Edited add-ons stop uninstall unless `--force` is supplied, in which case edits
are backed up. Managed copies and runtimes are removed after successful
restoration. Runtimes with unknown/changed inventories and foreign files are
retained and reported. Edit backups and stale archives are moved into an adjacent
`*-uninstalled-*` archive instead of being discarded. `--keep-state` retains the
final receipt; otherwise the receipt and empty instance state directory are
removed. Repeated uninstall is safe.

Run the launcher without arguments for the seven-entry menu: Install, Uninstall,
Repair, Status, Recover, Experimental install, Force install. Commands accept
`--verbose` for additional diagnostic details.

Exit codes: **0** success, **1** general failure, **2** command usage error,
**3** inconsistent/interrupted/ambiguous state, **4** unavailable or required native
support. New lifecycle tests use synthetic ELF fixtures with a mocked startup
probe; they do not certify a real Blender build.
