# v0.16.2-pre.alpha � tested Windows native-grid installer

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


# v0.16.1-pre.alpha — current authoring tools and Blender diagnostics

- Incorporates v0.16.0 authoring updates: brush creation, editable primitives,
  asset and entity browsing, texture handling, and transform synchronization.
- Blender Diagnostics includes persistent rotating logs and View, Copy, Clear,
  and Export controls with error references and tracebacks.
- Updates the Linux native grid's parent-line color and opacity from v0.16.0.
- Corrects the Linux patch download URL to match its updated checksum.
- Synchronizes shared source and the Windows launcher into the private Pro tree.

Linux x86_64 installer and add-on/source downloads are supplied. This release
does not rebuild Blender. The Windows v0.15 preview has a reported missing
`cycles_kernel_oneapi_jit.dll` failure during startup verification and remains
blocked; no new Windows installer is supplied. The Windows installer executable
fingerprint also differs from the supported ZIP fingerprint. Do not bypass checks.

Earlier validation claims below describe their respective historical releases.

# v0.15.0-pre.alpha — Windows native-grid patch preview (historical)

The Windows package now includes a native Blender grid binary patch, not just the
standalone grid-math helper. It bundles Windows Python and installs through
`wavelength-installer.cmd`. Linux retains the tested v0.14 native patch.

**Windows is published for manual verification:** the C++ code is compiled and
binary patch reconstruction is checked, but Windows installation, injection, and
rendering have not been tested. No Wine/Proton or Windows Blender runtime tests
were run by the maintainer.

## Windows x86_64

Target: official **Blender 5.2.2 Windows x64 ZIP executable**, with the exact hash
recorded in `patches/native/manifest.json`. Close Blender, extract the Windows
installer ZIP, and run PowerShell in the extracted folder:

```powershell
.\wavelength-installer.cmd install --force --blender "C:\path\to\blender.exe" --yes
```

Use an Administrator terminal for a Program Files target, or install into a writable
portable Blender folder. Reopen the same executable, enable Wavelength, and enter
its workspace. Follow [the Windows verification guide](https://github.com/parallel-minds0/wavelength/blob/v0.15.0-pre.alpha/docs/WINDOWS-INSTALL.md) and report errors.

```powershell
.\wavelength-installer.cmd status
.\wavelength-installer.cmd repair --force --yes
.\wavelength-installer.cmd uninstall --yes
```

## Linux x86_64

```sh
./wavelength-installer install --force --blender /home/moe/Applications/blender-5.2.2-linux-x64/blender --yes
```

The Linux native payload is unchanged from v0.14.0, where real install, repair,
byte-exact uninstall, native grid spacing, occlusion, and workspace restoration passed.

## Installation behavior

Both packages contain source, a private platform-specific Python runtime, and native
binary differences. No replacement Blender distribution, system Python, or compiler
is required. The installer checks input/output hashes and probes native API startup
before committing installation. It retains the original executable for rollback and
uninstall. `--force` does not bypass binary matching or the startup check.

Only listed executable fingerprints are supported. Other Blender versions, modified
executables, ARM64, and macOS need separate patches. The read-only `diagnose` command
now recognizes native patch fingerprints on both platforms.
