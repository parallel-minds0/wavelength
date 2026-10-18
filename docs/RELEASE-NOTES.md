# v0.19.1-pre.alpha — Garry's Mod profile

- Add a dedicated Windows Garry's Mod Source profile with Steam App ID 4000.
- Discover GarrysMod/garrysmod, Garry's Mod's win64 VBSP/VVIS/VRAD tools and garrysmod.fgd without falling back to HL2 setup.
- Verified the installed game, all three compiler startup banners, 564 FGD definitions and 6,016 indexed materials. The private cache contains 5,516 supported previews and reports 500 unsupported materials.

# v0.19.0-pre.alpha — Windows authoring and interactive sun

Includes the following development milestones since v0.16.2: Blender-native UI,
external texture libraries, debounced search and material drops, Windows Steam
discovery, and interactive sun lighting. The native Windows patch is unchanged
and remains restricted to the exact Blender 5.2.3 candidate executable below.

- Add a real Blender Sun preview to light_environment entities, including existing entities and imported maps. Preserve the entity identity and hierarchy.
- Add viewport heading/elevation rings and a direction arrow, plus Object Properties controls for direction, color, preview strength and sun size.
- Synchronize native light edits and engine pitch/angles/_light fields in both directions; keep the loaded inspector fields current.
- Add Shift+A → Light → Wavelength Sun and Preview Scene Lighting for Material Preview with scene lights/world.
- Export exactly one engine entity; exclude generated light previews. Restore on load/undo and remove orphan previews when the entity is deleted.
- Brightness uses an editor preview conversion (engine brightness / 100), not a reproduction of VRAD's baked lighting. Ambient/HDR compilation fields remain intact.
- Verified real-time viewport shadows, two-way direction/color/strength, export, deletion and reload; 152 unit tests pass.

# v0.18.2-pre.alpha — Windows Steam discovery (local, unreleased)

- Honor a configured Steam executable and locate Windows Steam through its registry/install folders, without requiring PATH edits.
- Preserve Steam App ID and map/game launch arguments. Verified both configured and registry discovery without starting Steam or the game.

# v0.18.1-pre.alpha — native search and material drops (local, unreleased)

- Debounce texture search by 250 ms in the Wavelength native Asset Browser; other browsers keep their existing header behavior.
- Append editable preview materials rather than importing read-only packed placeholders. Repair linked placeholders when assigned.
- Realize dropped shaders on ordinary meshes, including unselected drop targets. Preserve existing UV coordinates and provide mapping for UV-less meshes.
- Synchronize face records and engine UVs on a brush's first material drop.
- Verify real dependency-graph updates, linked-material repair, displayed brick pixels in Material Preview, and 13 typed characters producing one native filter update.

# v0.18.0-pre.alpha — external texture libraries (local, unreleased)

- Build preview-only texture assets in a separate, low-priority Blender worker, saved in bounded external .blend shards.
- Browse cached assets in Blender's native external Asset Browser; importing/applying a texture creates only the selected material in the map.
- Cache the index and previews across sessions. Worker-side source fingerprints detect archive/WAD/loose-material changes; explicit Reload rechecks them.
- Remove legacy gallery decoding from profile refresh and defer entity templates until the entity section is requested.
- Stop the worker monitor after completion. Dependency handlers inspect changed objects instead of scanning all brushes on material events.
- Migrate unused generated in-map thumbnail materials in bounded batches; preserve assigned, realized and customized materials.
- Full HL2 check: 6,885 indexed, 6,519 previews, 366 unsupported; ~74 seconds first cache generation in worker, ~2.2 seconds warm validation, ~0.13 seconds profile activation. No map material growth while browsing.

# v0.17.0-pre.alpha — local Blender-native UI (unreleased)

- Replace the giant sidebar with Scene/Object Properties, contextual geometry and face actions, and a compact workspace tool header.
- Keep profile management and maintenance in a small Wavelength menu; expose map grid controls through viewport popovers.
- Use the native Outliner for hierarchy, native File import/export menus, and active tool settings for drawing parameters.
- Follow entity selection in Object Properties, preserve brush-entity membership tools, and retain searchable operators.
- Keep face mapping in the Edit Mode Item sidebar, and show build progress, errors and validation targets in Scene Properties.
- Verify real Blender UI drawing, workspace isolation, inspector binding and repeated add-on registration; fix operator cleanup on reload.

# v0.16.4-pre.alpha — local Asset Browser display fix (unreleased)

- Select all catalogs with Blender's empty catalog ID and ALL visibility. The nil UUID selected an empty catalog and hid loaded materials.
- Retry editor configuration until its Asset Browser parameters exist; preserve user catalog/search choices after initial configuration.
- Report ready and skipped material counts separately instead of presenting unsupported materials as unfinished loading.
- Apply saved profile fields as one transaction, then refresh textures once.
- Verified real visible/selectable material entries and texture pixels in the native Asset Browser, plus profile refresh and progress regressions.

# v0.16.3-pre.alpha — local texture-loading fix (unreleased)

- Time-budgeted thumbnail loading with cached lookups and constant-time queues.
- Thumbnail assets do not retain default shader nodes; applying a material builds its complete shader on demand.
- VTF previews remain bounded for single-mip textures, with decoding restricted to sampled pixels/blocks.
- Old oversized previews regenerate, and unused generated shader graphs are cleaned in bounded batches. Assigned, realized and customized shaders are preserved.
- Checks cover single-mip RGBA/DXT previews, cleanup safety, full installed HL2 material loading and UI timer progress.

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


# v0.16.1-pre.alpha â€” current authoring tools and Blender diagnostics

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

# v0.15.0-pre.alpha â€” Windows native-grid patch preview (historical)

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
