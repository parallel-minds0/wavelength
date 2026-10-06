# Repository structure

The repository root is directly installable as the Blender add-on. Root `__init__.py` is Blender's entry point and delegates to the implementation in `source/`.

`environment/` contains versioned resources used by the editor and tests. `models/` is for editor model references, `sprites/` for SVG/PNG entity representations, and `maps/` for small test maps.

`dev/` is local scratch space and is ignored by Git. `third-party/` is part of the distributable package and holds only third-party source/binaries whose licenses permit redistribution.

`documentation/` contains Markdown source suitable for later HTML/PDF presentation alongside source comments.
