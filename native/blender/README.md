# wavelength native grid — Blender 5.2.2

This is a source-level C++/RNA/DNA and GPU shader integration into Blender's
native grid pass. It is not the legacy embedded-string color patch, and it does
not use Python GPU geometry or a POST_VIEW draw callback. The Python add-on
supplies state through explicit per-viewport RNA properties only.

The parent/subdivision mechanism is unchanged: world-anchored parent intervals
are yellow, grey intervals divide each parent, and subpixel lines fade rather
than switching to another yellow interval. Metric mode starts at one meter.
The existing Blender grid/axis path is retained when the native setting is off.
The custom grid is submitted once inside Blender's grid pass; aligned views use
its behind-geometry rule and perspective views use the actual plane depth.

## Use the native package

Extract the Linux `wavelength-native` package and run `Launch-wavelength`.
It starts the included Blender with factory preferences and loads the matching
Python add-on for that session, then enters the wavelength workspace. It does
not replace your system Blender or change your saved preferences.

In **wavelength → Grid & Units**, select a profile and grid mode. `[` halves
the parent interval and `]` doubles it. Subdivisions stay grey and divide that
interval; `0` selects the profile default (8 for engines, 10 for metric).
Blender / No Engine starts at one meter. Leaving the workspace restores
Blender's normal grid. The native renderer obeys viewport overlay visibility.

The add-on ZIP alone cannot add this native API to a stock Blender executable.
The old installer shader-color experiment is not this implementation and
must not be applied to the native package. On other builds, the authoring tools
remain available but the panel reports the missing native grid explicitly.

## Build separately

Use the exact source and Linux dependency commits in `source.json`, with Git LFS
assets checked out for both the source and `lib/linux_x64` submodule. Run:

```sh
python3 tools/build_native_blender.py --source /path/to/blender-5.2.2 --build /path/to/separate-build --jobs 4
```

The script applies the checked patch idempotently and refuses other revisions.
It never overwrites the installed Blender. Configure/build dependencies and disk
space must be available. The patch changes native types and the shader interface;
it cannot be installed by overwriting two embedded shader strings in a stock
executable. A compiled, tested matching Blender executable is required.
The build helper installs resources into the separate build's `bin` directory.
Package that directory with `tools/package_native_blender.py --runtime
/path/to/separate-build/bin --output /path/to/wavelength-native.tar.gz`.

`grid-5.2.2.patch` is licensed GPL-2.0-or-later, matching the Blender source it
modifies; see `GPL-license.txt`. This explicit license applies to the patch
irrespective of the repository's general copyright notice. Blender's upstream
license and corresponding-source obligations apply to redistribution of a
modified Blender build; the ordinary add-on ZIP is not that executable.

## State API (View3DOverlay)

- `wavelength_grid_enabled`: per viewport, off by default.
- `wavelength_grid_spacing`: exact parent spacing in world coordinates.
- `wavelength_grid_subdivisions`: integer grey subdivisions (2–64).

Python preserves these settings and native floor/ortho visibility while active,
then restores them on workspace exit, feature disable, save/load and unregister.
Unsupported Blender builds retain their normal native grid and display an
explicit unavailable message; there is no Python grid-rendering fallback.

See [VALIDATION.md](VALIDATION.md) for actual runtime results, binary identity,
and the limits of the Linux preview.
