# v0.12.0-pre.alpha — installer lifecycle

- Replacement is the default for an existing install; versions can be upgraded, downgraded or reinstalled while retaining the original backup chain. Interactive installs offer replace, side-by-side or cancel.
- Side-by-side instances have separate add-ons, receipts and Blender executable copies. Only one wavelength add-on should be enabled in Blender at a time. A copy that cannot be created requires `--force` for Python-only fallback; `--require-native` still fails.
- `uninstall` (`remove` alias) now removes adopted native shader patches too. Exact original bytes are restored from an intact original backup; adopted patches are structurally reverted to pristine shader behavior, without claiming byte identity.
- `repair` restores add-on files with edit backups, repairs recognized native states, and rolls back interrupted transactions. Unknown external binary replacements or corrupt receipts require `--force`; corrupt receipts also require explicit target paths.
- Managed runtimes with intact full inventories are removed. User backups/stale archives are preserved outside the removed instance. Unknown or changed runtimes are retained and reported.
- Validation: 129 automated tests passed. New native lifecycle checks use synthetic ELF fixtures with startup probes mocked; this release does not certify compatibility with any real Blender build. Both deliberate mutations (skipping replacement and skipping structural revert) were caught by the new tests.

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

# v0.11.0-pre.alpha

Adds a dedicated persistent Wavelength workspace, independent world-aligned map-unit highlights preserving Blender's native grid, scoped toggles, transactional engine-grid object movement and move gizmos. Stops registering the old settle-time transform correction timer.

Adds native Asset Browser publishing for game materials, entity templates and labelled model/sound/effect proxies; user profile CRUD/import/export in user configuration; persistent editable stairs, arches and 20/80-face convex spheres; independent private Pro source synchronization with drift checks. See MILESTONES-1-2.md for usage, validation and explicit limits.

# v0.10.33-pre.alpha

Fix Source compiler argument defaults when switching engine profiles. Empty values saved by earlier versions also recover as empty argument lists. Retains the v0.10.32 gallery, scrollbar, grid-setting restoration, and consistent Source map filenames. Custom HL2 map gameplay remains unverified and unresolved.

# 0.10.32-pre.alpha

- Source materials use the shared thumbnail gallery; gallery rows and native scrollbar now share the same height (applies to WAD browsing too).
- Reapply engine grid units/subdivisions after loading scenes and creating viewports, correcting stale saved settings in the experimental shader path.
- Discover HL2's combined game directory; migrate launch directory for older profiles. Explicit singleplayer mode for Tools++ VBSP.
- Preserve the final Source map basename throughout compilation and launching so embedded asset paths are not renamed out from under the BSP.
- Source runtime investigation remains unresolved: stock map reached gameplay, custom-map tests exited before the gameplay marker. Do not interpret a successful compile or Spawn Server as a successful load.
- Preserve Source compiler arguments in saved project files.

# 0.10.31-pre.alpha

- Source-tree distribution doubles as the installer; release archive includes private Python, source checkouts bootstrap the same pinned runtime.
- Explicit experimental/force mode bypasses the verified whole-file allowlist while retaining structural shader fingerprints, exact byte/hash validation, startup checks, backups and recovery.
- Experimental AppImage deployment extracts and patches the payload, installs a reversible launcher, and records prototype limitations in receipts. C++ per-view renderer bridge remains unfinished.
- HL2 VPK/VMT/VTF texture previews and searchable material names, real texture dimensions, entity output editing, side-reference remapping and Tools++ compiler support.
- Real installed-game Blender workflow and native BSP/VIS/RAD compilation tested; Steam HL2 spawned the generated map.
- Repairs the missing live-texture state helper; verified projection follows brush movement.
- Full Source 1/Hammer parity is not complete: see SOURCE1.md for remaining displacement/model/instance and advanced rendering work.

# 0.10.30-pre.alpha

- Native grid experiment highlights only the exact selected spacing; other levels retain native gray/emphasis colors.
- Adds HL2 Source 1 Linux/Windows profiles, VMF brush/entity import/export, Source material-name assignment and VBSP/VVIS/VRAD build orchestration.
- Adds BSP20 header/lump validation and Steam App ID 220 launch configuration.
- Tested format round-trips and Blender integration, including fake-compiler orchestration. Real HL2 compilation/runtime validation remains pending installed SDK tools.
- VTF/VPK previews, displacements and a full Source I/O editor are not implemented.

# 0.10.29-pre.alpha

- Adds an exact-build native shader experiment and interactive Wavelength grid demo.
- Yellow snap-interval lines rendered in a copied Blender; step changes and top/front/right/perspective capture scripts available.
- Original Blender untouched; generated recipe deliberately unverified. Production native installer support and C++ state bridge remain unfinished.

# 0.10.28-pre.alpha

- Bundled CPython Linux installer builder, isolated launcher and terminal menu.
- Paired native/Python install, remove and recovery with receipts, exact hashes and original backups.
- Transaction tests cover failures, pre-existing add-ons, user edits and external Blender updates.
- Native renderer patch and AppImage deployment backend remain unavailable; real installations refuse before modifying either component.

# 0.10.27-pre.alpha

- Corrects an inherited ignore rule that excluded the Python `source/build/` package from Git.
- Release validation now requires all three build modules and refuses ignored Python source.
- Retains the first published tag unchanged; this is the complete source distribution.

# 0.10.26-pre.alpha

- Consolidates the latest 0.10.25 add-on edits and native installer workspace into one repository, retaining previous Git history and tags.
- Includes current native-grid/text indicator, GoldSrc profile/catalog, origin, texture caching, and UI source changes from the local working baseline.
- Adds validation, ZIP packaging, annotated tag/commit/atomic-push automation and GitHub Actions validation/artifact packaging.
- Identifies AppImage containers separately from renderer payloads.
- Pins official Blender 5.2.1 source and documents CPU/shader/RNA integration points and the missing native renderer bridge.

The C++ library is a grid-math prototype. No native renderer hook, supported binary patch, or AppImage host replacement is released in this version.
