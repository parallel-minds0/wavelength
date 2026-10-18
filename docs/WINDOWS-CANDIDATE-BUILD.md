# v0.16.2-pre.alpha — tested Windows native-grid installer

Builds and installs Wavelength's native grid for the exact Blender 5.2.3 LTS Release Candidate Windows x64 build `32ede9dba158` (original executable SHA-256 `19e60200c51e981aa48a515ffc22c46d9192ea0538e249b2891394a425bd855b`). Other Blender executables require their own matching patch.

- Compiles the native Blender renderer with MSVC and reuses the candidate's existing oneAPI AOT kernel DLL, fixing the earlier missing JIT DLL startup failure.
- Fixes Windows installer file flushing and loose Source material path enumeration.
- Includes the Python add-on, editable source, native binary patch, and pinned private Python runtime. No separate Blender runtime is distributed.
- Verified native RNA startup, real OpenGL grid rendering on AMD Radeon(TM) Graphics, yellow parent lines, grey subdivisions, orthographic/perspective occlusion, workspace restoration, installed add-on loading, and brush creation.
- Verified a real install/uninstall/reinstall cycle; uninstall restored the original executable byte-for-byte. Original backups and receipts are retained by the installer.

Close Blender, extract the Windows installer ZIP, and run:

```powershell
.\wavelength-installer.cmd install --force --require-native --blender "C:\path\to\blender.exe" --yes
```

To keep the add-on inside that Blender folder, additionally pass `--addons "C:\path\to\5.2\scripts\addons_core"`. Otherwise the installer uses Blender's normal user add-on directory. Enable Wavelength in Preferences and enter its workspace.

The previous Windows 5.2.2 preview remains available in historical releases; this release does not certify or repair that build. Linux retains its existing source and compatibility entry; no newly tested Linux installer or Vulkan certification is claimed here.
