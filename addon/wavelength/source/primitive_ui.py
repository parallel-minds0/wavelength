"""Persistent parameter controls with transactional regeneration and Blender undo."""
import json
import bpy
from . import primitives, profiles, scene, workspace, diagnostics

DEFAULTS=dict(sphere_type='ICO',subdivisions=1,radius=128.,thickness=32.,depth=64.,angle=180.,segments=8,rings=6,steps=8,rise=16.,run=32.,width=128.,landing=0.,curved=False,curve_angle=90.,inner_radius=64.,direction=0.)
FIELDS={'ARCH':('radius','thickness','depth','angle','segments','direction'),'SPHERE':('sphere_type','radius','subdivisions','segments','rings','direction'),'STAIRS':('steps','rise','run','width','landing','curved','curve_angle','inner_radius','direction')}
_SELECTED_ROOTS=set()
_EDITING_ROOTS=set()
_KEYMAPS=[]


def is_assembly_root(obj):
    return bool(obj is not None and (obj.get('wl_primitive') or obj.get('wl_assembly')))


def fields_for(kind, values=None):
    if kind=='SPHERE':
        st=str((values or {}).get('sphere_type','ICO')).upper()
        return ('sphere_type','radius','segments','rings','direction') if st=='UV' else ('sphere_type','radius','subdivisions','direction')
    if kind=='STAIRS':
        curved=bool((values or {}).get('curved',False))
        return ('steps','rise','width','landing','curved','curve_angle','inner_radius','direction') if curved else ('steps','rise','run','width','landing','curved','direction')
    return FIELDS[kind]


def root_for(obj):
    while obj:
        if is_assembly_root(obj):return obj
        obj=obj.parent
    return None


def parts_for(root):
    if not root:return []
    return sorted(
        (o for o in root.children if o.get('wl_primitive_part') is not None or o.get('wl_assembly_part') is not None or o.get('wl_role')=='BRUSH'),
        key=lambda o:(int(o.get('wl_primitive_part',o.get('wl_assembly_part',999999))),o.name)
    )


def apply_assembly_lock(root):
    if not root:return
    locked=bool(root.get('wl_assembly_locked',True))
    locks=(locked,locked,locked)
    for obj in parts_for(root):
        if tuple(obj.lock_location)!=locks:obj.lock_location=locks
        if tuple(obj.lock_rotation)!=locks:obj.lock_rotation=locks
        if tuple(obj.lock_scale)!=locks:obj.lock_scale=locks


def select_assembly(root, context=None, select=True):
    context=context or bpy.context
    if not root:return
    for obj in (root,*parts_for(root)):
        try:obj.select_set(select)
        except RuntimeError:pass
    if select and context and getattr(context,'view_layer',None):
        context.view_layer.objects.active=root


def enter_assembly_edit_mode(root, context=None, preferred_part=None):
    """Enter Blender Multi-Object Edit Mode across all mesh parts of an assembly."""
    context=context or bpy.context
    if not root:return False
    mesh_parts=[p for p in parts_for(root) if p.type=='MESH']
    if not mesh_parts:return False
    if getattr(context,'mode','OBJECT')!='OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in list(getattr(context,'selected_objects',())):
        try:obj.select_set(False)
        except RuntimeError:pass
    for obj in (root,*mesh_parts):
        try:obj.select_set(True)
        except RuntimeError:pass
    active_part=preferred_part if preferred_part in mesh_parts else mesh_parts[0]
    if getattr(context,'view_layer',None):
        context.view_layer.objects.active=active_part
    from . import editor
    for p in mesh_parts:
        if p.get('wl_role')=='BRUSH':
            editor.note_edit_session(p)
    bpy.ops.object.mode_set(mode='EDIT')
    key=root.as_pointer()
    _EDITING_ROOTS.add(key)
    _SELECTED_ROOTS.add(key)
    return True


def exit_assembly_edit_mode(root, context=None):
    """Exit Multi-Object Edit Mode on an assembly and restore root active selection."""
    context=context or bpy.context
    if not root:return False
    if getattr(context,'mode','OBJECT')!='OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    key=root.as_pointer()
    _EDITING_ROOTS.discard(key)
    if root.get('wl_assembly_locked',True):
        select_assembly(root,context,True)
        _SELECTED_ROOTS.add(key)
    return True


def sync_assemblies(force=False):
    if bpy.app.background and not force:return None
    try:
        wm=getattr(bpy.context,'window_manager',None)
        targets=[(w.scene,w.view_layer) for w in wm.windows] if wm and wm.windows else [(getattr(bpy.context,'scene',None),getattr(bpy.context,'view_layer',None))]
        for scene_data,view_layer in targets:
            if not scene_data or not view_layer:continue
            active=view_layer.objects.active
            if active and active.mode!='OBJECT':
                r=root_for(active)
                if r and r.get('wl_assembly_locked',True):
                    _EDITING_ROOTS.add(r.as_pointer())
                continue
            for obj in scene_data.objects:
                if not is_assembly_root(obj):continue
                if 'wl_assembly_locked' not in obj:obj['wl_assembly_locked']=True
                apply_assembly_lock(obj)
                key=obj.as_pointer()
                if not obj.get('wl_assembly_locked',True):
                    _SELECTED_ROOTS.discard(key)
                    _EDITING_ROOTS.discard(key)
                    continue
                parts=parts_for(obj)
                members=[obj,*parts]
                sel=[m for m in members if m.select_get()]
                if key in _EDITING_ROOTS:
                    _EDITING_ROOTS.discard(key)
                    if sel or active in members:
                        for m in members:
                            try:m.select_set(True)
                            except RuntimeError:pass
                        view_layer.objects.active=obj
                        _SELECTED_ROOTS.add(key)
                        continue
                was_selected=key in _SELECTED_ROOTS
                if not sel:
                    _SELECTED_ROOTS.discard(key)
                elif len(sel)==len(members):
                    _SELECTED_ROOTS.add(key)
                    if active in parts:
                        view_layer.objects.active=obj
                elif not was_selected:
                    for m in members:
                        try:m.select_set(True)
                        except RuntimeError:pass
                    if active in members:
                        view_layer.objects.active=obj
                    _SELECTED_ROOTS.add(key)
                else:
                    if active in parts and sel==[active]:
                        for m in members:
                            try:m.select_set(True)
                            except RuntimeError:pass
                        view_layer.objects.active=obj
                        _SELECTED_ROOTS.add(key)
                    else:
                        for m in members:
                            try:m.select_set(False)
                            except RuntimeError:pass
                        _SELECTED_ROOTS.discard(key)
    except (RuntimeError,ReferenceError,AttributeError):
        pass
    return .08


def rebuild(root, kind, values, context):
    settings = getattr(context.scene, 'wavelength', None)
    engine = root.get('wl_engine', settings.engine if settings else 'blender')
    is_engine = bool(profiles.get(engine).get('brush_semantics', False))
    unit = float(root.get('wl_unit_meters', profiles.unit_meters(settings) if settings else 1.0))
    grid_step = profiles.grid_step_units(settings) if (is_engine and settings) else (profiles.active_snap_step_units(settings, context) if settings else None)
    gen_values = dict(values)
    parts = primitives.generate(kind, gen_values, validate_bsp=is_engine, grid_step=grid_step)
    if is_engine:
        limit = 32768 if profiles.is_source(engine) else 4096
        from mathutils import Vector
        for verts, _ in parts:
            if any(abs(c / unit) > limit for v in verts for c in (root.matrix_world @ (Vector(v) * unit))):
                raise ValueError(f'{engine}: primitive exceeds ±{limit} map units; move it or reduce dimensions')
    old = parts_for(root)
    prepared = []
    try:
        for i, (verts, faces) in enumerate(parts):
            mesh = bpy.data.meshes.new(kind.title() + ' solid')
            mesh.from_pydata([tuple(c * unit for c in v) for v in verts], [], faces)
            mesh.update()
            source = old[min(i, len(old) - 1)] if old else None
            if source:
                for mat in source.data.materials:
                    mesh.materials.append(mat)
                mesh['wl_faces'] = source.data.get('wl_faces', '{}')
                for polygon in mesh.polygons:
                    if polygon.index < len(source.data.polygons):
                        polygon.material_index = source.data.polygons[polygon.index].material_index
            prepared.append(mesh)
    except Exception:
        for mesh in prepared:
            bpy.data.meshes.remove(mesh)
        raise
    for i, mesh in enumerate(prepared):
        if i < len(old):
            obj = old[i]
            previous = obj.data
            obj.data = mesh
            if previous.users == 0:
                bpy.data.meshes.remove(previous)
        else:
            obj = bpy.data.objects.new(kind.title() + f' {i+1:02}', mesh)
            (root.users_collection[0] if root.users_collection else context.collection).objects.link(obj)
            obj.parent = root
        obj['wl_unit_meters'] = unit
        obj['wl_primitive_part'] = i
        if is_engine:
            scene.mark_brush(obj)
            from . import editor
            editor.apply_uv(obj, engine)
        else:
            obj['wl_assembly_part'] = i
    for obj in old[len(parts):]:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    root['wl_primitive'] = kind
    root['wl_parameters'] = json.dumps(values)
    root['wl_engine'] = engine
    root['wl_unit_meters'] = unit
    if 'wl_assembly_locked' not in root:
        root['wl_assembly_locked'] = True
    apply_assembly_lock(root)


class WL_OT_assembly_editmode_toggle(bpy.types.Operator):
    bl_idname='wavelength.assembly_editmode_toggle';bl_label='Toggle Assembly Multi-Object Edit Mode';bl_options={'REGISTER','UNDO'}

    def _target_root(self,context):
        active=getattr(context,'edit_object',None) or getattr(context,'object',None)
        root=root_for(active)
        if not root:return None,active
        locked=bool(root.get('wl_assembly_locked',True))
        if getattr(context,'mode','OBJECT')=='OBJECT':
            if locked or active==root:
                return root,active
            return None,active
        if locked or root.as_pointer() in _EDITING_ROOTS:
            return root,active
        return None,active

    def invoke(self,context,event):
        root,_=self._target_root(context)
        if root is None:
            return {'PASS_THROUGH'}
        return self.execute(context)

    def execute(self,context):
        root,active=self._target_root(context)
        if root is None:
            active=getattr(context,'edit_object',None) or getattr(context,'object',None)
            root=root_for(active)
        if root is None:
            return {'PASS_THROUGH'}
        if getattr(context,'mode','OBJECT')=='OBJECT':
            preferred=active if (active and active!=root and active.type=='MESH') else None
            return {'FINISHED'} if enter_assembly_edit_mode(root,context,preferred) else {'PASS_THROUGH'}
        return {'FINISHED'} if exit_assembly_edit_mode(root,context) else {'PASS_THROUGH'}


class WL_OT_primitive_lock(bpy.types.Operator):
    bl_idname='wavelength.primitive_lock';bl_label='Toggle Whole-Object Assembly Mode';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        active=getattr(context,'edit_object',None) or getattr(context,'object',None)
        root=root_for(active)
        if not root:return {'CANCELLED'}
        if getattr(context,'mode','OBJECT')!='OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        locked=not bool(root.get('wl_assembly_locked',True))
        root['wl_assembly_locked']=locked
        apply_assembly_lock(root)
        key=root.as_pointer()
        _EDITING_ROOTS.discard(key)
        if locked:
            select_assembly(root,context,True)
            _SELECTED_ROOTS.add(key)
        else:
            _SELECTED_ROOTS.discard(key)
        return {'FINISHED'}


class WL_OT_stair_curve_toggle(bpy.types.Operator):
    bl_idname='wavelength.stair_curve_toggle';bl_label='Toggle Curved Staircase';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        root=root_for(context.object)
        if not root or root.get('wl_primitive')!='STAIRS':return {'CANCELLED'}
        if getattr(context,'mode','OBJECT')!='OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            _EDITING_ROOTS.discard(root.as_pointer())
        values=dict(DEFAULTS,**json.loads(root.get('wl_parameters','{}')))
        values['curved']=not bool(values.get('curved',False))
        try:
            rebuild(root,'STAIRS',values,context)
            if root.get('wl_assembly_locked',True):
                select_assembly(root,context,True)
                _SELECTED_ROOTS.add(root.as_pointer())
            return {'FINISHED'}
        except (ValueError,RuntimeError) as exc:
            self.report({'ERROR'},diagnostics.error(self.bl_idname, exc));return {'CANCELLED'}


class WL_OT_primitive(bpy.types.Operator):
    bl_idname='wavelength.primitive';bl_label='Editable BSP Primitive';bl_options={'REGISTER','UNDO'}
    kind:bpy.props.EnumProperty(items=[(k,k.title(),'') for k in FIELDS],default='STAIRS')
    edit:bpy.props.BoolProperty(default=False,options={'HIDDEN'})
    sphere_type:bpy.props.EnumProperty(name='Sphere Type',items=[('ICO','Icosphere (Triangles)','Geodesic icosphere with 20 or 80 triangular faces'),('UV','UV Sphere (Quads)','Latitude/longitude sphere with planar quad bands and triangular poles')],default='ICO')
    subdivisions:bpy.props.IntProperty(name='Sphere detail (0: 20 faces, 1: 80 faces)',default=1,min=0,max=1)
    radius:bpy.props.FloatProperty(name='Radius (units)',default=128,min=0.01)
    thickness:bpy.props.FloatProperty(name='Thickness (units)',default=32,min=0.01)
    depth:bpy.props.FloatProperty(name='Depth (units)',default=64,min=0.01)
    angle:bpy.props.FloatProperty(name='Arc angle',default=180,min=1,max=360)
    segments:bpy.props.IntProperty(name='Segments',default=8,min=3,max=64)
    rings:bpy.props.IntProperty(name='Rings',default=6,min=2,max=32)
    steps:bpy.props.IntProperty(name='Step count',default=8,min=1,max=64)
    rise:bpy.props.FloatProperty(name='Rise (units)',default=16,min=0.01)
    run:bpy.props.FloatProperty(name='Run (units)',default=32,min=0.01)
    width:bpy.props.FloatProperty(name='Width (units)',default=128,min=0.01)
    landing:bpy.props.FloatProperty(name='Landing (units)',default=0,min=0)
    curved:bpy.props.BoolProperty(name='Curved Staircase',default=False)
    curve_angle:bpy.props.FloatProperty(name='Curve Angle (degrees)',default=90,min=-360,max=360)
    inner_radius:bpy.props.FloatProperty(name='Inner Radius (units)',default=64,min=0.01)
    direction:bpy.props.FloatProperty(name='Direction (degrees)',default=0)
    @classmethod
    def poll(cls,context):
        return context.mode=='OBJECT' and hasattr(context.scene,'wavelength')
    def invoke(self,context,event):
        root=root_for(context.object) if self.edit else None
        if self.edit and (not root or not root.get('wl_primitive')):
            self.report({'ERROR'},'Select a generated primitive');return {'CANCELLED'}
        if root and root.get('wl_primitive'):
            self.kind=root['wl_primitive']
            for key,value in json.loads(root['wl_parameters']).items():
                if hasattr(self,key):setattr(self,key,value)
        elif hasattr(context.scene,'wavelength'):
            st=context.scene.wavelength
            if self.kind=='SPHERE':
                self.sphere_type=getattr(st,'sphere_type','ICO')
                self.segments=getattr(st,'brush_sides',8)
                self.rings=getattr(st,'brush_rings',6)
                self.subdivisions=getattr(st,'sphere_subdivisions',1)
            elif self.kind=='STAIRS':
                self.steps=getattr(st,'stair_steps',8)
                self.curved=getattr(st,'stair_curved',False)
                self.curve_angle=getattr(st,'stair_angle',90.0)
                self.inner_radius=getattr(st,'stair_inner_radius',64.0)
                self.landing=getattr(st,'stair_landing',0.0)
        return context.window_manager.invoke_props_dialog(self)
    def draw(self,context):
        if not self.edit:self.layout.prop(self,'kind')
        for field in fields_for(self.kind,{'sphere_type':self.sphere_type,'curved':self.curved}):self.layout.prop(self,field)
        self.layout.label(text='Dimensions are authoring units. Rotation and location remain on the parent.')
    def execute(self,context):
        values={k:getattr(self,k) for k in DEFAULTS}
        st=getattr(context.scene,'wavelength',None)
        root=root_for(context.object) if self.edit else None;created=False
        if root and not root.get('wl_primitive'):root=None
        engine=root.get('wl_engine',st.engine if st else 'blender') if root else (st.engine if st else 'blender')
        is_engine=bool(profiles.get(engine).get('brush_semantics',False))
        grid_step=profiles.grid_step_units(st) if (is_engine and st) else (profiles.active_snap_step_units(st,context) if st else None)
        if grid_step and self.kind=='STAIRS':
            g=float(grid_step)
            values['rise']=max(g,round(values['rise']/g)*g)
            values['run']=max(g,round(values['run']/g)*g)
            values['width']=max(g,round(values['width']/g)*g)
            if values['landing']>0:
                values['landing']=max(g,round(values['landing']/g)*g)
            if values['curved']:
                values['inner_radius']=max(g,round(values['inner_radius']/g)*g)
        try:
            primitives.generate(self.kind,values,validate_bsp=is_engine,grid_step=grid_step)
            if root is None:
                loc=context.scene.cursor.location.copy()
                if st and profiles.snap_enabled(st,context):
                    loc.x=profiles.snap_world_value(st,loc.x,context)
                    loc.y=profiles.snap_world_value(st,loc.y,context)
                    loc.z=profiles.snap_world_value(st,loc.z,context)
                root=bpy.data.objects.new(self.kind.title(),None);context.collection.objects.link(root);root.location=loc;root.empty_display_size=.2;root['wl_exclude']=True;root['wl_assembly_locked']=True;created=True
                context.view_layer.update()
            rebuild(root,self.kind,values,context)
            for obj in context.selected_objects:obj.select_set(False)
            if root.get('wl_assembly_locked',True):
                select_assembly(root,context,True)
                _SELECTED_ROOTS.add(root.as_pointer())
            else:
                root.select_set(True);context.view_layer.objects.active=root
            return {'FINISHED'}
        except (ValueError,RuntimeError) as exc:
            if created:bpy.data.objects.remove(root,do_unlink=True)
            self.report({'ERROR'},diagnostics.error(self.bl_idname, exc));return {'CANCELLED'}



class WL_PT_primitive(bpy.types.Panel):
    bl_label='Assembly & Primitive Parameters';bl_idname='WL_PT_primitive';bl_space_type='PROPERTIES';bl_region_type='WINDOW';bl_context='object'
    @classmethod
    def poll(cls,context):
        active=getattr(context,'edit_object',None) or getattr(context,'object',None)
        return workspace.active(context) and root_for(active) is not None
    def draw(self,context):
        active=getattr(context,'edit_object',None) or getattr(context,'object',None)
        root=root_for(active)
        locked=bool(root.get('wl_assembly_locked',True))
        in_edit=getattr(context,'mode','OBJECT')!='OBJECT'
        kind_label=(root.get('wl_primitive') or root.get('wl_assembly') or 'Assembly').title()
        parts=parts_for(root)
        self.layout.label(text=f"{kind_label} ({len(parts)} brush{'es' if len(parts)!=1 else ''})")
        self.layout.operator('wavelength.primitive_lock',text='Whole Object (Locked)' if locked else 'Individual Brushes (Unlocked)',icon='LOCKED' if locked else 'UNLOCKED',depress=locked)
        self.layout.operator('wavelength.assembly_editmode_toggle',text='Finish Vertex Editing (Tab)' if in_edit else 'Edit Assembly Vertices (Tab)',icon='OBJECT_DATAMODE' if in_edit else 'EDITMODE_HLT',depress=in_edit)
        if root.get('wl_primitive'):
            params=dict(DEFAULTS,**json.loads(root.get('wl_parameters','{}')))
            if root['wl_primitive']=='STAIRS':
                is_curved=bool(params.get('curved',False))
                self.layout.operator('wavelength.stair_curve_toggle',text='Shape: Curved Staircase' if is_curved else 'Shape: Straight Staircase',icon='IPO_BEZIER' if is_curved else 'IPO_LINEAR',depress=is_curved)
            for key in fields_for(root['wl_primitive'],params):
                val=params[key]
                if isinstance(val,bool):
                    text=f'{key.replace("_"," ").title()}: {"Yes" if val else "No"}'
                elif isinstance(val,str):
                    text=f'{key.replace("_"," ").title()}: {val}'
                else:
                    text=f'{key.replace("_"," ").title()}: {val:g}'
                self.layout.label(text=text)
            self.layout.operator('wavelength.primitive',text='Edit Parameters').edit=True


def add_menu(self,context):
    if workspace.active(context):
        for kind in FIELDS:
            op=self.layout.operator('wavelength.primitive',text=kind.title(),icon='MESH_CUBE');op.kind=kind


def _register_keymaps():
    _unregister_keymaps()
    wm=getattr(bpy.context,'window_manager',None)
    kc=wm.keyconfigs.addon if wm else None
    if not kc:return
    for name in ('Object Mode','Mesh'):
        km=kc.keymaps.new(name=name,space_type='EMPTY')
        kmi=km.keymap_items.new('wavelength.assembly_editmode_toggle','TAB','PRESS')
        _KEYMAPS.append((km,kmi))


def _unregister_keymaps():
    for km,kmi in _KEYMAPS:
        try:km.keymap_items.remove(kmi)
        except RuntimeError:pass
    _KEYMAPS.clear()


def register():
    for cls in (WL_OT_assembly_editmode_toggle,WL_OT_primitive_lock,WL_OT_stair_curve_toggle,WL_OT_primitive,WL_PT_primitive):bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.append(add_menu)
    _register_keymaps()
    if not bpy.app.timers.is_registered(sync_assemblies):
        bpy.app.timers.register(sync_assemblies,first_interval=.08,persistent=True)


def unregister():
    if bpy.app.timers.is_registered(sync_assemblies):
        bpy.app.timers.unregister(sync_assemblies)
    _unregister_keymaps()
    _SELECTED_ROOTS.clear()
    _EDITING_ROOTS.clear()
    bpy.types.VIEW3D_MT_mesh_add.remove(add_menu)
    for cls in (WL_PT_primitive,WL_OT_primitive,WL_OT_stair_curve_toggle,WL_OT_primitive_lock,WL_OT_assembly_editmode_toggle):bpy.utils.unregister_class(cls)

