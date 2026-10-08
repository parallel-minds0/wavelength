# Wavelength

> **This is the pre-alpha testing release. Don't expect usable functionality; it does the bare minimum.**

Wavelength is an experimental Blender add-on for brush-based level authoring. The current pre-alpha focuses on Quake and GoldSrc / Half-Life workflows. Interfaces, project formats, behavior, and repository structure can change while the project is being tested.

## Repository layout

- `__init__.py` — Blender add-on entry point; delegates to `source/`.
- `source/` — Wavelength Blender add-on implementation.
- `environment/` — versioned editor/test resources: model references, test maps, and SVG/PNG entity references.
- `documentation/` — Markdown documentation intended to remain suitable for later HTML/PDF generation.
- `dev/` — local scratch/generated development files; ignored by Git.
- `third-party/` — redistributable third-party source/binaries shipped with Wavelength.
- `LICENSE` — project license.

## Pre-alpha expectations

Wavelength v0.10.25-pre.alpha is not production-ready. Features may be incomplete or broken, engine/toolchain setups still require manual configuration, and compatibility is not guaranteed. Test with disposable project files and keep backups.

## Development

The Blender add-on package lives in `source/`. Repository-relative editor assets are resolved from `environment/`. Do not commit proprietary game assets or third-party binaries merely because Wavelength can use them locally.

See [`documentation/`](documentation/) for architecture, development, and testing notes.


## Self-contained installation

The repository root is the Blender add-on package. Zip the `wavelength/` directory as-is and install that ZIP in Blender. The ZIP is expected to include `source/`, `environment/`, `documentation/`, and any redistributable components under `third-party/`.

Runtime paths must resolve relative to the installed Wavelength package. A separate checkout, absolute developer path, or separately installed compiler is not required when the corresponding redistributable component is bundled.

`dev/` is local scratch space and is not required by Wavelength at runtime.
