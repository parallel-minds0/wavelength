# wavelength — 0.50.0-pre.alpha

Blender level authoring for Quake, GoldSrc and Source 1, with editable CS2 / Source 2 VMAP geometry and materials, and Godot 4 mesh/texture export.

Development priorities and known gaps: [TODO](TODO.md). Release scope and known limitations are tracked in the TODO
and [release notes](documentation/RELEASE-NOTES.md).

The [handbook](documentation/index.md) contains a User Guide, Developer Guide and generated
code reference. Author Markdown in `documentation/`; inline source commentary and marked
code excerpts are included directly from the implementation. See
[documentation authoring](documentation/developer/writing-documentation.md) for HTML/PDF
build commands and manual screenshot placeholders.

The [Windows release](https://github.com/parallel-minds0/wavelength/releases/tag/v0.50.0-pre.alpha) includes a tested native-grid installer for the exact Blender 5.2.3 LTS Release Candidate Windows x64 build `32ede9dba158`. See [installation and validation](documentation/WINDOWS-INSTALL.md).

Close Blender, extract the installer, then run:

```powershell
.\wavelength-installer.cmd install --force --require-native --blender "C:\path\to\blender.exe" --yes
```

Enable wavelength in Preferences and enter its workspace.

This release includes inherited profile registration, Geometry Nodes generation, pencil clipping,
CSG and geometry diagnostics, terrain and model workflows, and native file-browser IO.
CS2 supports editable VMAP polygon meshes and installed VMAT/VTEX material browsing;
Godot 4 supports GLB mesh/texture export. Entities, model instances and subdivision
surfaces are outside the Source 2 map implementation. Source 2 Viewer CLI is a
separate material-decoding dependency; see the [CS2 guide](documentation/user/source2-maps.md).
See the [editor layout guide](documentation/NATIVE-UX.md). Texture caches are generated locally from your game;
game textures and local profiles are not distributed.

Add an engine sun with **Add → Light → wavelength Sun**, select it to use the heading/elevation rings,
and enable **Object Properties → Sun Direction & Preview → Preview Scene Lighting** for live shadows.
 The installer backs up the original executable and previous add-on; uninstall restores them. It bundles Python, source, and a checksum-bound native patch, not a separate Blender runtime.

```powershell
.\wavelength-installer.cmd status
.\wavelength-installer.cmd repair --force --yes
.\wavelength-installer.cmd uninstall --yes
```

Only exact executable fingerprints listed in `patches/native/manifest.json` qualify. `--force` does not bypass compatibility checks. The previous Windows 5.2.2 preview has a known startup failure and remains historical. Linux users can use the [v0.16.1 installer](https://github.com/parallel-minds0/wavelength/releases/tag/v0.16.1-pre.alpha).

See [release notes](documentation/RELEASE-NOTES.md), [installer details](documentation/INSTALLER.md), and [Source 1 support](documentation/SOURCE1.md).
