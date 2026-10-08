# Wavelength — 0.10.27-pre.alpha

Blender authoring tools for Quake and Half-Life/GoldSrc, with an experimental native-grid integration workspace.

| Component | Location | Current state |
|---|---|---|
| Blender Python add-on | `addon/wavelength/` | Authoring, entities, textures, MAP/build tools |
| Standalone Python installer | `installer/` | Discovery, build, inspection, fresh add-on install, guarded offline patch recipes |
| C++17 library | `native/` | Loadable grid-line math prototype; **no Blender renderer hook yet** |
| Build-specific patch recipes | `patches/` | No supported Blender binaries |

Read the [current-state audit](docs/CURRENT-STATE.md), [Blender source/injection findings](docs/BLENDER-INTEGRATION.md), and [architecture](docs/ARCHITECTURE.md).

## Validate and package

```sh
python3 tools/release.py
```

Runs Python syntax checks, installer/native tests, builds the C++ library, and creates `dist/wavelength-addon-v0.10.27-pre.alpha.zip`. Install that ZIP through Blender's add-on installation UI. No game assets or native host patch are bundled. GitHub Actions runs the same checks and retains the ZIP artifact. Blender UI and game-runtime validation are separate checks.

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
