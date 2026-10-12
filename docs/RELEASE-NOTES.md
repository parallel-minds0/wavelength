# v0.14.0-pre.alpha — installable Linux native-grid patch

The installer now applies a checksum-bound binary patch to the selected Blender
executable and installs the Python add-on in one transaction. Users keep launching
their existing Blender. This release does not distribute a Blender runtime.

## Install on Linux x86_64

Close Blender, extract the Linux installer archive, open a terminal in that folder:

```sh
./wavelength-installer install --force --blender /home/moe/Applications/blender-5.2.2-linux-x64/blender --yes
```

Then launch that same Blender executable. Enable **Wavelength** in Preferences →
Add-ons if needed, and use the Wavelength workspace. `[` / `]` adjust grid spacing.
Yellow lines are the selected parent spacing; grey lines are its subdivisions.
Leaving Wavelength restores Blender's regular grid.

```sh
./wavelength-installer status
./wavelength-installer repair --force --yes
./wavelength-installer uninstall --yes
```

The original executable and previous add-on are backed up. Uninstall restores them;
external modifications are protected. `--force` permits experimental installation
and reconciles previous installer state, but never bypasses patch checksums or the
native startup check. Unsupported binaries fail before installing the add-on.

## Scope

This release targets the exact Linux Blender 5.2.2 executable identified in
`patches/native/manifest.json`. This initial payload is experimental and built for
the tested Linux host; other distributions may fail its startup compatibility check.
Windows installer groundwork and cross-compilation tooling are included as source.
Windows native-grid injection is not provided or claimed as working in this Linux milestone.

The archive contains the source tree, the native binary difference, and a pinned
private Python runtime. A source-only checkout downloads the same checksum-pinned
patch on demand. Internal Blender builds are development tools only.
