# 0.10.26-pre.alpha

- Consolidates the latest 0.10.25 add-on edits and native installer workspace into one repository, retaining previous Git history and tags.
- Includes current native-grid/text indicator, GoldSrc profile/catalog, origin, texture caching, and UI source changes from the local working baseline.
- Adds validation, ZIP packaging, annotated tag/commit/atomic-push automation and GitHub Actions validation/artifact packaging.
- Identifies AppImage containers separately from renderer payloads.
- Pins official Blender 5.2.1 source and documents CPU/shader/RNA integration points and the missing native renderer bridge.

The C++ library is a grid-math prototype. No native renderer hook, supported binary patch, or AppImage host replacement is released in this version.
