"""Authored terrain masks, deterministic rules, shared instances and overrides.

Schema 1 lives in native mesh vertex groups and Object RNA layer records. Generated
point geometry is disposable. No depsgraph handlers or whole-world rescatters.
"""
import json
import math
import uuid

import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty,
                       IntProperty, PointerProperty, StringProperty)
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

from . import context_policy, distribution

SCHEMA = 1
OVERRIDES = 'wl_environment_placement_overrides'


def read_overrides(layer):
    values=json.loads(layer.id_data.get(OVERRIDES,'{}'))
    return values.get(layer.uid,layer.get('overrides','{}'))


def write_overrides(layer,value):
    if not isinstance(json.loads(value),dict):raise ValueError('Overrides must be an object')
    values=json.loads(layer.id_data.get(OVERRIDES,'{}'))
    values[layer.uid]=value
    layer.id_data[OVERRIDES]=json.dumps(values,sort_keys=True)


def identity(obj):
    if not obj.get('wl_environment_id'):
        obj['wl_environment_id'] = uuid.uuid4().hex
    return obj['wl_environment_id']


def add_layer(obj, kind='DISTRIBUTION', name='Trees'):
    if obj.type != 'MESH' or obj.data.users > 1:
        raise ValueError('Use a single-user terrain mesh for independently editable masks')
    identity(obj)
    obj['wl_environment_schema']=SCHEMA
    layer = obj.wavelength_environment_layers.add()
    layer.name = name
    layer.uid = uuid.uuid4().hex
    layer.kind = kind
    layer.mask = obj.vertex_groups.new(name=f'WL {name} {layer.uid[:8]}').name
    obj.wavelength_environment_active = len(obj.wavelength_environment_layers) - 1
    return layer


def active_layer(obj):
    layers = obj.wavelength_environment_layers
    return layers[min(obj.wavelength_environment_active, len(layers)-1)] if layers else None


def fork_layer_set(obj):
    """Independent terrain copy: retain masks/rules, never share disposable previews."""
    if not obj.wavelength_environment_layers:
        return
    saved=[(layer,layer.overrides) for layer in obj.wavelength_environment_layers]
    obj['wl_environment_id']=uuid.uuid4().hex
    obj[OVERRIDES]='{}'
    for layer,value in saved:
        layer.uid=uuid.uuid4().hex
        layer.overrides=value
        layer.preview=None


def stamp(obj, layer, center, radius, value, strength=1.):
    """World-meter brush stamp used by scripted tools and regression fixtures.

    Native Weight Paint edits the same group interactively. Stamps do not move
    vertices or touch any other mask. Linear falloff, replace toward target value.
    """
    if obj.data.users > 1 or radius <= 0:
        raise ValueError('Use a positive brush radius and a single-user terrain mesh')
    group = obj.vertex_groups.get(layer.mask)
    if group is None:
        raise ValueError(f'{layer.name}: authored mask is missing')
    for vertex in obj.data.vertices:
        distance = (obj.matrix_world @ vertex.co - Vector(center)).length
        if distance > radius:
            continue
        old = next((g.weight for g in vertex.groups if g.group == group.index), 0.)
        factor = min(1., max(0., strength * (1-distance/radius)))
        group.add([vertex.index], min(1., max(0., old+(value-old)*factor)), 'REPLACE')
    obj.data.update()


def palette(layer):
    if layer.palette is None:
        raise ValueError(f'{layer.name}: choose a prototype palette collection')
    objects = [o for o in layer.palette.objects if o.type == 'MESH']
    if not objects:
        raise ValueError(f'{layer.name}: palette has no mesh prototypes')
    for obj in objects:
        identity(obj)
        if not obj.matrix_world.is_identity:
            raise ValueError(f'{obj.name}: prototype must have applied transforms and its origin at the placement foot; use a normalized palette copy')
        if obj.animation_data or obj.constraints or any(m.type=='ARMATURE' for m in obj.modifiers):
            raise ValueError(f'{obj.name}: this environment milestone supports static mesh prototypes only')
    objects.sort(key=lambda o: o['wl_environment_id'])
    if len({identity(o) for o in objects}) != len(objects):
        raise ValueError('Palette contains duplicated identities; assign independent prototype IDs')
    distribution.choose(0, 'validate', [o.wavelength_environment_weight for o in objects])
    return objects


class Surface:
    """One evaluated, world-space terrain snapshot and its interpolated masks."""
    def __init__(self, context, obj):
        self.obj = obj
        evaluated = obj.evaluated_get(context.evaluated_depsgraph_get())
        self.mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True,
                                                   depsgraph=context.evaluated_depsgraph_get())
        self.mesh.calc_loop_triangles()
        self.vertices = [obj.matrix_world @ v.co for v in self.mesh.vertices]
        self.triangles = [tuple(t.vertices) for t in self.mesh.loop_triangles]
        if not self.triangles:
            self.close()
            raise ValueError(f'{obj.name}: terrain has no evaluated faces')
        self.bvh = BVHTree.FromPolygons(self.vertices, self.triangles, all_triangles=True)
        self.bounds = (min(v.x for v in self.vertices), min(v.y for v in self.vertices),
                       max(v.x for v in self.vertices), max(v.y for v in self.vertices))
        self.top = max(v.z for v in self.vertices)+1
        self.depth = self.top-min(v.z for v in self.vertices)+1
        self.groups = {g.name:g.index for g in evaluated.vertex_groups}

    def close(self):
        bpy.data.meshes.remove(self.mesh)

    def hit(self, x, y):
        point, normal, triangle, _ = self.bvh.ray_cast(Vector((x,y,self.top)), Vector((0,0,-1)), self.depth)
        return (point, normal, triangle) if triangle is not None else None

    def weight(self, name, point, triangle):
        if name not in self.groups:
            raise ValueError(f'{self.obj.name}: missing mask {name}; recreate or remap it explicitly')
        indices = self.triangles[triangle]
        values = [next((g.weight for g in self.mesh.vertices[i].groups
                        if g.group == self.groups[name]), 0.) for i in indices]
        result = barycentric_transform(point, *(self.vertices[i] for i in indices),
                                       *(Vector((value,0,0)) for value in values))
        return min(1., max(0., result.x))


def overrides(layer):
    result = json.loads(layer.overrides)
    if not isinstance(result, dict):
        raise ValueError('Invalid distribution overrides')
    return result


def set_override(layer, address, prototype=None, matrix=None, delete=False):
    data = overrides(layer)
    if delete:
        data[address] = {'deleted':True}
    else:
        if prototype is None or matrix is None or not all(math.isfinite(v) for row in matrix for v in row):
            raise ValueError('A placement override needs a prototype and finite transform')
        data[address] = {'prototype':identity(prototype), 'matrix':[list(row) for row in matrix]}
    layer.overrides = json.dumps(data, sort_keys=True)


def records(context, obj, layer, surface=None):
    """Resolve once for both preview and export. Overrides are authored intent."""
    if not layer.enabled or layer.kind != 'DISTRIBUTION':
        return []
    prototypes = palette(layer)
    if layer.scale_min > layer.scale_max:
        raise ValueError('Minimum scale must not exceed maximum scale')
    owned = surface is None
    surface = surface or Surface(context, obj)
    result = []
    edits = overrides(layer)
    try:
        exclusions = [l for l in obj.wavelength_environment_layers if l.enabled and l.kind=='EXCLUSION']
        if layer.mode=='PLACEMENTS':
            from .environment_adopt import placement_candidates
            for address,hit,prototype,matrix in placement_candidates(surface,layer):
                if address in edits:continue
                point,normal,triangle=hit
                coverage=surface.weight(layer.mask,point,triangle)
                exclusion=max((surface.weight(l.mask,point,triangle) for l in exclusions),default=0.)
                if distribution.random_value(layer.seed,address,'coverage')>=coverage*(1-exclusion)*min(1.,layer.density):continue
                result.append({'id':address,'prototype':identity(prototype),'matrix':[list(r) for r in matrix]})
        generated=distribution.candidates(surface.bounds, layer.cell_size, layer.density, layer.seed) if layer.mode=='SCATTER' else ()
        for address,x,y,chance in generated:
            if address in edits:
                continue
            hit = surface.hit(x,y)
            if hit is None:
                continue
            point,normal,triangle = hit
            if normal.z < math.cos(math.radians(layer.max_slope)):
                continue
            coverage = surface.weight(layer.mask,point,triangle)
            exclusion = max((surface.weight(l.mask,point,triangle) for l in exclusions), default=0.)
            if chance >= coverage*(1-exclusion):
                continue
            index = distribution.choose(layer.seed,address,[o.wavelength_environment_weight for o in prototypes])
            yaw = distribution.random_value(layer.seed,address,'yaw')*math.tau
            rotation = (normal.to_track_quat('Z','Y') if layer.align_normal else Quaternion()) @ Quaternion((0,0,1),yaw)
            scale = layer.scale_min+(layer.scale_max-layer.scale_min)*distribution.random_value(layer.seed,address,'scale')
            matrix = Matrix.LocRotScale(point,rotation,Vector((scale,)*3))
            result.append({'id':address,'prototype':identity(prototypes[index]),'matrix':[list(r) for r in matrix]})
        available = {identity(o) for o in prototypes}
        for address, edit in sorted(edits.items()):
            if edit.get('deleted'):
                continue
            if edit['prototype'] not in available:
                raise ValueError(f'{layer.name}: override {address} references a missing palette prototype')
            result.append({'id':address, **edit})
        return result
    finally:
        if owned:
            surface.close()


def preview(context, obj, layer):
    items = records(context,obj,layer)
    total = len(items)
    prototypes = palette(layer)
    # Stable thinning is preview-only and never alters full export membership.
    items = [r for r in items if distribution.random_value(layer.seed,r['id'],'preview') < layer.preview_fraction]
    editing = {o.get('wl_environment_edit') for o in context.scene.objects
               if o.get('wl_environment_layer') == layer.uid}
    items = [r for r in items if r['id'] not in editing]
    mesh = bpy.data.meshes.new(f'{obj.name} {layer.name} points')
    mesh.from_pydata([Matrix(r['matrix']).translation for r in items],[],[])
    indices = {identity(o):i for i,o in enumerate(prototypes)}
    attribute = mesh.attributes.new('wl_prototype','INT','POINT')
    attribute.data.foreach_set('value',[indices[r['prototype']] for r in items])
    for name,values in (('wl_rotation',[v for r in items for v in Matrix(r['matrix']).to_euler()]),
                        ('wl_scale',[v for r in items for v in Matrix(r['matrix']).to_scale()])):
        mesh.attributes.new(name,'FLOAT_VECTOR','POINT').data.foreach_set('vector',values)
    tree = bpy.data.node_groups.new(f'{layer.name} shared instances','GeometryNodeTree')
    tree.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    tree.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    nodes,links = tree.nodes,tree.links
    inputs=nodes.new('NodeGroupInput'); output=nodes.new('NodeGroupOutput'); join=nodes.new('GeometryNodeJoinGeometry')
    attributes={}
    for name,kind in (('wl_prototype','INT'),('wl_rotation','FLOAT_VECTOR'),('wl_scale','FLOAT_VECTOR')):
        node=nodes.new('GeometryNodeInputNamedAttribute');node.data_type=kind;node.inputs['Name'].default_value=name
        attributes[name]=node.outputs['Attribute']
    for index, prototype in enumerate(prototypes):
        info=nodes.new('GeometryNodeObjectInfo');info.transform_space='ORIGINAL'
        info.inputs['Object'].default_value=prototype;info.inputs['As Instance'].default_value=True
        compare=nodes.new('FunctionNodeCompare');compare.data_type='INT';compare.operation='EQUAL'
        links.new(attributes['wl_prototype'],compare.inputs['A']);compare.inputs['B'].default_value=index
        instance=nodes.new('GeometryNodeInstanceOnPoints')
        links.new(inputs.outputs['Geometry'],instance.inputs['Points'])
        links.new(compare.outputs[0],instance.inputs['Selection'])
        links.new(info.outputs['Geometry'],instance.inputs['Instance'])
        links.new(attributes['wl_rotation'],instance.inputs['Rotation']);links.new(attributes['wl_scale'],instance.inputs['Scale'])
        links.new(instance.outputs['Instances'],join.inputs['Geometry'])
    links.new(join.outputs['Geometry'],output.inputs['Geometry'])
    visual = layer.preview
    if visual is None or visual.name not in context.scene.objects:
        visual=bpy.data.objects.new(f'{obj.name} · {layer.name} preview',mesh)
        context.scene.collection.objects.link(visual)
        visual['wl_exclude']=True;visual['wl_editor_helper']=True;visual.hide_select=True
        layer.preview=visual
    else:
        old=visual.data;visual.data=mesh
        if old.users==0:bpy.data.meshes.remove(old)
    for modifier in list(visual.modifiers):
        old=modifier.node_group if modifier.type=='NODES' else None
        visual.modifiers.remove(modifier)
        if old and old.users==0:bpy.data.node_groups.remove(old)
    visual.modifiers.new('Shared palette instances','NODES').node_group=tree
    visual['wl_environment_layer']=layer.uid
    visual.hide_render=not layer.enabled
    layer.status=f'{len(items)} preview / {total} placements'
    return visual


class WLEnvironmentLayer(bpy.types.PropertyGroup):
    uid:StringProperty()
    kind:EnumProperty(items=[('DISTRIBUTION','Distribution','Trees, vegetation or rocks'),
                             ('EXCLUSION','Exclusion','Clear generated placements; manual overrides survive'),
                             ('MATERIAL','Material Mask','Independent terrain material coverage')])
    enabled:BoolProperty(name='Enabled',default=True)
    mask:StringProperty()
    mode:EnumProperty(items=[('SCATTER','Generated','Seeded coverage distribution'),('PLACEMENTS','Adopted Points','Retain and edit existing native placements')])
    placements:PointerProperty(type=bpy.types.Object)
    source_origin:StringProperty()
    follow_terrain:BoolProperty(name='Follow Sculpted Terrain',default=True)
    adopt_source:PointerProperty(type=bpy.types.Object)
    adopt_remainder:PointerProperty(type=bpy.types.Object)
    source_hidden:BoolProperty()
    source_render_hidden:BoolProperty()
    palette:PointerProperty(type=bpy.types.Collection,name='Asset Palette')
    material:PointerProperty(type=bpy.types.Material,name='Material Reference')
    biome:EnumProperty(name='Paint Surface',items=[('CUSTOM','Custom Material','')]+[(str(i),name,'Privateer native biome') for i,name in enumerate(('Mixed Woodland','Meadow','Conifer Upland','Wetland','Rocky Heath','Coastal Shore'))])
    manual_prototype:PointerProperty(type=bpy.types.Object,name='Manual Prototype')
    density:FloatProperty(name='Instances / m²',default=.08,min=0)
    cell_size:FloatProperty(name='Candidate Cell (m)',default=4,min=.01)
    seed:IntProperty(name='Seed',default=1)
    max_slope:FloatProperty(name='Maximum Slope',default=45,min=0,max=90)
    scale_min:FloatProperty(name='Minimum Scale',default=.8,min=.001)
    scale_max:FloatProperty(name='Maximum Scale',default=1.2,min=.001)
    align_normal:BoolProperty(name='Align to Surface',default=False)
    preview_fraction:FloatProperty(name='Preview Fraction',default=1,min=0,max=1)
    preview:PointerProperty(type=bpy.types.Object)
    overrides:StringProperty(get=read_overrides,set=write_overrides)
    status:StringProperty()


class WL_OT_environment_layer(bpy.types.Operator):
    bl_idname='wavelength.environment_layer';bl_label='Environment Layer';bl_options={'REGISTER','UNDO'}
    action:EnumProperty(items=[(v,v.title(),'') for v in ('ADD','ADOPT','MATERIAL_PREVIEW','REMOVE','PAINT','REFRESH','FILL','CLEAR','MANUAL','EDIT','KEEP','DISCARD','DELETE')])
    kind:EnumProperty(items=[(v,v.title(),'') for v in ('DISTRIBUTION','EXCLUSION','MATERIAL')])

    @classmethod
    def poll(cls,context):
        return context_policy.allows(context,'editing') and context.object is not None and context.object.type=='MESH'

    def execute(self,context):
        obj=context.object
        try:
            if obj and obj.get('wl_environment_edit'):
                return self.edit_action(context,obj)
            if not obj or obj.type!='MESH':raise ValueError('Select a terrain mesh')
            if context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
            if self.action=='ADD':
                add_layer(obj,self.kind,self.kind.title());return {'FINISHED'}
            if self.action=='ADOPT':
                from .environment_adopt import adopt
                sources=[o for o in context.selected_objects if o!=obj and o.type=='MESH']
                if not sources:raise ValueError('Select point meshes, with the terrain active last')
                for source in sources:
                    adopted=adopt(context,obj,source)
                    if adopted:preview(context,obj,adopted)
                return {'FINISHED'}
            if self.action=='MATERIAL_PREVIEW':
                from .environment_materials import refresh
                refresh(obj);return {'FINISHED'}
            layer=active_layer(obj)
            if layer is None:raise ValueError('Add an environment layer first')
            if self.action in {'PAINT','FILL','CLEAR'}:
                group=obj.vertex_groups.get(layer.mask)
                if group is None:raise ValueError('Layer mask is missing')
                if obj.data.users>1:raise ValueError('Make terrain mesh data single-user before painting')
                obj.vertex_groups.active_index=group.index
                if self.action=='PAINT':
                    if layer.kind=='MATERIAL':
                        from .environment_materials import refresh
                        refresh(obj)
                    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
                else:
                    if obj.data.vertices:group.add(list(range(len(obj.data.vertices))),1. if self.action=='FILL' else 0.,'REPLACE')
            elif self.action=='REMOVE':
                if layer.adopt_source:
                    raise ValueError('Disable adopted layers to suppress their contents; retain adoption provenance instead of removing the layer')
                if layer.preview:
                    visual=layer.preview;mesh=visual.data
                    groups=[m.node_group for m in visual.modifiers if m.type=='NODES' and m.node_group]
                    bpy.data.objects.remove(visual,do_unlink=True)
                    if mesh.users==0:bpy.data.meshes.remove(mesh)
                    for tree in groups:
                        if tree.users==0:bpy.data.node_groups.remove(tree)
                # Leave the mask as native editable data rather than deleting authored paint.
                obj.wavelength_environment_layers.remove(obj.wavelength_environment_active)
                obj.wavelength_environment_active=max(0,len(obj.wavelength_environment_layers)-1)
            elif self.action=='REFRESH':
                for item in obj.wavelength_environment_layers:
                    if item.kind=='DISTRIBUTION' and item.palette:preview(context,obj,item)
            elif self.action in {'MANUAL','EDIT'}:
                prototypes=palette(layer)
                if self.action=='MANUAL':
                    address='manual:'+uuid.uuid4().hex;prototype=layer.manual_prototype or prototypes[0]
                    if prototype not in prototypes:raise ValueError('Choose a manual prototype from this layer palette')
                    matrix=Matrix.Translation(context.scene.cursor.location)
                else:
                    items=records(context,obj,layer)
                    if not items:raise ValueError('Layer has no placements to edit')
                    item=min(items,key=lambda r:(Matrix(r['matrix']).translation-context.scene.cursor.location).length_squared)
                    address=item['id'];matrix=Matrix(item['matrix'])
                    prototype=next(o for o in prototypes if identity(o)==item['prototype'])
                proxy=bpy.data.objects.new('Placement correction',prototype.data)
                context.scene.collection.objects.link(proxy);proxy.matrix_world=matrix
                proxy['wl_exclude']=True;proxy['wl_editor_helper']=True
                proxy['wl_environment_edit']=address;proxy['wl_environment_layer']=layer.uid
                proxy['wl_environment_owner']=obj;proxy['wl_environment_prototype']=prototype
                obj.select_set(False);proxy.select_set(True);context.view_layer.objects.active=proxy
                preview(context,obj,layer)
        except (ValueError,RuntimeError,KeyError) as exc:
            self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}

    def edit_action(self,context,proxy):
        owner=proxy['wl_environment_owner']
        layer=next(l for l in owner.wavelength_environment_layers if l.uid==proxy['wl_environment_layer'])
        if self.action not in {'KEEP','DISCARD','DELETE'}:raise ValueError('Keep or discard the current correction first')
        if self.action!='DISCARD':
            set_override(layer,proxy['wl_environment_edit'],proxy['wl_environment_prototype'],
                         proxy.matrix_world,delete=self.action=='DELETE')
        bpy.data.objects.remove(proxy,do_unlink=True)
        owner.select_set(True);context.view_layer.objects.active=owner
        preview(context,owner,layer)
        return {'FINISHED'}


class WL_UL_environment_layers(bpy.types.UIList):
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        layout.prop(item,'enabled',text='');layout.prop(item,'name',text='',emboss=False)
        layout.label(text=item.kind.title())


class WL_PT_environment_layers(bpy.types.Panel):
    bl_label='Environment Layers';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength'
    @classmethod
    def poll(cls,context):return WL_OT_environment_layer.poll(context)
    def draw(self,context):
        layout=self.layout;obj=context.object
        def button(row,text,action,kind='DISTRIBUTION'):
            op=row.operator('wavelength.environment_layer',text=text);op.action=action;op.kind=kind
        if obj.get('wl_environment_edit'):
            layout.label(text='Move, rotate or scale this correction')
            row=layout.row();button(row,'Keep','KEEP');button(row,'Discard','DISCARD');button(layout,'Remove Placement','DELETE');return
        layout.template_list('WL_UL_environment_layers','',obj,'wavelength_environment_layers',obj,'wavelength_environment_active',rows=3)
        row=layout.row();button(row,'Distribution','ADD');button(row,'Exclusion','ADD','EXCLUSION');button(row,'Material','ADD','MATERIAL')
        button(layout,'Adopt Selected Point Sets','ADOPT')
        layer=active_layer(obj)
        if layer is None:return
        row=layout.row();button(row,'Paint Mask','PAINT');button(row,'Fill','FILL');button(row,'Clear','CLEAR')
        layout.label(text='Native Weight Paint: 0 removes, 1 covers')
        if layer.kind=='DISTRIBUTION':
            layout.prop(layer,'palette')
            if layer.mode=='PLACEMENTS':
                layout.prop(layer,'density',text='Retained Fraction');layout.prop(layer,'follow_terrain')
                keys=('seed','scale_min','scale_max','preview_fraction')
            else:keys=('density','cell_size','seed','max_slope','scale_min','scale_max','align_normal','preview_fraction')
            for key in keys:layout.prop(layer,key)
            if layer.palette:
                for prototype in layer.palette.objects:
                    if prototype.type=='MESH':
                        layout.prop(prototype,'wavelength_environment_weight',text=prototype.name)
                        layout.prop(prototype,'wavelength_environment_godot_scene',text='Godot Scene')
            button(layout,'Refresh Distribution','REFRESH')
            layout.prop(layer,'manual_prototype')
            row=layout.row();button(row,'Add Manual at Cursor','MANUAL');button(row,'Edit Nearest to Cursor','EDIT')
            layout.label(text=layer.status)
        elif layer.kind=='MATERIAL':
            layout.prop(obj,'wavelength_environment_material_adapter')
            layout.prop(obj,'wavelength_environment_native_material')
            if obj.wavelength_environment_material_adapter=='PRIVATEER':layout.prop(layer,'biome')
            if layer.biome=='CUSTOM':layout.prop(layer,'material')
            button(layout,'Refresh Material Preview','MATERIAL_PREVIEW')
        else:layout.label(text='Excludes generated instances across this terrain')
        button(layout,'Remove Layer (Keep Mask)','REMOVE')
        layout.operator('wavelength.export_environment',text='Export Environment to Godot')


CLASSES=(WLEnvironmentLayer,WL_OT_environment_layer,WL_UL_environment_layers,WL_PT_environment_layers)


def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Object.wavelength_environment_layers=CollectionProperty(type=WLEnvironmentLayer)
    bpy.types.Object.wavelength_environment_active=IntProperty(min=0)
    bpy.types.Object.wavelength_environment_weight=FloatProperty(name='Palette Weight',default=1,min=0)
    bpy.types.Object.wavelength_environment_native_material=StringProperty(name='Godot Base Material',description='Optional res:// base terrain material, preserved by the Godot adapter')
    bpy.types.Object.wavelength_environment_material_adapter=EnumProperty(name='Material Adapter',items=[('PBR','PBR Material Layers','Portable static base-color painting'),('PRIVATEER','Privateer Biomes','Preserve the native six-biome terrain shader')])
    bpy.types.Object.wavelength_environment_mask_resolution=IntProperty(name='Mask Export Resolution',default=128,min=2)
    from . import environment_godot
    environment_godot.register()


def unregister():
    from . import environment_godot
    environment_godot.unregister()
    for name in ('wavelength_environment_layers','wavelength_environment_active','wavelength_environment_weight','wavelength_environment_native_material','wavelength_environment_material_adapter','wavelength_environment_mask_resolution'):delattr(bpy.types.Object,name)
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
