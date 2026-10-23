# Core API contracts

Signatures/docstrings below are read statically. Undocumented callables are explicitly marked; they are not inferred contracts.

## addon/wavelength/source/asset_placement.py

Click-to-paint surfaces and click-to-place entities from the native browser.

### resolved_scope

```python
resolved_scope(context)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:13`

### auto_place

```python
auto_place()
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:17`

### prune_session

```python
prune_session()
```

Dispose of resources if Blender invalidated the session's RNA operator.

{source}`addon/wavelength/source/asset_placement.py:27`

### clear_session

```python
clear_session(_unused=None)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:36`

### payload

```python
payload(context)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:56`

### material

```python
material(context, row)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:72`

### paint

```python
paint(context, obj, index, mat, scope='SURFACE')
```

Assign material indices, never replace a shared material slot's contents.

{source}`addon/wavelength/source/asset_placement.py:86`

### paint_drop

```python
paint_drop(context, obj, index, mat, scope)
```

Apply a drop to selected edit faces, or fall back to the hit/object scope.

{source}`addon/wavelength/source/asset_placement.py:151`

### WL_OT_stamp

```python
class WL_OT_stamp(bpy.types.Operator)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:170`

```python
poll(cls, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:176`

```python
execute(self, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:177`

### PlacementSession

```python
class PlacementSession
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:195`

```python
__init__(self)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:196`

```python
poll(cls, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:199`

```python
invoke(self, context, event, operator)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:200`

```python
status(self, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:217`

```python
finish(self, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:219`

```python
draw_cursor(self)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:237`

```python
modal(self, context, event)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:246`

### WL_OT_click_place

```python
class WL_OT_click_place(bpy.types.Operator)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:288`

```python
poll(cls, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:292`

```python
invoke(self, context, event)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:293`

```python
modal(self, context, event)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:296`

```python
cancel(self, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:297`

### WL_OT_drag_texture

```python
class WL_OT_drag_texture(bpy.types.Operator)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:300`

```python
poll(cls, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:305`

```python
invoke(self, context, event)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/asset_placement.py:309`

### register

```python
register()
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:318`

### unregister

```python
unregister()
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/asset_placement.py:332`

## addon/wavelength/source/build/pipeline.py

Polled subprocess pipeline; no Blender API and no shell command strings.

### Pipeline

```python
class Pipeline
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/build/pipeline.py:8`

```python
__init__(self, commands, directory, timeout=120, environment=None)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/build/pipeline.py:9`

```python
poll(self)
```

Advance at most one queued stage and return its nonblocking state.

Called repeatedly by the owner. Terminal states are stable; a timeout
cancels the active process and records FAILED rather than restarting it.

{source}`addon/wavelength/source/build/pipeline.py:14`

```python
cancel(self)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/build/pipeline.py:46`

### publish_bsp

```python
publish_bsp(source, destination)
```

Replace the selected output atomically after compilation has succeeded.

{source}`addon/wavelength/source/build/pipeline.py:55`

## addon/wavelength/source/context_policy.py

Context capabilities and object meaning; independent of Blender execution.

### capabilities

```python
capabilities(mode='EDIT', workspace_enabled=True, editing=True, overlays=True, preparation=True, rendering=False)
```

Return allowed operations without mutating scene or workspace state.

{source}`addon/wavelength/source/context_policy.py:8`

### role

```python
role(obj, engine='')
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/context_policy.py:20`

### allows

```python
allows(context, feature=None)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/context_policy.py:48`

### preparation_active

```python
preparation_active(scene)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/context_policy.py:58`

### operation_allowed

```python
operation_allowed(context, operator)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/context_policy.py:67`

## addon/wavelength/source/cutter_solid.py

Capped solid operations from a planar cutter path.

### apply

```python
apply(context, guide, points, closed, normal)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/cutter_solid.py:7`

## addon/wavelength/source/formats.py

Bounded classic/Valve 220 MAP reader and deterministic writer.

### Face

```python
class Face
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/formats.py:13`

```python
plane(self)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/formats.py:20`

### Entity

```python
class Entity
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/formats.py:30`

### Map

```python
class Map
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/formats.py:35`

### parse

```python
parse(text)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/formats.py:38`

### quoted

```python
quoted(value)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/formats.py:97`

### write

```python
write(document)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/formats.py:102`

### brush_mesh

```python
brush_mesh(faces)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/formats.py:123`

### quake_axes

```python
quake_axes(normal, projection)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/formats.py:126`

## addon/wavelength/source/node_pencil.py

Curve-driven pencil geometry and capped cutting volumes generated by nodes.

### shape_group

```python
shape_group(kind)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/node_pencil.py:8`

### bake

```python
bake(obj)
```

Commit evaluated node geometry without constructing vertices in Python.

{source}`addon/wavelength/source/node_pencil.py:47`

### create

```python
create(context, guide, kind, height, normal, direction)
```

Keep the source curve editable; node inputs define the generated output.

{source}`addon/wavelength/source/node_pencil.py:57`

### update

```python
update(obj, force=False)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/node_pencil.py:79`

### tick

```python
tick()
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/node_pencil.py:98`

### finalize

```python
finalize(obj)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/node_pencil.py:105`

### volume

```python
volume(context, points, normal, low, high)
```

An input polygon is a curve; Fill/Extrude nodes create the cutter mesh.

{source}`addon/wavelength/source/node_pencil.py:112`

### boolean

```python
boolean(obj, cutter, operation)
```

Use the node Boolean kernel; Python still validates and commits outputs.

{source}`addon/wavelength/source/node_pencil.py:136`

## addon/wavelength/source/node_primitives.py

Versioned parametric Geometry Nodes generators; Python never builds shape vertices.

Node graphs own mesh construction. This adapter validates scalar parameters,
selects profile output parts and evaluates/attaches graphs at Blender boundaries.

### Graph

```python
class Graph
```

Small graph-building vocabulary shared by shape and pencil assets.

{source}`addon/wavelength/source/node_primitives.py:13`

```python
__init__(self, name, generator, inputs)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/node_primitives.py:15`

```python
node(self, kind, label)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/node_primitives.py:24`

```python
wire(self, value, socket)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/node_primitives.py:26`

```python
math(self, op, a, b=0)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/node_primitives.py:29`

```python
vector(self, x=0, y=0, z=0)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/node_primitives.py:32`

```python
split(self, value)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/node_primitives.py:36`

```python
choose(self, test, a, b, kind='FLOAT')
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/node_primitives.py:38`

```python
store(self, geometry, name, value, kind='INT', domain='FACE')
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/node_primitives.py:42`

```python
transform(self, geometry, translation=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/node_primitives.py:46`

```python
finish(self, geometry)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/node_primitives.py:50`

### material_uv

```python
material_uv(g, geometry)
```

Carry the assigned material and generate the UV attribute engine shaders use.

{source}`addon/wavelength/source/node_primitives.py:60`

### parameters

```python
parameters(definition)
```

Validate authoring parameters; grid fallback changes inputs, not vertices.

{source}`addon/wavelength/source/node_primitives.py:72`

### group

```python
group(kind, sphere_type='ICO')
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/node_primitives.py:98`

### set_input

```python
set_input(modifier, name, value)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/node_primitives.py:167`

### attach

```python
attach(obj, definition, index=0)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/node_primitives.py:175`

### sync_materials

```python
sync_materials(obj)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/node_primitives.py:186`

### evaluate

```python
evaluate(definition)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/node_primitives.py:197`

## addon/wavelength/source/pencil.py

Editable line/curve guides with explicit knife projection and mesh creation.

### target_hit

```python
target_hit(context, target, origin, direction)
```

Hit the chosen mesh even when another object occludes it.

{source}`addon/wavelength/source/pencil.py:13`

### point

```python
point(co)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:29`

### is_guide

```python
is_guide(obj)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:30`

### guide

```python
guide(context)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:33`

### WLCutterGuide

```python
class WLCutterGuide(bpy.types.PropertyGroup)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:39`

### WLDrawSettings

```python
class WLDrawSettings(bpy.types.PropertyGroup)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:52`

### records

```python
records(obj)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:64`

### sampled

```python
sampled(obj)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:72`

### cut_direction

```python
cut_direction(obj)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:88`

### normal

```python
normal(obj)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:93`

### create_guide

```python
create_guide(context, points, plane_normal, closed=False, target=None)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:97`

### create_geometry

```python
create_geometry(context, obj, kind, height=None)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:119`

### apply_cut

```python
apply_cut(context, obj)
```

Knife-project on a private mesh copy. Failure restores the original mesh.

{source}`addon/wavelength/source/pencil.py:147`

### cut_result

```python
cut_result(obj)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:211`

### cycle_keep

```python
cycle_keep(settings, step=1)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:218`

### WL_OT_apply_cut

```python
class WL_OT_apply_cut(bpy.types.Operator)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:223`

```python
poll(cls, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:226`

```python
execute(self, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:227`

### WL_OT_create_cut_geometry

```python
class WL_OT_create_cut_geometry(bpy.types.Operator)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:235`

```python
poll(cls, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:238`

```python
execute(self, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:239`

### WL_OT_keep_cut_guide

```python
class WL_OT_keep_cut_guide(bpy.types.Operator)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:246`

```python
poll(cls, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:249`

```python
execute(self, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:250`

### WL_OT_activate_cutter

```python
class WL_OT_activate_cutter(bpy.types.Operator)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:257`

```python
poll(cls, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:261`

```python
execute(self, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:262`

### WL_OT_draw_path

```python
class WL_OT_draw_path(bpy.types.Operator)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:270`

```python
poll(cls, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:273`

```python
invoke(self, context, event)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:286`

```python
modal(self, context, event)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:424`

### WL_PT_drawing

```python
class WL_PT_drawing(bpy.types.Panel)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:491`

```python
poll(cls, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:494`

```python
draw(self, context)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:495`

### WL_Tool_pencil

```python
class WL_Tool_pencil(bpy.types.WorkSpaceTool)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:509`

```python
draw_settings(context, layout, tool)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:515`

### WL_Tool_pencil_edit

```python
class WL_Tool_pencil_edit(bpy.types.WorkSpaceTool)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:526`

```python
draw_settings(context, layout, tool)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/pencil.py:532`

### register

```python
register()
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:546`

### unregister

```python
unregister()
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/pencil.py:556`

## addon/wavelength/source/procedural.py

Generator-independent definitions, evaluation and profile validation.

No Blender data mutation belongs in this module. Adapters return local-space
mesh parts; Blender owns committing them and baking evaluated objects.

### Definition

```python
class Definition
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/procedural.py:15`

```python
dumps(self)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/procedural.py:28`

```python
loads(cls, text)
```

Implementation method; refer to its source for current behavior.

{source}`addon/wavelength/source/procedural.py:31`

### define

```python
define(kind, owner, parameters, unit_meters, grid_step=None, profile_id='', profile_name='')
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/procedural.py:37`

### evaluate

```python
evaluate(definition)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/procedural.py:42`

### validate

```python
validate(definition, parts)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/procedural.py:56`

### state

```python
state(root)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/procedural.py:67`

### definition_for

```python
definition_for(root, kind, values, owner, unit, grid_step)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/procedural.py:70`

## addon/wavelength/source/profiles.py

Engine authoring profiles.  Tools read units/behavior from the active profile.

### is_mesh_export

```python
is_mesh_export(engine)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/profiles.py:6`

### is_source

```python
is_source(engine)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/profiles.py:12`

### is_source2

```python
is_source2(engine)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/profiles.py:15`

### uses_valve_axes

```python
uses_valve_axes(engine)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/profiles.py:17`

### get

```python
get(engine)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/profiles.py:21`

### requires_convex_brushes

```python
requires_convex_brushes(engine)
```

Return whether the profile explicitly requires convex BSP brushes.

Unrecognized or mesh-based profiles are unrestricted unless they opt in.
This is an authoring/export constraint, independent of Blender's display.

{source}`addon/wavelength/source/profiles.py:27`

### family

```python
family(engine)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/profiles.py:38`

### is_goldsrc

```python
is_goldsrc(engine)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/profiles.py:41`

### grid_step_units

```python
grid_step_units(settings)
```

Selected engine-grid increment, in engine authoring units.

{source}`addon/wavelength/source/profiles.py:45`

### active_grid_step_meters

```python
active_grid_step_meters(settings)
```

Authoritative creation/grid increment for the active engine profile.

None means the profile has no engine-unit snap; Blender viewport-grid snapping is resolved from the active 3D view by the creation tool.

{source}`addon/wavelength/source/profiles.py:49`

### create_cube_label

```python
create_cube_label(settings)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/profiles.py:60`

### unit_meters

```python
unit_meters(settings)
```

Meters represented by one authoring unit for the active profile.

{source}`addon/wavelength/source/profiles.py:64`

### engine_to_world

```python
engine_to_world(settings, value)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/profiles.py:68`

### world_to_engine

```python
world_to_engine(settings, value)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`addon/wavelength/source/profiles.py:71`

### snap_enabled

```python
snap_enabled(settings, context=None)
```

Whether grid snapping should be enforced for the active profile.

{source}`addon/wavelength/source/profiles.py:74`

### active_snap_step_units

```python
active_snap_step_units(settings, context=None)
```

Active snap step in authoring units (engine units or Blender meters), or None if unsnapped.

{source}`addon/wavelength/source/profiles.py:87`

### active_snap_step_meters

```python
active_snap_step_meters(settings, context=None)
```

Active snap step in world meters, or None if unsnapped.

{source}`addon/wavelength/source/profiles.py:96`

### snap_world_value

```python
snap_world_value(settings, value, context=None)
```

Snap a world-space scalar through engine-unit space (or Blender grid if enabled), then convert back.

{source}`addon/wavelength/source/profiles.py:105`

### snap_world_length

```python
snap_world_length(settings, value, minimum_steps=1, context=None)
```

Snap a positive world-space length to an exact grid multiple when snapping is active.

{source}`addon/wavelength/source/profiles.py:116`

### display_grid

```python
display_grid(settings)
```

Parent spacing in meters and subdivisions, independent of Blender LOD.

{source}`addon/wavelength/source/profiles.py:128`

## installer/wavelength_installer/source_bundle.py

Run the installer directly from the source tree without a separate add-on ZIP.

### bundle_from_source

```python
bundle_from_source(root)
```

No callable docstring yet. Read the source and the Developer Guide before using this internal interface.

{source}`installer/wavelength_installer/source_bundle.py:8`
