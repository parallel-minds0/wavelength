# Third-party layout

Components may be grouped by purpose, for example:

- `compilers/` — redistributable map compiler toolchains.
- `tools/` — other redistributable helper binaries/source.
- `licenses/` — notices when a component does not carry them in its own directory.

Code should resolve bundled tools from `source.paths.THIRD_PARTY_ROOT`; platform/profile selection decides which executable to use.
