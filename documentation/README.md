# wavelength documentation

This is the canonical Markdown source folder for the wavelength handbook.
Start at [index.md](index.md). It contains both the User Guide and Developer Guide,
with source-linked examples, a generated code reference and manual screenshot
placeholders. Put captures in [screenshots/](screenshots/README.md).

With the documentation dependencies installed:

```console
python documentation/build.py check
python documentation/build.py build --format all
python documentation/build.py sync
```

The local `.code-root` file selects the implementation checkout containing
`tools/docs.py`; it is a machine-local path, relative to this folder. A normal
source checkout with its own `tools/docs.py` does not need this setting.
HTML/PDF outputs remain under that implementation checkout's `build/docs/`.
Packaging uses generated copies; edit this folder rather than those copies.
