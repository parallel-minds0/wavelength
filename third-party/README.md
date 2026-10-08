# Manually bundled dependencies

Place your **redistributable** compiler toolchains in `compilers/<platform>/` and your self-contained Python interpreter in `python/<platform>/`. These folders intentionally contain no binaries. Ensure the toolchain includes its linker, standard library, headers and runtime dependencies, not just a `g++` executable. Review redistribution licenses before packaging.

The installer searches bundled compiler executables first and then falls back to system PATH. It does not download or install compilers. Bundled Python is for launching the standalone installer; Blender uses its own Python for the add-on. Bundled runtimes must be complete and match the target OS/architecture.
