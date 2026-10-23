# Registered profiles

**Shipped templates** define engine capabilities and game defaults. They are
protected. **User profiles** inherit a template or another user profile and store
only their own settings overrides, under a stable UUID.

Open the viewport header profile popover or **Scene Properties → wavelength Map**.
Both show the **Registered Profile** selector and registry controls.

## Register and use

1. Choose **Register**, enter a name, and choose **Inherit From**.
2. Choose a shipped game template, a common parent such as Source 1, or an
   existing user profile. Current settings differences are captured when the
   parent uses the current backend; a different backend starts from its defaults.
3. Configure project, asset, compiler, grid and export settings as needed.
4. Press **Save Current Overrides** to persist the changes.
5. To switch, select a registered profile and press **Load**.

**Derive** creates a child of the selected profile. Parent changes are resolved
when a child is loaded; they do not silently change the open scene or regenerate
finalized geometry.

```{screenshot} registered-profile-hierarchy
:alt: Protected template and user profile controls with an Inherit From selector
Capture a protected Source template, then a custom child with its parent shown.
```

## Manage and share

**Rename**, **Parent**, and **Remove** apply to user profiles only. Parent changes
retain effective settings and cannot silently switch backend. Register another
profile to change backend. Remove or reparent dependent children before removing
their parent. Missing parents and inheritance cycles are rejected.

Removing a registration does not delete scene objects or finalize geometry.
Current scene settings and existing object ownership metadata remain intact.
Live CSG must be finalized or cancelled before loading another profile.

**Register File** accepts old flat JSON and inherited profiles. **Export Bundle**
includes custom ancestors so another installation can register the hierarchy.
Shipped parents are referenced by ID. Exporting a shipped template produces a
derived custom definition, not an editable replacement for the template.

```json
{
  "schema": 2,
  "name": "My Godot Project",
  "parent": "godot4",
  "settings": {
    "mesh_export_directory": "C:/Projects/MyGame/assets",
    "metric_grid_step": 0.5
  }
}
```

An ID is assigned when omitted. Old snapshots retain their IDs and settings and
use their original engine as parent. Files migrate when saved, not when read.
Registrations live outside the addon under Blender's configuration directory,
`wavelength/profiles/<UUID>.json`, and survive addon reinstalls.

## Shared engine parents

Shipped definitions are data in `environment/profiles/templates.json`:

```text
Convex Brush Engine
  Source 1
    Half-Life 2
      Half-Life 2 / Windows
      Half-Life 2 / Linux
    Source 1 / Windows base
      Garry's Mod / Windows
```

GMod inherits Source rules, not HL2's game paths or entity definitions. Mesh
templates similarly share common rules. Steam folders, FGD names and discovery
paths are template data.

A registered profile configures an existing backend; it does not implement a
new compiler or model format. The generic Source 1 / Windows base exports VMF,
requires an explicit game FGD, and has no Build/Play pipeline. An L4D2 custom
configuration can inherit that base, but this does not add a verified L4D2 build
pipeline.
