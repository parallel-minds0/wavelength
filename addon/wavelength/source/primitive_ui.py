"""Persistent parameter controls with transactional regeneration and Blender undo."""
import json
import bpy
from . import primitives, profiles, scene, workspace

DEFAULTS=dict(subdivisions=1,radius=128.,thickness=32.,depth=64.,angle=180.,segments=8,rings=6,steps=8,rise=16.,run=32.,width=128.,landing=0.,direction=0.)
FIELDS={'ARCH':('radius','thickness','depth','angle','segments','direction'),'SPHERE':('radius','subdivisions'),'STAIRS':('steps','rise','run','width','landing','direction')}

def root_for(obj):
    while obj:
        if obj.get('wl_primitive'):return obj
        obj=obj.parent
    return None


def rebuild(root, kind, values, context):
    parts=primitives.generate(kind,values) # Validate everything before changing the scene.
    engine=root.get('wl_engine',context.scene.wavelength.engine)
    unit=root.get('wl_unit_meters',profiles.unit_meters(context.scene.wavelength))
    limit=32768 if profiles.is_source(engine) else 4096
    from mathutils import Vector
    for verts,_ in parts:
        if any(abs(c/unit)>limit for v in verts for c in (root.matrix_world @ (Vector(v)*unit))):
            raise ValueError(f'{engine}: primitive exceeds ±{limit} map units; move it or reduce dimensions')
    old=sorted((o for o in root.children if o.get('wl_primitive_part') is not None),key=lambda o:o['wl_primitive_part'])
    prepared=[]
    try:
        for i,(verts,faces) in enumerate(parts):
            mesh=bpy.data.meshes.new(kind.title()+' solid');mesh.from_pydata([tuple(c*unit for c in v) for v in verts],[],faces);mesh.update()
            source=old[min(i,len(old)-1)] if old else None
            if source:
                for mat in source.data.materials:mesh.materials.append(mat)
                mesh['wl_faces']=source.data.get('wl_faces','{}')
                for polygon in mesh.polygons:
                    if polygon.index<len(source.data.polygons):polygon.material_index=source.data.polygons[polygon.index].material_index
            prepared.append(mesh)
    except Exception:
        for mesh in prepared:bpy.data.meshes.remove(mesh)
        raise
    for i,mesh in enumerate(prepared):
        if i<len(old):
            obj=old[i];previous=obj.data;obj.data=mesh
            if previous.users==0:bpy.data.meshes.remove(previous)
        else:
            obj=bpy.data.objects.new(kind.title()+f' {i+1:02}',mesh);(root.users_collection[0] if root.users_collection else context.collection).objects.link(obj)
            obj.parent=root
        obj['wl_unit_meters']=unit;obj['wl_primitive_part']=i;scene.mark_brush(obj)
        from . import editor
        editor.apply_uv(obj,engine)
    for obj in old[len(parts):]:
        mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    root['wl_primitive']=kind;root['wl_parameters']=json.dumps(values);root['wl_engine']=engine;root['wl_unit_meters']=unit


class WL_OT_primitive(bpy.types.Operator):
    bl_idname='wavelength.primitive';bl_label='Editable BSP Primitive';bl_options={'REGISTER','UNDO'}
    kind:bpy.props.EnumProperty(items=[(k,k.title(),'') for k in FIELDS],default='STAIRS')
    edit:bpy.props.BoolProperty(default=False,options={'HIDDEN'})
    subdivisions:bpy.props.IntProperty(name='Sphere detail (0: 20 faces, 1: 80 faces)',default=1,min=0,max=1)
    radius:bpy.props.FloatProperty(name='Radius (units)',default=128,min=1)
    thickness:bpy.props.FloatProperty(name='Thickness (units)',default=32,min=1)
    depth:bpy.props.FloatProperty(name='Depth (units)',default=64,min=1)
    angle:bpy.props.FloatProperty(name='Arc angle',default=180,min=1,max=360)
    segments:bpy.props.IntProperty(name='Segments',default=8,min=3,max=64)
    rings:bpy.props.IntProperty(name='Rings',default=6,min=2,max=16)
    steps:bpy.props.IntProperty(name='Step count',default=8,min=1,max=64)
    rise:bpy.props.FloatProperty(name='Rise (units)',default=16,min=1)
    run:bpy.props.FloatProperty(name='Run (units)',default=32,min=1)
    width:bpy.props.FloatProperty(name='Width (units)',default=128,min=1)
    landing:bpy.props.FloatProperty(name='Landing (units)',default=0,min=0)
    direction:bpy.props.FloatProperty(name='Direction (degrees)',default=0)
    @classmethod
    def poll(cls,context):
        return context.mode=='OBJECT' and hasattr(context.scene,'wavelength') and context.scene.wavelength.engine!='blender'
    def invoke(self,context,event):
        root=root_for(context.object) if self.edit else None
        if self.edit and not root:self.report({'ERROR'},'Select a generated primitive');return {'CANCELLED'}
        if root:
            self.kind=root['wl_primitive']
            for key,value in json.loads(root['wl_parameters']).items():setattr(self,key,value)
        return context.window_manager.invoke_props_dialog(self)
    def draw(self,context):
        if not self.edit:self.layout.prop(self,'kind')
        for field in FIELDS[self.kind]:self.layout.prop(self,field)
        self.layout.label(text='Dimensions are engine units. Rotation and location remain on the parent.')
    def execute(self,context):
        values={k:getattr(self,k) for k in DEFAULTS}
        root=root_for(context.object) if self.edit else None;created=False
        try:
            primitives.generate(self.kind,values)
            if root is None:
                root=bpy.data.objects.new(self.kind.title(),None);context.collection.objects.link(root);root.location=context.scene.cursor.location;root.empty_display_size=.2;root['wl_exclude']=True;created=True
                context.view_layer.update()
            rebuild(root,self.kind,values,context)
            for obj in context.selected_objects:obj.select_set(False)
            root.select_set(True);context.view_layer.objects.active=root
            return {'FINISHED'}
        except (ValueError,RuntimeError) as exc:
            if created:bpy.data.objects.remove(root,do_unlink=True)
            self.report({'ERROR'},str(exc));return {'CANCELLED'}


class WL_PT_primitive(bpy.types.Panel):
    bl_label='Primitive Parameters';bl_idname='WL_PT_primitive';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength'
    @classmethod
    def poll(cls,context):return workspace.active(context) and root_for(context.object) is not None
    def draw(self,context):
        root=root_for(context.object);self.layout.label(text=root['wl_primitive'].title())
        for key in FIELDS[root['wl_primitive']]:self.layout.label(text=f'{key.title()}: {json.loads(root["wl_parameters"])[key]:g}')
        self.layout.operator('wavelength.primitive',text='Edit Parameters').edit=True


def add_menu(self,context):
    if workspace.active(context):
        for kind in FIELDS:
            op=self.layout.operator('wavelength.primitive',text=kind.title(),icon='MESH_CUBE');op.kind=kind


def register():
    for cls in (WL_OT_primitive,WL_PT_primitive):bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.append(add_menu)


def unregister():
    bpy.types.VIEW3D_MT_mesh_add.remove(add_menu)
    for cls in (WL_PT_primitive,WL_OT_primitive):bpy.utils.unregister_class(cls)
