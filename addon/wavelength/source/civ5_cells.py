"""High-level hex-cell authoring; Blender mesh geometry is only a visualization."""
import base64,hashlib,json,math,struct
from array import array
from pathlib import Path
import bpy,bmesh,gpu
from mathutils import Vector,Quaternion
from bpy.props import EnumProperty,PointerProperty,IntProperty,BoolProperty
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from . import civ5_format,profiles

_FIELDS=civ5_format.FIELDS;_enum_cache={};_documents={};_river_cache={};_handle=None

def active(context):
    obj=context.object
    return obj if obj and obj.get('wl_civ5_document') else None

def document(obj):
    text=obj['wl_civ5_document'];key=text.as_pointer()
    if key not in _documents:_documents[key]=civ5_format.parse(base64.b64decode(text.as_string()))
    return _documents[key]

def selected(obj):return json.loads(obj.get('wl_civ5_selected','[]'))

def signature(mesh):
    h=hashlib.sha256()
    for values,field,code,count in ((mesh.vertices,'co','f',len(mesh.vertices)*3),(mesh.polygons,'loop_total','i',len(mesh.polygons)),(mesh.loops,'vertex_index','i',len(mesh.loops))):
        data=array(code,[0])*count;values.foreach_get(field,data);h.update(data.tobytes())
    return h.hexdigest()

def _palette(name):
    colors={'GRASS':(.24,.48,.18,1),'PLAINS':(.57,.52,.25,1),'DESERT':(.76,.61,.35,1),'TUNDRA':(.43,.47,.39,1),'SNOW':(.85,.9,.92,1),'COAST':(.13,.47,.65,1),'OCEAN':(.04,.17,.36,1)}
    return colors.get(name.removeprefix('TERRAIN_'),(.5,.3,.5,1))

def refresh(obj,indices):
    mesh=obj.data;terrain=mesh.attributes['civ5_terrain'];elevation=mesh.attributes['civ5_elevation']
    for i in indices:
        p=mesh.polygons[i];p.material_index=min(terrain.data[i].value,len(mesh.materials)-1)
        z=(0,.25,.65)[min(elevation.data[i].value,2)]
        for vi in p.vertices:mesh.vertices[vi].co.z=z
    mesh.update();obj['wl_civ5_signature']=signature(mesh)

def import_map(context,path):
    model=civ5_format.parse(Path(path).read_bytes());vertices=[];faces=[]
    for i in range(model.width*model.height):
        x=i%model.width;y=i//model.width;cx=math.sqrt(3)*(x+.5*(y%2));cy=1.5*y
        faces.append(tuple(range(len(vertices),len(vertices)+6)))
        vertices.extend((cx+math.cos(math.radians(30+j*60)),cy+math.sin(math.radians(30+j*60)),0) for j in range(6))
    mesh=bpy.data.meshes.new(Path(path).stem+' Cells');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(Path(path).stem,mesh);context.collection.objects.link(obj)
    text=bpy.data.texts.new(Path(path).stem+' Original Civ5Map');text.write(base64.b64encode(model.raw).decode('ascii'))
    obj['wl_civ5_document']=text;obj['wl_civ5_selected']='[]';obj['wl_civ5_source']=str(path)
    _documents[text.as_pointer()]=model
    obj['wl_role']='CELL_MAP';obj['wl_exclude']=True
    for fi,name in enumerate(_FIELDS):
        attr=mesh.attributes.new('civ5_'+name,'INT','FACE');attr.data.foreach_set('value',[model.tile(i)[fi] for i in range(len(faces))])
    for name in model.tables['terrain'] or ['Unknown']:
        mat=bpy.data.materials.new(name);mat.diffuse_color=_palette(name);mat.use_nodes=True
        mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=mat.diffuse_color;mesh.materials.append(mat)
    refresh(obj,range(len(faces)))
    for o in context.selected_objects:o.select_set(False)
    obj.select_set(True);context.view_layer.objects.active=obj
    context.scene.wavelength.engine='civ5';context.scene.wavelength.map_path=str(path);context.scene.wavelength.map_name=Path(path).stem
    context.scene.wavelength.status=f'Experimental Civ V: {model.width} × {model.height} hex cells'
    for area in context.screen.areas if context.screen else []:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.shading.color_type='MATERIAL';space.overlay.show_floor=False
            rv=space.region_3d;rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO'
            rv.view_location=Vector((math.sqrt(3)*model.width/2,1.5*model.height/2,0))
            rv.view_distance=max(model.width*math.sqrt(3),model.height*1.5)
    if context.area and context.area.type=='VIEW_3D':bpy.ops.wm.tool_set_by_id(name='wavelength.civ5_cells')
    return obj

def export_map(context,path):
    obj=active(context)
    if not obj:raise ValueError('Select a Civ V cell map')
    from .export_scope import Scope
    if not Scope(context.scene,context.view_layer).includes(obj):raise ValueError('The cell map is excluded from export; enable it in the Outliner')
    if context.mode!='OBJECT':raise ValueError('Civ V uses high-level cells; leave mesh Edit Mode')
    model=document(obj)
    if obj.modifiers or signature(obj.data)!=obj.get('wl_civ5_signature'):raise ValueError('Cell visualization geometry changed; edit Civ V cell properties instead of vertices/topology')
    if len(obj.data.polygons)!=model.width*model.height:raise ValueError('Cell count changed')
    changes={i:tuple(obj.data.attributes['civ5_'+name].data[i].value for name in _FIELDS) for i in range(model.width*model.height)}
    Path(path).write_bytes(model.write(changes))
    return len(changes)

def table_items(field):
    def items(self,context):
        obj=active(context) if context else None
        names=document(obj).tables[field] if obj else []
        key=(field,tuple(names))
        if key not in _enum_cache:_enum_cache[key]=[(str(i),name.removeprefix('TERRAIN_').removeprefix('FEATURE_').removeprefix('RESOURCE_').replace('_',' ').title(),'') for i,name in enumerate(names)]+([('255','None','')] if field!='terrain' else [])
        return _enum_cache[key] or [('255','None','')]
    return items

class WLCiv5Settings(bpy.types.PropertyGroup):
    mode:EnumProperty(name='Tool',items=[('SELECT','Select Cells','Click to select; Shift toggles'),('PAINT','Paint Cells','Drag to paint the chosen field')])
    field:EnumProperty(name='Paint',items=[(name,name.replace('_',' ').title(),'') for name in ('terrain','elevation','feature','resource','wonder','river','resource_amount')])
    terrain:EnumProperty(name='Terrain',items=table_items('terrain'))
    feature:EnumProperty(name='Feature',items=table_items('feature'))
    resource:EnumProperty(name='Resource',items=table_items('resource'))
    wonder:EnumProperty(name='Natural Wonder',items=table_items('wonder'))
    elevation:EnumProperty(name='Elevation',items=[('0','Flat',''),('1','Hills',''),('2','Mountain','')])
    river_east:BoolProperty(name='East River')
    river_southeast:BoolProperty(name='Southeast River')
    river_southwest:BoolProperty(name='Southwest River')
    resource_amount:IntProperty(name='Resource Amount',min=0,max=255)

def apply_cells(context,obj,indices):
    if signature(obj.data)!=obj.get('wl_civ5_signature'):raise ValueError('The cell visualization was edited as geometry; restore it before painting cell data')
    settings=context.scene.wavelength_civ5;field=settings.field
    value=(int(settings.river_east)|int(settings.river_southeast)<<1|int(settings.river_southwest)<<2) if field=='river' else int(getattr(settings,field))
    attr=obj.data.attributes['civ5_'+field]
    for i in indices:
        # The upper river byte bits contain metadata unrelated to visible edges.
        attr.data[i].value=(attr.data[i].value&248)|value if field=='river' else value
        if field=='resource':obj.data.attributes['civ5_resource_amount'].data[i].value=(settings.resource_amount or 1) if value!=255 else 0
    refresh(obj,indices)

class WL_OT_civ5_apply(bpy.types.Operator):
    bl_idname='wavelength.civ5_apply';bl_label='Apply to Selected Cells';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        obj=active(context)
        if not obj or not selected(obj):self.report({'WARNING'},'Select cells with the Civ V Cells tool');return {'CANCELLED'}
        try:apply_cells(context,obj,selected(obj))
        except ValueError as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}

class WL_OT_civ5_pick(bpy.types.Operator):
    bl_idname='wavelength.civ5_pick';bl_label='Edit Civ V Cells';bl_options={'REGISTER','UNDO','BLOCKING'}
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT' and active(context) is not None and context.scene.wavelength.engine=='civ5'
    def hit(self,context,event):
        xy=(event.mouse_region_x,event.mouse_region_y);origin=view3d_utils.region_2d_to_origin_3d(context.region,context.region_data,xy);direction=view3d_utils.region_2d_to_vector_3d(context.region,context.region_data,xy)
        obj=active(context);inverse=obj.matrix_world.inverted();hit,_,_,index=obj.ray_cast(inverse@origin,(inverse.to_3x3()@direction).normalized())
        return index if hit else None
    def paint(self,context,event):
        i=self.hit(context,event)
        if i is None or i in self._seen:return
        self._seen.add(i);obj=active(context)
        if context.scene.wavelength_civ5.mode=='PAINT':apply_cells(context,obj,[i])
        else:
            indices=set(selected(obj));indices.symmetric_difference_update({i}) if event.shift else indices.add(i);obj['wl_civ5_selected']=json.dumps(sorted(indices))
            settings=context.scene.wavelength_civ5
            for name in ('terrain','feature','resource','wonder','elevation'):
                value=obj.data.attributes['civ5_'+name].data[i].value
                try:setattr(settings,name,str(value))
                except TypeError:pass
            river=obj.data.attributes['civ5_river'].data[i].value
            settings.river_east=bool(river&1);settings.river_southeast=bool(river&2);settings.river_southwest=bool(river&4)
            settings.resource_amount=obj.data.attributes['civ5_resource_amount'].data[i].value
        context.area.tag_redraw()
    def invoke(self,context,event):
        if signature(active(context).data)!=active(context).get('wl_civ5_signature'):
            self.report({'ERROR'},'Restore the cell visualization geometry before editing cell data');return {'CANCELLED'}
        self._seen=set()
        if context.scene.wavelength_civ5.mode=='SELECT' and not event.shift:active(context)['wl_civ5_selected']='[]'
        self.paint(context,event);context.window_manager.modal_handler_add(self);return {'RUNNING_MODAL'}
    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'}:return {'FINISHED'}
        if event.type=='LEFTMOUSE' and event.value=='RELEASE':return {'FINISHED'}
        if event.type=='MOUSEMOVE':self.paint(context,event)
        return {'RUNNING_MODAL'}

class WL_WT_civ5_cells(bpy.types.WorkSpaceTool):
    bl_space_type='VIEW_3D';bl_context_mode='OBJECT';bl_idname='wavelength.civ5_cells';bl_label='Civ V Cells';bl_description='Select or paint high-level hex cells';bl_icon='ops.generic.select_box'
    bl_keymap=((WL_OT_civ5_pick.bl_idname,{'type':'LEFTMOUSE','value':'PRESS','any':True},None),)

class WL_PT_civ5(bpy.types.Panel):
    bl_label='Civ V Cells (Experimental)';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength'
    @classmethod
    def poll(cls,context):return context.scene.wavelength.engine=='civ5'
    def draw(self,context):
        layout=self.layout;obj=active(context)
        if not obj:layout.label(text='Import a .Civ5Map with wavelength IO');return
        m=document(obj);settings=context.scene.wavelength_civ5
        layout.label(text=f'{m.width} × {m.height} cells · {len(selected(obj))} selected')
        layout.operator('wm.tool_set_by_id',text='Activate Cell Tool').name='wavelength.civ5_cells'
        layout.prop(settings,'mode',expand=True);layout.prop(settings,'field')
        if settings.field=='river':
            for key in ('river_east','river_southeast','river_southwest'):layout.prop(settings,key)
        else:layout.prop(settings,settings.field)
        layout.operator('wavelength.civ5_apply');layout.label(text='Scenario data preserved; not editable')
        if selected(obj):
            i=selected(obj)[0];layout.label(text=f'Cell ({i%m.width}, {i//m.width})')
            for name in ('terrain','feature','resource','elevation'):
                v=obj.data.attributes['civ5_'+name].data[i].value;names=m.tables.get(name,[])
                label=names[v] if v<len(names) else (('Flat','Hills','Mountain')[v] if name=='elevation' and v<3 else 'None' if v==255 else str(v));layout.label(text=name.title()+': '+label)

def draw_selection():
    context=bpy.context;obj=active(context)
    if not obj or context.scene.wavelength.engine!='civ5':return
    points=[]
    for i in selected(obj):
        if i>=len(obj.data.polygons):continue
        vertices=[obj.matrix_world@(obj.data.vertices[v].co) for v in obj.data.polygons[i].vertices]
        for a,b in zip(vertices,vertices[1:]+vertices[:1]):points.extend((a,b))
    shader=gpu.shader.from_builtin('UNIFORM_COLOR');gpu.state.depth_test_set('NONE');gpu.state.line_width_set(2)
    try:
        # Cache the river overlay; bulk attribute reads avoid a Python scan of
        # every map cell on each redraw. Each shared river edge is stored once.
        values=array('i',[0])*len(obj.data.polygons);obj.data.attributes['civ5_river'].data.foreach_get('value',values)
        key=(obj.data.as_pointer(),obj.get('wl_civ5_signature'),values.tobytes(),tuple(v for row in obj.matrix_world for v in row))
        cached=_river_cache.get(obj.as_pointer())
        if not cached or cached[0]!=key:
            rivers=[]
            for i,bits in enumerate(values):
                if not bits&7:continue
                face=obj.data.polygons[i]
                for flag,a,b in ((1,5,0),(2,4,5),(4,3,4)):
                    if bits&flag:rivers.extend(obj.matrix_world@obj.data.vertices[face.vertices[j]].co for j in (a,b))
            cached=(key,batch_for_shader(shader,'LINES',{'pos':rivers}) if rivers else None);_river_cache[obj.as_pointer()]=cached
        shader.bind();shader.uniform_float('color',(.08,.5,1,1))
        if cached[1]:cached[1].draw(shader)
        if points:shader.uniform_float('color',(.1,1,1,1));batch_for_shader(shader,'LINES',{'pos':points}).draw(shader)
    finally:gpu.state.line_width_set(1);gpu.state.depth_test_set('LESS_EQUAL')

CLASSES=(WLCiv5Settings,WL_OT_civ5_apply,WL_OT_civ5_pick,WL_PT_civ5)
def register():
    global _handle
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.wavelength_civ5=PointerProperty(type=WLCiv5Settings)
    bpy.utils.register_tool(WL_WT_civ5_cells,after={'builtin.select_box'},separator=True)
    if not bpy.app.background:_handle=bpy.types.SpaceView3D.draw_handler_add(draw_selection,(),'WINDOW','POST_VIEW')
def unregister():
    if _handle:bpy.types.SpaceView3D.draw_handler_remove(_handle,'WINDOW')
    bpy.utils.unregister_tool(WL_WT_civ5_cells);del bpy.types.Scene.wavelength_civ5
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
    _documents.clear();_enum_cache.clear();_river_cache.clear()
