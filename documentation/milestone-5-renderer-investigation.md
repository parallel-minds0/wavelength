# Milestone 5: Renderer integration investigation

The grid bridge calculates whether a coordinate belongs to a selected snap interval, but Blender's viewport grid is rendered by Blender's internal GPU shader pipeline. Calling the bridge from Python does not alter that shader.

## Read-only reconnaissance

Run `python installer/cli.py probe-renderer /path/to/extracted/blender --report renderer-report.json` on the **extracted executable**, not the outer AppImage. The command hashes the executable, reads its ELF architecture and searches for several shader-related marker strings. The report is only an investigation aid. A marker occurrence is **not** a valid binary patch offset.

## Required before a real patch

1. Identify the precise Blender 5.2.1 source revision and GPU shader implementation, including grid line spacing, antialiasing, and zoom-dependent fade behavior.
2. Determine whether the shader is embedded in the executable or generated/loaded elsewhere; inspect the corresponding compiled binary/disassembly.
3. Establish a tested method to change the **existing** grid shader's output for only the matching snap lines, without drawing a second grid. This likely requires a shader replacement or a validated shader/program creation hook; the C++ grid math library alone is insufficient.
4. Specify a robust, versioned state channel from the add-on to the patched native renderer.
5. Verify against an exact executable SHA-256 on a disposable copy, with visual tests in Blender and reversible installation.

The current `patch_blender` entry point intentionally refuses modifications. Do not convert marker search hits into patch recipes without the above verification.
