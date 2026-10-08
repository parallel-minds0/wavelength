# Architecture

Wavelength separates engine/profile rules from Blender editing behavior where practical. Profiles define engine-facing assumptions such as grid/unit behavior and toolchain stages. Brush, entity, texture, export, and build responsibilities remain separate modules instead of being collapsed into one UI module.

Entity-related code is grouped under `source/entity/`. Compiler/build execution is grouped under `source/build/`. Repository-owned editor resources are addressed through the top-level `environment/` directory.

The Wavelength Asset Browser is hosted by Blender's Asset Browser machinery because Python add-ons cannot register an equivalent new native Blender Space type. Real model thumbnail rendering is deferred; placeholder/editor representations remain the alpha path.
