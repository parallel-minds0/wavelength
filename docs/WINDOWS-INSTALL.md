# Windows native-grid patch: manual verification preview

This preview targets the **official Blender 5.2.2 Windows x64 ZIP executable**.
The installer accepts only the exact original SHA-256 listed in
`patches/native/manifest.json`; other builds need a matching patch.

Windows installation, rendering, and injection have **not** been tested by the
maintainer. Compilation and patch reconstruction are checked. This preview is
published for manual verification; please report the installer output and any
Blender startup or grid problems.

## Install

1. Close Blender.
2. Extract the Windows x86_64 installer ZIP into a writable folder.
3. Open PowerShell in the extracted folder and run:

```powershell
.\wavelength-installer.cmd install --force --blender "C:\path\to\blender.exe" --yes
```

For Blender in `C:\Program Files`, use an Administrator terminal, or use the
portable Blender ZIP in a writable folder. The installer uses its bundled Windows
Python runtime; system Python, a compiler, Wine, and Proton are not required.

The installer stages the patched executable beside the selected Blender and checks
its native API before installation. A failed check leaves the original installation
intact. `--force` does not bypass checksum matching or the startup check.

Reopen **the same Blender executable**, enable Wavelength in Preferences → Add-ons,
and enter its workspace. Check yellow parent grid lines, grey subdivisions, `[` and
`]`, geometry occlusion, and restoration of Blender's regular grid on workspace exit.

## Status, repair, and removal

```powershell
.\wavelength-installer.cmd status
.\wavelength-installer.cmd repair --force --yes
.\wavelength-installer.cmd uninstall --yes
```

The installer retains the original executable and previous add-on for removal and
rollback. Keep its state directory in `%LOCALAPPDATA%\wavelength\install`. Close
Blender before repair or uninstall. External updates are protected rather than
silently overwritten.
