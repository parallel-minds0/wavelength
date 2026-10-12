# v0.15.0-pre.alpha — Windows native-grid patch preview

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
