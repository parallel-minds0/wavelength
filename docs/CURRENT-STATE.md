# v0.11.3-pre.alpha — playable HL2 validation milestone

- Adds a sealed, textured Source room with editable stairs, arch and 80-face sphere, plus an opt-in Blender build regression.
- Rejects renamed BSPs whose embedded default cubemaps still refer to a different map name. Rebuild instead of renaming the compiled file.
- Source build filenames now follow the same lowercase rule as launching.
- Verified real Blender export and VBSP/VVIS/VRAD compilation, followed by visible HL2 gameplay and client sign-on. Local .blend, BSP and screenshot are in maps/hl2-playable outside the source repository.
- Automated movement/collision verification, Build & Play, and launch monitoring were stopped at the user's request and are not included. The legacy custom-map failure's full cause is not established; freshly rebuilt test geometry loads successfully.

# v0.11.2-pre.alpha — installer force mode

- `install --force` now installs Python even when native preparation or writing fails. `--require-native` restores strict rollback.
- Structural shader classification recognizes current and known legacy patches, including shared shader strings. Existing patches are adopted without rewriting.
- Reinstalls retain original backups; stale state is archived. Healthy recovery is a no-op. Removal preserves adopted patches and external edits.
- Added local discovery, read-only `diagnose`, verbose summaries, and a lightweight source ZIP with the same installer launcher.
- Verified isolated install/reinstall/removal and startup on the actual already-patched Blender 5.2.2; binary unchanged. This does not certify native rendering or fresh AppImage patching.

See [installer instructions](INSTALLER.md). Earlier milestone notes below are historical.

# Current implementation — 2026-10-09

The new milestone audit in [MILESTONES-1-2.md](MILESTONES-1-2.md) supersedes the historical baseline below. Native shader patching is no longer needed for the workspace grid; Blender 5.2.2 was used for verification.

# Current baseline — 2026-10-08

This audit supersedes the old 0.2.x chat context. The imported baseline is
0.10.25; 0.10.26-pre.alpha consolidates the native workspace, current add-on
changes, repeatable checks/publication, and source research. 0.10.27-pre.alpha additionally fixes an inherited ignore rule that omitted the
Python build package from Git and adds a publication check. It does not ship
a working native renderer hook.

## Layout and ownership

- `addon/wavelength/__init__.py`: installable Python add-on entry point.
- `addon/wavelength/source/`: actual editor modules; this is no longer the old
  `wavelength/addon/wavelength/ui.py` layout.
- `installer/`: standalone Python CLI, compiler/runtime discovery, C++ build,
  ctypes ABI bridge, executable inspection, source/renderer probes, offline
  same-length binary-replacement recipe engine.
- `native/`: C++17 math predicate and C ABI version 1. No Blender headers,
  renderer registration, code redirection, or shader state transport.
- `patches/manifest.json`: zero supported executable builds.
- `patches/blender-source-lock.json`: pinned official research files, NOT a
  binary compatibility manifest.
- `tools/`: source research, validation, packaging, commit/tag/push automation.

The outer workspace also contains game installations/toolchains, maps, historical
`old_wavelength`, `old-dont-detele`, web work, and planning documents. These are
not release inputs. Old 0.2.5 unfinished edits are not reapplied.

## Add-on changes found

- Engine profiles now include Blender/no-engine, Quake, generic GoldSrc,
  Linux GoldSrc and Linux/Steam Half-Life. Engine unit conversion is centralized
  in `profiles.py` (0.0254 meters per Quake/GoldSrc unit).
- Grid uses Blender's native overlay, not the old Python-drawn finite grid.
  There is a yellow **text indicator**, not selective yellow grid lines.
- Modal click/drag primitive tools cover cube, cylinder, cone, sphere and arch;
  resize gizmos and origin-to-geometry logic have their own modules.
- `transform_sync.py` snaps native object transforms after three stable ticks
  at 0.08-second intervals. This is settle-time correction, not native continuous
  transform snapping. Rotated non-uniform scaling deserves further testing.
- System Tree classifies engine content independently of artist Collections.
- Entities have FGD/property support, searchable catalogs, an Asset Browser,
  model-reference helpers, icons, brush-group add/remove/to-world operations,
  spawnflags/choices, targets, worldspawn, paths, and HL1 authoring helpers.
- Texture previews have WAD browsing, generated material caching, face mapping,
  fit/capture/copy/paste, and live projection polling. `editor._live_tick` skips
  active Edit Mode geometry and finalizes on return to Object Mode; this is not
  evidence of continuous reprojection during a vertex drag.
- Build/publish/launch code moved to `source/build/` plus UI operators. Previous
  custom destination and compiler diagnostics exist. No new game-runtime claim
  was established in this audit.

## Installer/native limitations confirmed by reading code

The installer installs only into a fresh add-on directory. Overwrite/transactional
upgrade is not implemented. Compiler discovery prefers staged tools; those staging
folders are empty. MSVC is not supported by the direct build adapter. The recipe
engine produces a new file and validates input/output SHA-256 and exact bytes;
it cannot insert arbitrary C++ or enlarge an ELF. `verified: true` is a local
recipe assertion, not a signature or independently established compatibility.

AppImage inspection now explicitly distinguishes the runtime container from its
Blender payload; the container cannot qualify as a supported renderer executable.
No AppImage extraction/repack/deployment/rollback orchestration or native GUI
installer is implemented. Do not label the foundation a working injector.

## Git

The canonical repository root is this `wavelength/` native workspace. It retains
history from the former nested add-on repository (remote master at 5be4913).
The nested Git metadata was preserved outside release inputs in the outer
workspace's `.local/addon-git-before-native-workspace`. The unexpected ancestor
repository rooted at the user's home was left untouched. Publication checks the
exact Git root and remote before staging, commits, creates a new annotated
prerelease tag and atomically pushes branch plus tag without force.

## 0.10.28 installer lifecycle update

The installer now bundles pinned standalone CPython through tools/build_installer.py.
Python applies the native patch and manages both components with a single receipt.
C++ implements the patched behavior, not injection. Install/remove/recover have
transaction tests and restore backups; edited files and unknown target hashes
are refused. Current recipes are still empty: no real native renderer installation
or AppImage backend is claimed. See INSTALLER.md for the accurate current scope.

## 0.10.31 update

Read INSTALLER.md and SOURCE1.md's 0.10.31 sections before the older audit above.
Experimental shader/AppImage installation now exists, with explicit confirmation,
structural generation and rollback. Source tree and installer share one layout.
HL2 game asset previews, I/O editing and actual native map compilation now work.
The C++ bridge and full Hammer feature parity are still incomplete.
