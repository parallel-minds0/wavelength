# Documentation authoring contract

## One Markdown source tree

Author in `documentation/`. User and developer navigation lives in their `index.md` files.
The installed add-on receives a generated copy; edit the canonical pages rather
than that copy. Build products, code reference pages and source viewers are
regenerated from the checkout. The archive preserves dated investigations and
must not be mistaken for current implementation instructions.

## Document code at three levels

1. Module docstrings state ownership and boundaries.
2. Callable/class docstrings explain inputs, units, side effects, return values
   and failure behavior where those are not obvious.
3. Inline comments explain why a constraint, ordering decision or workaround
   exists. Avoid narrating each assignment or duplicating an obvious expression.

When a non-obvious algorithm needs a handbook example, bracket a short coherent
region in the real source with `# docs:begin region-name` and
`# docs:end region-name`. Include it with the `code-sample` directive and a
repository-relative path. The build reads that exact region and fails if it is
missing or ambiguous. Keep comments inside the region so the example explains
the implementation rather than displaying unexplained code.

Use the `source` role with a repository-relative path and optional line number
for code links. HTML provides local, line-anchored source viewers, even for
uncommitted code. PDF prints the path and line; it never requires running Blender.
Generated signatures/docstrings are an inventory, not a substitute for narrative
contracts or carefully chosen inline commentary.

## Screenshots, captured manually

Use a `screenshot` directive with a stable lowercase hyphenated ID, an `alt`
option and capture instructions. Missing images deliberately render as labeled
placeholders in HTML and PDF. Add the capture at
`documentation/screenshots/<id>.png`; the next build replaces the placeholder with the
image and caption. Do not commit empty image files or broken image links.

The build writes `build/docs/screenshots.json` listing every ID, page, instruction,
expected filename and capture status. Use it as the screenshot checklist.

## Build tools

Create a Python 3.11+ virtual environment and install `documentation/requirements.txt`.
The pinned stack is Sphinx/MyST for Markdown and rst2pdf/ReportLab for the book;
LaTeX, Blender and engine installations are not required.

```console
python -m venv .venv-docs
.venv-docs/Scripts/python -m pip install -r documentation/requirements.txt
.venv-docs/Scripts/python documentation/build.py build --format all
```

On Linux/macOS use `.venv-docs/bin/python`. The source-folder launcher uses
`documentation/.code-root` when the implementation is in a separate checkout.
You can also run that checkout's `tools/docs.py` with `--source` pointing at this
folder. HTML starts at
`build/docs/html/index.html`; the PDF is
`build/docs/pdf/wavelength-handbook.pdf`. `sync` regenerates the add-on Markdown
copy and removes only files listed in its prior generated manifest.

## Preserve implemented behavior

The permanent [feature ledger](../FEATURES.md) records stable behavioral IDs,
implementation ownership, regression entrypoints and known limits. Consult it
before changing a subsystem. Every fix, addition or architectural replacement
updates the affected contracts and verification; retain retired rows with their
reason and migration path. The [surface inventory](../reference/feature-surface.md)
includes private helpers and static UI/settings/native evidence, not just the
visible buttons.

`python tools/feature_inventory.py` compares the current implementation with its
reviewed baseline. Source-body, interface, settings, test, native-patch, asset
and configuration changes fail until explicitly reviewed. Accept a deliberate
change with `--update --feature WL-... --reason "change, preservation, tests and
limits"`; this appends the change record. Do not use baseline refresh as a way
to dismiss regressions. Documentation checks run this guard too. Structural
presence is not proof that an operator registers or its behavior works: run
meaningful subsystem regressions and report what actually passed.

The PDF embeds DejaVu Sans 2.37 from the checked-in documentation font assets
to render navigation arrows and other Unicode text. The font license is stored
beside those assets.
