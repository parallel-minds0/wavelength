# Wavelength — 0.13.0-pre.alpha

The grid now requires the wavelength-enabled Blender build. See [native grid usage and build instructions](native/blender/README.md). The authoring tools remain in the Python add-on; grid geometry is rendered inside Blender.

Blender authoring tools for Quake, Half-Life/GoldSrc and Half-Life 2/Source 1 brush mapping, with an experimental native-grid integration workspace.

| Component | Location | Current state |
|---|---|---|
| Blender Python add-on | `addon/wavelength/` | Authoring, entities, textures, MAP/build tools |
| Standalone Python installer | `installer/` | Paired install/remove/recover; verified or explicit experimental mode |
| Native grid | `native/blender/` | Blender C++/RNA state bridge and native grid shader patch; separate Blender build required |
| Build-specific patch recipes | `patches/` | Verified list empty; structurally matched experimental shader generator |

Read the [current-state audit](docs/CURRENT-STATE.md), [Blender source/injection findings](docs/BLENDER-INTEGRATION.md), and [architecture](docs/ARCHITECTURE.md).

## Validate and package

```sh
python3 tools/release.py
```

Runs Python syntax checks, installer/native tests, builds the C++ library, and creates `dist/wavelength-addon-v0.13.0-pre.alpha.zip`. Install that ZIP through Blender's add-on installation UI. No game assets or native host patch are bundled. GitHub Actions runs the same checks and retains the ZIP artifact. Blender UI and game-runtime validation are separate checks.

## Native research and host inspection

```sh
python3 tools/research_blender.py
python3 installer/cli.py inspect /path/to/Blender.AppImage
python3 installer/cli.py probe-renderer /path/to/extracted/blender
python3 installer/cli.py probe-native build/libwavelength_grid.so --step 0.4064 --coordinate 0.8128
```

The research command retrieves SHA-256-locked official Blender source at the verified v5.2.1 commit. AppImage containers and their ELF Blender payloads are different artifacts. Native library loading alone does not modify rendering.

## Publish a version

Update the add-on version tuples and release notes, then run:

```sh
python3 tools/release.py --publish
```

This validates/packages, checks the exact repository root and remote, fetches remote history, stages this workspace, commits changes, creates a new annotated `v<version>-pre.alpha` tag, and atomically pushes branch plus tag. It never force pushes or replaces a tag. If a push is interrupted after local tag creation, inspect local/remote state and retry the atomic Git push; do not recreate the tag. The old tag `v0.10.25-pre.alpha` remains unchanged.

The repository root is this native workspace, not the outer directory containing local games, maps, downloaded compilers, or historical copies.

## Self-contained Linux installer

`python3 tools/build_installer.py` produces an installer with bundled, pinned CPython. See [installer lifecycle and current native support limits](docs/INSTALLER.md). Launch `wavelength-installer` for the terminal menu or use install/remove/status/recover commands. The legacy installer shader experiment is not the new native grid. Use the native Blender package for grid rendering; `--force` still allows installation of the Python authoring tools on unsupported hosts.

## Native grid

Use the separate native Blender package and its `Launch-wavelength` launcher. The former [shader experiment](docs/GRID-PROTOTYPE.md) is historical and should not be applied to this build.

Source 1 Linux/Windows profiles, VMF interchange and compiler wiring are documented in [SOURCE1.md](docs/SOURCE1.md). Displacements and VTF previews remain unsupported.

## One download: source and installer

The Linux release archive contains this editable source tree **and** its private
Python runtime. Run `./wavelength-installer` in its root. A Git checkout or
GitHub-generated source ZIP uses the same launcher, downloading the pinned private
runtime on first use; it needs curl/tar, not system Python. The release archive
includes that runtime for offline use. See [installer instructions](docs/INSTALLER.md).

Menu option 5 or `install --allow-unverified` attempts the experimental native
shader backend, with explicit risk confirmation. `--force` is an alias; neither
option disables structural checks. AppImages are extracted into managed installer
state and their original path becomes a reversible launcher. This is the GPU
shader prototype, not the unfinished C++ per-view bridge.

HL2 now has local VPK/VMT/VTF previews, material search, an entity-output editor,
side-reference remapping, configurable compile arguments and native Tools++ names.
The Linux brush mapping pipeline has been compiled against an installed HL2 game.
See [Source support and limitations](docs/SOURCE1.md); full Hammer parity is not claimed.
