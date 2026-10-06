# Development and testing

Treat the repository as development source, not a finished Blender product.

Before packaging a change:

1. Compile-check every Python file under `source/`.
2. Do not package `__pycache__`, `.pyc`, `.pyo`, Blender backup files, generated caches, `dev/` contents, or `third-party/` contents.
3. Validate ZIP integrity.
4. Test engine-specific behavior in Blender and, where applicable, with the actual compiler/game toolchain.

The maps under `environment/maps/` are intentionally small smoke-test fixtures, not example production levels.
