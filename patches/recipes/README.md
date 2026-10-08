# Exact-build patch recipes

No Blender 5.2.1 recipe is currently verified. Never invent offsets or set
`verified: true` without a tested, byte-for-byte compatible build.

Recipes use schema 1, `verified: true`, exact `input_sha256`, exact
`output_sha256`, and `changes` with integer `offset`, `before` and `after`
hexadecimal byte strings. Patches must be length-preserving, non-overlapping,
and have exact precondition bytes. The engine only writes a separate output
file, never the original executable. It does not automatically install or
execute patched binaries.

**Important:** This mechanism alone cannot inject arbitrary compiled C++ code.
A real Blender renderer integration needs a proven loader/hook or source-level
change, plus a build-specific patch recipe and end-to-end rendering tests.
