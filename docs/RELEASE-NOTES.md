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
