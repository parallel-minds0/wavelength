# wavelength native Source 1 assets

`assets.hh` is the portable original-format reader. `draw_source_assets.hh/.cc`
connect it to Blender's native GPU and background request cache. The complete
Blender integration is included in `../blender/grid-5.2.3-candidate-msvc.patch`.

Build and test the standalone readers without Blender:

```sh
cmake -S native/source1 -B build/source-assets
cmake --build build/source-assets --config Release
ctest --test-dir build/source-assets -C Release --output-on-failure
```

The test executable optionally accepts an ordered, newline-separated file of
mounted game directories/VPK paths and a `models/...mdl` path. It reads installed
game files without extracting or modifying them. No game content is distributed.

The native preview uses original DXT texture blocks and shared model GPU buffers.
It does not execute Valve shader bytecode or load the game's material-system DLL.
See `documentation/developer/native-source-assets.md` for supported formats,
cache bounds, persistence, ownership and current rendering limitations.
