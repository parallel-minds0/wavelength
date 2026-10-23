# Local Windows cross-build preparation

Status: experimental configuration only; no configuration, compilation, or Windows
execution has been performed with this toolchain. The current release uses GitHub's
Windows/MSVC runner.

- Compiler: system LLVM 21.1.8, clang-cl, MSVC ABI, Windows x86_64 target.
- SDK/runtime: `build/toolchains/windows-sdk`, prepared by xwin 0.10.0.
- Download cache: `build/toolchains/xwin-cache`.
- Toolchain: `native/windows-clang-cl.cmake`.
- Existing Blender source: `build/native-grid/blender-5.2.2`.
- Reserve a separate future build directory: `build/windows-cross`.

Do not reuse the Linux build directory or assume the toolchain is sufficient to
build Blender unchanged. Before the first cross-build:

1. Acquire Blender's pinned Windows dependency tree matching its source revision.
2. Adapt build-time generators (including makesdna and makesrna) to use Linux host
   executables rather than attempting to execute Windows outputs.
3. Check Windows-specific resource generation, library discovery, and compiler
   options under the Linux host. Configure resource include paths if needed.
4. Validate compile/link behavior and binary-difference reconstruction separately.

No Wine/Proton or Windows execution tests are configured. Installing these tools
does not change the installed Blender or the active GitHub build.
