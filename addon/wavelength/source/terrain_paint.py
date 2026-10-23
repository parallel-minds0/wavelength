"""Non-destructive height/mask painting on a normalized terrain control surface."""
import math
import bpy,gpu
from bpy.props import EnumProperty
from mathutils import Vector
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from . import profiles,workspace
_RUNNING=[]
PAINT_TYPES=(('RAISE','Raise / Lower','BRUSH_DATA'),('SMOOTH','Smooth','MOD_SMOOTH'),('TEXTURE','Texture Blend','TEXTURE'))


def paint_button(layout,context,text=''):
    mode=context.object.wavelength_terrain.paint_mode
    icon=next(icon for key,_,icon in PAINT_TYPES if key==mode)
    layout.operator_menu_hold('wavelength.terrain_paint',text=text,icon=icon,menu='WL_MT_terrain_paint_types')


class WL_MT_terrain_paint_types(bpy.types.Menu):
    bl_label='Terrain Paint Type'
    def draw(self,context):
        self.layout.operator_context='INVOKE_REGION_WIN'
        current=context.object.wavelength_terrain.paint_mode
        for mode,label,icon in PAINT_TYPES:
            self.layout.operator('wavelength.terrain_paint',text=label,icon=icon,depress=current==mode).mode=mode


def input_value(modifier,identifier,value=None,write=False):
    if hasattr(modifier,'properties'):
        prop=getattr(modifier.properties.inputs,identifier)
        if write:prop.value=value
        return prop.value
    if write:modifier[identifier]=value
    return modifier[identifier]


def full_surface(obj):
    previous=[]
    for modifier in obj.modifiers:
        if modifier.type=='NODES' and modifier.node_group and modifier.node_group.get('wl_generator') in {'wavelength.geometry_nodes.heightfield','wavelength.terrain.shared_deformation'}:
            socket=next((s for s in modifier.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name=='Flat Placement'),None)
            if socket:
                value=input_value(modifier,socket.identifier);input_value(modifier,socket.identifier,False,True);previous.append((modifier,socket.identifier,value))
    if previous:obj.update_tag();bpy.context.view_layer.update()
    return previous


def restore_surface(obj,previous):
    if previous:
        for modifier,identifier,value in previous:input_value(modifier,identifier,value,True)
        obj.update_tag();bpy.context.view_layer.update()


def ensure_control(obj):
    if obj.data.vertices:return
    name='Wavelength · Terrain Control Grid · v1';group=bpy.data.node_groups.get(name)
    if group is None:
        group=bpy.data.node_groups.new(name,'GeometryNodeTree');group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
        grid=group.nodes.new('GeometryNodeMeshGrid');grid.inputs['Size X'].default_value=grid.inputs['Size Y'].default_value=1
        grid.inputs['Vertices X'].default_value=grid.inputs['Vertices Y'].default_value=65
        output=group.nodes.new('NodeGroupOutput');group.links.new(grid.outputs['Mesh'],output.inputs['Geometry'])
    data=bpy.data.meshes.new('.Terrain controls');temporary=bpy.data.objects.new('.Terrain controls',data);bpy.context.scene.collection.objects.link(temporary)
    try:
        modifier=temporary.modifiers.new('Control grid','NODES');modifier.node_group=group;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
        mesh=bpy.data.meshes.new_from_object(temporary.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
        old=obj.data;mesh.materials.clear()
        for material in old.materials:mesh.materials.append(material)
        obj.data=mesh
        if old.users==0:bpy.data.meshes.remove(old)
        mesh.attributes.new('wl_terrain_blend','FLOAT','POINT')
    finally:bpy.data.objects.remove(temporary,do_unlink=True);bpy.data.meshes.remove(data)


def preview_material(obj):
    base=next((m for m in obj.data.materials if m),None);paint=obj.wavelength_terrain.paint_material
    if paint is None or profiles.is_source(obj.get('wl_owner_profile','blender')):return base
    name=obj.get('wl_terrain_preview_material','');material=bpy.data.materials.get(name)
    signature=(base.name if base else '')+'|'+paint.name
    if material and material.get('wl_terrain_layers')==signature:return material
    if material is None:material=bpy.data.materials.new(obj.name+' Terrain Layers');obj['wl_terrain_preview_material']=material.name
    material.use_nodes=True;nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
    output=nodes.new('ShaderNodeOutputMaterial');shader=nodes.new('ShaderNodeBsdfPrincipled');shader.inputs['Roughness'].default_value=1;links.new(shader.outputs[0],output.inputs['Surface'])
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map='wavelength'
    def color(source):
        image=next((n.image for n in source.node_tree.nodes if n.type=='TEX_IMAGE' and n.image),None) if source and source.use_nodes else None
        if image:
            tex=nodes.new('ShaderNodeTexImage');tex.image=image;links.new(uv.outputs[0],tex.inputs['Vector']);return tex.outputs['Color']
        rgb=nodes.new('ShaderNodeRGB');rgb.outputs[0].default_value=source.diffuse_color if source else (.5,.5,.5,1);return rgb.outputs[0]
    mask=nodes.new('ShaderNodeAttribute');mask.attribute_name='wl_terrain_blend'
    mix=nodes.new('ShaderNodeMixRGB');links.new(mask.outputs['Fac'],mix.inputs[0]);links.new(color(base),mix.inputs[1]);links.new(color(paint),mix.inputs[2]);links.new(mix.outputs[0],shader.inputs['Base Color'])
    material['wl_terrain_layers']=signature;return material


def base_heights(obj):
    """Read the evaluated node surface once per paint session for smoothing."""
    from mathutils.kdtree import KDTree
    previous=full_surface(obj)
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:
        tree=KDTree(len(mesh.vertices))
        for i,vertex in enumerate(mesh.vertices):tree.insert(Vector((vertex.co.x,vertex.co.y,0)),i)
        tree.balance();s=obj.wavelength_terrain;unit=obj['wl_unit_meters']
        from . import terrain_face
        quad=terrain_face.corners(obj) if obj.get('wl_terrain_face_corners') else None
        return [mesh.vertices[tree.find(terrain_face.position(obj,v.co.x+.5,v.co.y+.5,quad) if quad else Vector((v.co.x*s.width*unit,v.co.y*s.length*unit,0)))[1]].co.z-v.co.z for v in obj.data.vertices]
    finally:evaluated.to_mesh_clear();restore_surface(obj,previous)


def network_stroke(items,base,point,normal,mode,radius,strength,opacity,invert=False):
    """A world-space brush spans connected patches regardless of their planes."""
    from . import terrain_sew
    world={o:terrain_sew.positions(o,base[o]) for o in items};touched=0
    for obj in items:
        attr=obj.data.attributes['wl_terrain_vector'];mask=obj.data.attributes.get('wl_terrain_blend');inverse=obj.matrix_world.inverted().to_3x3();adjacent=None
        if mode=='SMOOTH':
            adjacent=[[] for _ in obj.data.vertices]
            for e in obj.data.edges:
                a,b=e.vertices;adjacent[a].append(b);adjacent[b].append(a)
        for index,p in enumerate(world[obj]):
            distance=(p-point).length
            if distance>=radius:continue
            weight=(1-distance/radius)**2;touched+=1
            if mode=='TEXTURE':mask.data[index].value=max(0,min(1,mask.data[index].value+(-1 if invert else 1)*opacity*weight))
            elif mode=='SMOOTH':
                row=adjacent[index]
                if row:attr.data[index].vector+=inverse@((sum((world[obj][i] for i in row),Vector())/len(row)-p)*opacity*weight)
            else:attr.data[index].vector+=inverse@(normal*strength*weight*(-1 if invert else 1))
            if mode!='TEXTURE' and obj.data.attributes['wl_terrain_seam_weight'].data[index].value>.99999:
                obj.data.attributes['wl_terrain_seam_target'].data[index].vector=base[obj][index]+Vector((0,0,obj.data.vertices[index].co.z))+attr.data[index].vector
        obj.data.update();obj.update_tag()
    terrain_sew.constrain(items,base,geometry=mode!='TEXTURE')
    return touched


def stroke(obj,local,mode,radius,strength,opacity,invert=False,base=None):
    """Apply one falloff stamp; the node graph interprets the control data."""
    s=obj.wavelength_terrain;unit=float(obj['wl_unit_meters']);width=s.width*unit;length=s.length*unit
    vertices=obj.data.vertices;mask=obj.data.attributes.get('wl_terrain_blend');radius=max(radius,1e-8)
    old=[v.co.z for v in vertices];neighbors=None
    from . import terrain_face
    quad=terrain_face.corners(obj) if obj.get('wl_terrain_face_corners') else None
    if mode=='SMOOTH':
        if base is None:base=base_heights(obj)
        neighbors=[[] for _ in vertices]
        for edge in obj.data.edges:
            a,b=edge.vertices;neighbors[a].append(b);neighbors[b].append(a)
    touched=0
    for index,vertex in enumerate(vertices):
        if quad:
            p=terrain_face.position(obj,vertex.co.x+.5,vertex.co.y+.5,quad);delta=obj.matrix_world.to_3x3()@Vector((p.x-local.x,p.y-local.y,0))
        else:delta=obj.matrix_world.to_3x3()@Vector((vertex.co.x*width-local.x,vertex.co.y*length-local.y,0))
        distance=delta.length
        if distance>=radius:continue
        weight=(1-distance/radius)**2;touched+=1
        if mode=='TEXTURE':mask.data[index].value=max(0,min(1,mask.data[index].value+(-1 if invert else 1)*opacity*weight))
        elif mode=='SMOOTH':
            adjacent=neighbors[index]
            if adjacent:vertex.co.z=old[index]+(sum(old[i]+base[i] for i in adjacent)/len(adjacent)-old[index]-base[index])*opacity*weight
        else:vertex.co.z=old[index]+(-1 if invert else 1)*strength*weight/max((obj.matrix_world.to_3x3()@Vector((0,0,1))).length,1e-8)
    obj.data.update();obj.update_tag();return touched


class WL_OT_terrain_paint(bpy.types.Operator):
    bl_idname='wavelength.terrain_paint';bl_label='Paint Terrain';bl_options={'REGISTER','UNDO','BLOCKING'}
    bl_description='Paint terrain with the selected type; hold the button to choose Raise / Lower, Smooth or Texture Blend'
    mode:EnumProperty(items=[('CURRENT','Current','Use the selected terrain paint type')]+[(key,label,label) for key,label,_ in PAINT_TYPES],default='CURRENT',options={'SKIP_SAVE'})
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.object and context.object.get('wl_terrain') and context.object.get('wl_procedural_state')=='PROCEDURAL' and context.mode=='OBJECT'
    def invoke(self,context,event):
        area=context.area if context.area.type=='VIEW_3D' else next((a for a in context.screen.areas if a.type=='VIEW_3D'),None)
        if area is None:self.report({'ERROR'},'Open a 3D viewport');return {'CANCELLED'}
        self.obj=context.object;s=self.obj.wavelength_terrain
        from . import terrain
        if not terrain.paintable(self.obj):
            self.report({'ERROR'},'Create Paintable Displacement from the flat terrain plane first');return {'CANCELLED'}
        if self.mode!='CURRENT':s.paint_mode=self.mode
        from . import terrain_sew
        try:
            self.members=terrain_sew.network(self.obj)
            self.connected=bool(self.obj.get('wl_terrain_vector_surface'))
            if any(o.get('wl_procedural_state')!='PROCEDURAL' for o in self.members):raise ValueError('All connected surfaces must remain procedural to paint; Unsew finalized neighbours first')
            terrain_sew.pairs(self.members)
        except ValueError as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        if s.paint_mode=='TEXTURE' and profiles.is_source(self.obj['wl_owner_profile']):
            material=next((m for m in self.obj.data.materials if m),None)
            if not material or not material.get('wl_source_blend'):
                self.report({'ERROR'},'Assign a Source WorldVertexTransition material to paint its two texture layers');return {'CANCELLED'}
            for obj in self.members:
                other=next((m for m in obj.data.materials if m),None)
                if other!=material:self.report({'ERROR'},'Connected texture painting requires the same transition material on every surface');return {'CANCELLED'}
        elif s.paint_mode=='TEXTURE':
            layers={(next((m for m in o.data.materials if m),None),o.wavelength_terrain.paint_material) for o in self.members}
            if len(layers)>1:self.report({'ERROR'},'Connected texture painting requires matching base and paint materials');return {'CANCELLED'}
        if not self.obj.get('wl_terrain_paint_initialized'):
            s.paint_radius=max(s.width,s.length)*.1;s.paint_strength=max(s.amplitude*.1,max(s.width,s.length)*.01,.1);self.obj['wl_terrain_paint_initialized']=True
        elif s.paint_strength<=.10001 and s.amplitude==0:
            s.paint_strength=max(s.width,s.length)*.01
        for obj in self.members:obj.wavelength_terrain.flat_preview=False
        from . import terrain
        terrain.update(self.obj)
        context.view_layer.update()
        if self.connected:
            try:
                for obj in self.members:terrain_sew.prepare(obj)
                context.view_layer.update();self.network_base=terrain_sew.frames(self.members)
            except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        self.base=base_heights(self.obj) if not self.connected else None
        if s.paint_mode=='TEXTURE' and area.spaces.active.shading.type in {'SOLID','WIREFRAME'}:area.spaces.active.shading.type='MATERIAL'
        self.area=area;self.region=next(r for r in area.regions if r.type=='WINDOW');self.down=False;self.hit=None;self.last=None;self.changed=False
        self.handle=bpy.types.SpaceView3D.draw_handler_add(self._draw,(),'WINDOW','POST_VIEW');_RUNNING.append(self)
        self.area.header_text_set('Terrain paint: drag LMB · Ctrl lower/erase · Shift smooth · wheel radius · Esc/Enter finish · Ctrl+Z undo after finishing')
        self.timer=context.window_manager.event_timer_add(.05,window=context.window);self.mouse=(event.mouse_x,event.mouse_y)
        context.window.cursor_modal_set('PAINT_BRUSH');context.window_manager.modal_handler_add(self);return {'RUNNING_MODAL'}
    def remove(self,context):
        if getattr(self,'timer',None):context.window_manager.event_timer_remove(self.timer);self.timer=None
        if self.handle:bpy.types.SpaceView3D.draw_handler_remove(self.handle,'WINDOW');self.handle=None
        self.area.header_text_set(None);self.area.tag_redraw();context.window.cursor_modal_restore()
        if self in _RUNNING:_RUNNING.remove(self)
    def _draw(self):
        if not self.hit or bpy.context.area!=self.area:return
        co,normal=self.hit;radius=self.obj.wavelength_terrain.paint_radius*self.obj['wl_unit_meters']
        from .brush_create import _axis_basis
        u,v,n=_axis_basis(normal);ring=[co+(u*math.cos(i*math.tau/64)+v*math.sin(i*math.tau/64))*radius for i in range(65)]
        shader=gpu.shader.from_builtin('UNIFORM_COLOR');shader.bind();shader.uniform_float('color',(1,.55,.1,1));gpu.state.depth_test_set('NONE')
        try:batch_for_shader(shader,'LINE_STRIP',{'pos':ring}).draw(shader)
        finally:gpu.state.depth_test_set('LESS_EQUAL')
    def modal(self,context,event):
        if event.type in {'ESC','RET','NUMPAD_ENTER','RIGHTMOUSE'} and event.value=='PRESS':self.remove(context);return {'FINISHED'} if self.changed else {'CANCELLED'}
        if not workspace.active(context):self.remove(context);return {'FINISHED'} if self.changed else {'CANCELLED'}
        if event.type in {'WHEELUPMOUSE','WHEELDOWNMOUSE'}:
            s=self.obj.wavelength_terrain;s.paint_radius*=1.1 if event.type=='WHEELUPMOUSE' else 1/1.1;self.area.tag_redraw();return {'RUNNING_MODAL'}
        if event.type=='MIDDLEMOUSE' or event.alt:
            self.down=False;self.last=None;return {'PASS_THROUGH'}
        if event.type=='TIMER' and not self.down:return {'RUNNING_MODAL'}
        if event.type in {'LEFTMOUSE','MOUSEMOVE'}:self.mouse=(event.mouse_x,event.mouse_y)
        if event.type=='LEFTMOUSE' and event.value=='RELEASE':self.down=False;self.last=None
        x=self.mouse[0]-self.region.x;y=self.mouse[1]-self.region.y
        if not (0<=x<self.region.width and 0<=y<self.region.height):return {'PASS_THROUGH'}
        if event.type in {'LEFTMOUSE','MOUSEMOVE','TIMER'}:
            rv=self.area.spaces.active.region_3d;origin=view3d_utils.region_2d_to_origin_3d(self.region,rv,(x,y));direction=view3d_utils.region_2d_to_vector_3d(self.region,rv,(x,y))
            best=None
            for obj in self.members:
                inverse=obj.matrix_world.inverted();evaluated=obj.evaluated_get(context.evaluated_depsgraph_get());hit,co,normal,_=evaluated.ray_cast(inverse@origin,(inverse.to_3x3()@direction).normalized())
                if hit:
                    world=obj.matrix_world@co;distance=(world-origin).length
                    if best is None or distance<best[0]:best=(distance,obj,co,world,(inverse.transposed().to_3x3()@normal).normalized())
            hit=best is not None
            self.hit=(best[3],best[4]) if hit else None
            if event.type=='LEFTMOUSE':self.down=event.value=='PRESS';self.last=None
            if hit and self.down:
                s=self.obj.wavelength_terrain;unit=self.obj['wl_unit_meters'];radius=s.paint_radius*unit
                if event.type=='TIMER' or self.last is None or (best[3]-self.last).length>radius*.08:
                    mode='SMOOTH' if event.shift else s.paint_mode
                    rate=.2 if event.type=='TIMER' else 1.
                    if self.connected:changed=network_stroke(self.members,self.network_base,best[3],best[4],mode,radius,s.paint_strength*unit*rate,s.paint_opacity*rate,event.ctrl)
                    else:changed=stroke(self.obj,best[2],mode,radius,s.paint_strength*unit*rate,s.paint_opacity*rate,event.ctrl,self.base)
                    self.changed=bool(changed) or self.changed;self.last=best[3].copy()
            self.area.tag_redraw();return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}


def register():
    bpy.utils.register_class(WL_OT_terrain_paint)
    bpy.utils.register_class(WL_MT_terrain_paint_types)
def unregister():
    for op in list(_RUNNING):
        if getattr(op,'timer',None):bpy.context.window_manager.event_timer_remove(op.timer);op.timer=None
        if op.handle:bpy.types.SpaceView3D.draw_handler_remove(op.handle,'WINDOW');op.handle=None
        try:op.area.header_text_set(None)
        except ReferenceError:pass
    _RUNNING.clear()
    bpy.utils.unregister_class(WL_MT_terrain_paint_types)
    try:bpy.utils.unregister_class(WL_OT_terrain_paint)
    except RuntimeError:pass
