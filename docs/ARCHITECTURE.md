# Implementation ownership

- **Python add-on:** Blender UI, profiles, entities, WAD assets, MAP import/export, brush operators, editor state, snapping and grid scale. Existing code is preserved under `addon/wavelength/`.
- **C++ native:** Only native renderer/grid internals that Blender Python cannot reach, plus profiled performance bottlenecks if warranted. Current `native/` code is an isolated math prototype, **not** a working Blender grid renderer modification.
- **Standalone Python installer:** Locate Blender, fingerprint executable, discover host C++ compiler, compile C++, install Python add-on, then (only if exact build-specific patch exists) apply native patch with backup and rollback. An embedded Python runtime/GUI wizard is a future packaging step; it is **not included**.

## Intended installer sequence

1. Identify Blender executable and user-specific scripts directory; obtain explicit consent.
2. Verify platform, version, exact binary SHA-256 and compatible patch recipe.
3. Find and validate a suitable compiler and required build dependencies.
4. Compile native payload, verify ABI and expected artifact.
5. Install Python add-on transactionally and verify it can register.
6. Back up Blender; apply verified native patch to an offline copy; validate and atomically deploy.
7. Restart and verify behavior; provide a restoration path.

**Current implementation:** compiler discovery, binary SHA-256 inspection, C++ object compilation, and explicit-path fresh Python add-on installation. The final patch stage refuses to run. No shader hook, injection, patch recipe, rollback, AppImage repack, or bundled interpreter is implemented. The install CLI does not yet orchestrate all stages automatically.

**Grid contract:** Wavelength Python determines the snap interval in meters; native rendering must use the same value, respect Blender zoom/perspective/fading and leave all other lines untouched. Integration/transport remains to be designed against Blender source and a verified build.

## Verified baseline update

See [CURRENT-STATE.md](CURRENT-STATE.md) for the 2026-10-08 audit. Native build now produces a shared C ABI library, rather than just an object file. A same-length verified-byte recipe engine and copy restoration helper exist, but there are no renderer recipes. AppImage detection, source-lock research, checks/package and commit/tag/push automation are available. The host Blender executable has not been modified. The earlier intended installer sequence remains future work.
