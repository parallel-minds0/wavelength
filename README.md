# Wavelength — 0.19.0-pre.alpha

Blender brush-map authoring for Quake, Half-Life/GoldSrc, and Half-Life 2/Source 1.

The [Windows release](https://github.com/parallel-minds0/wavelength/releases/tag/v0.19.1-pre.alpha) includes a tested native-grid installer for the exact Blender 5.2.3 LTS Release Candidate Windows x64 build `32ede9dba158`. See [installation and validation](docs/WINDOWS-INSTALL.md).

Close Blender, extract the installer, then run:

```powershell
.\wavelength-installer.cmd install --force --require-native --blender "C:\path\to\blender.exe" --yes
```

Enable Wavelength in Preferences and enter its workspace.

This release adds native Scene/Object Properties workflows, cached external texture libraries,
debounced search and working material drops, Windows Steam discovery, and interactive Sun lighting.
See the [editor layout guide](docs/NATIVE-UX.md). Texture caches are generated locally from your game;
game textures and local profiles are not distributed.

Add an engine sun with **Add → Light → Wavelength Sun**, select it to use the heading/elevation rings,
and enable **Object Properties → Sun Direction & Preview → Preview Scene Lighting** for live shadows.
 The installer backs up the original executable and previous add-on; uninstall restores them. It bundles Python, source, and a checksum-bound native patch, not a separate Blender runtime.

```powershell
.\wavelength-installer.cmd status
.\wavelength-installer.cmd repair --force --yes
.\wavelength-installer.cmd uninstall --yes
```

Only exact executable fingerprints listed in `patches/native/manifest.json` qualify. `--force` does not bypass compatibility checks. The previous Windows 5.2.2 preview has a known startup failure and remains historical. Linux users can use the [v0.16.1 installer](https://github.com/parallel-minds0/wavelength/releases/tag/v0.16.1-pre.alpha).

See [release notes](docs/RELEASE-NOTES.md), [installer details](docs/INSTALLER.md), and [Source 1 support](docs/SOURCE1.md).
