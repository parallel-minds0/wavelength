# Wavelength — 0.14.0-pre.alpha

Blender brush-map authoring for Quake, Half-Life/GoldSrc, and Half-Life 2/Source 1.

## Install the Linux patch

Download and extract the Linux installer from the [release](https://github.com/parallel-minds0/wavelength/releases/tag/v0.14.0-pre.alpha), close Blender, then run:

```sh
./wavelength-installer install --force --blender /path/to/blender --yes
```

Run your existing Blender normally, enable Wavelength in Preferences → Add-ons,
and enter its workspace. The native grid uses yellow parent lines and grey profile
subdivisions. `[` / `]` change spacing; leaving the workspace restores Blender's grid.

The installer includes the source tree, private Python runtime, and native binary
patch. It backs up the selected executable and add-on, validates the patched
executable before installing, and restores originals on uninstall. It does not ship
a separate Blender runtime. A source-only checkout uses the same launcher and
fetches checksum-pinned runtime/patch files when needed.

```sh
./wavelength-installer status
./wavelength-installer repair --force --yes
./wavelength-installer uninstall --yes
```

**Compatibility:** this experimental release supports the exact Linux x86_64 Blender
5.2.2 binary in `patches/native/manifest.json`, tested on the development host.
`--force` does not bypass binary compatibility checks and cannot turn an arbitrary
Blender executable into a supported target. Windows runtime/bootstrap and cross-compiler
support are groundwork; Windows native-grid injection is not part of this Linux milestone.

See [release notes](docs/RELEASE-NOTES.md), [installer details](docs/INSTALLER.md),
[native patch source](native/blender/README.md), and [Source 1 support](docs/SOURCE1.md).

## Development

`python3 tools/release.py` validates source, runs tests, builds the standalone C ABI
helper, and packages the add-on. `python3 tools/build_installer.py` creates the Linux
installer. Custom Blender reference builds remain internal development artifacts.
