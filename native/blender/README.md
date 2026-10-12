# Native grid patch

Wavelength is distributed as an installer and patches for an existing Blender.
Do not distribute `build/native-grid/build/bin` or direct users to a separate Blender.
The full source patch is `grid-5.2.2.patch`; its upstream revision is in `source.json`.
Internal reference builds are used for development, visual testing, and generating
binary differences. This derivative source patch is GPL-2.0-or-later; see GPL-license.txt.

The installer selects a binary difference using the exact original SHA-256, checks
both patch and resulting executable hashes, and probes native RNA startup beside
the selected installation before committing changes. The user's existing resources
and libraries stay in place. Original bytes are retained for uninstall and rollback.

See [release instructions](../../docs/RELEASE-NOTES.md). Linux x86_64 is the tested
installation target retained in v0.15.0. The Windows v0.15.0 native grid patch was
compiled with MSVC and its binary reconstruction checked. Windows installation
and rendering remain untested; see the Windows manual verification guide.

Internal build: `tools/build_native_blender.py`. Delta generation:
`tools/make_binary_patch.py` (maintainer-only bsdiff4 dependency). Installation uses
the bundled Python standard library and does not need a compiler.
