"""Interactive light_environment previews using real Blender Sun lights."""
import json
import math
import time
import bpy
from bpy.app.handlers import persistent
from mathutils import Matrix,Vector
from . import workspace,profiles

_state={}
_lights={}
_pending={}
_busy=False
_registered=[]
_previews={}


def values(obj):
    try:return dict(json.loads(obj.get('wl_pairs','[]')))
    except (ValueError,TypeError):return {}


def is_sun(obj):
    return bool(obj and obj.get('wl_role')=='ENTITY' and not obj.get('wl_exclude') and
                values(obj).get('classname')=='light_environment')


def entity_for(obj):
    if obj and obj.get('wl_sun_preview'):return obj.parent
    return obj if is_sun(obj) else None


def light_for(entity):
    return next((o for o in entity.children if o.get('wl_sun_preview') and o.type=='LIGHT'),None)


def number(value):
    return format(0 if abs(value)<1e-7 else value,'.7g')


def direction(heading,elevation):
    return Vector((math.cos(elevation)*math.cos(heading),math.cos(elevation)*math.sin(heading),-math.sin(elevation)))


def angles(light):
    matrix=light.matrix_basis
    if light.parent:matrix=light.parent.matrix_world@light.matrix_parent_inverse@matrix
    ray=matrix.to_quaternion()@Vector((0,0,-1))
    return math.atan2(ray.y,ray.x),-math.asin(max(-1,min(1,ray.z)))


def srgb(value):
    return value/12.92 if value<=.04045 else ((value+.055)/1.055)**2.4


def encoded(value):
    return 12.92*value if value<=.0031308 else 1.055*max(0,value)**(1/2.4)-.055


def replace(pairs,changes):
    return [(k,changes.pop(k,v)) for k,v in pairs]+list(changes.items())


def snapshot(entity,light):
    return (entity.get('wl_pairs','[]'),tuple(light.matrix_world.to_quaternion()),
            tuple(light.data.color),light.data.energy,light.data.angle)


def set_rotation(light,heading,elevation):
    world=direction(heading,elevation).to_track_quat('-Z','Y')
    parent=light.parent.matrix_world.to_quaternion() if light.parent else None
    light.rotation_euler=((parent.inverted()@world) if parent else world).to_euler('XYZ')


def ensure(entity,new=False):
    if not is_sun(entity):return None
    light=light_for(entity)
    if light is None:
        data=bpy.data.lights.new('Wavelength Sun','SUN')
        light=bpy.data.objects.new(entity.name+' sunlight',data)
        (entity.users_collection[0] if entity.users_collection else bpy.context.scene.collection).objects.link(light)
        light.parent=entity;light.location=(0,0,0)
        light['wl_exclude']=True;light['wl_sun_preview']=True
        if new:
            pairs=json.loads(entity.get('wl_pairs','[]'))
            entity['wl_pairs']=json.dumps(replace(pairs,{'pitch':'-45','angles':'0 135 0'}))
    from_entity(entity,light)
    return light


def from_entity(entity,light=None):
    light=light or light_for(entity)
    if not light:return
    data=values(entity)
    try:
        rotation=[float(x) for x in data.get('angles','0 0 0').split()]
        heading=math.radians(rotation[1] if len(rotation)>1 else float(data.get('angle',0)))
        elevation=-math.radians(float(data.get('pitch','0')))
        color=[float(x) for x in data.get('_light','255 255 255 200').split()]
        if len(color)<4:color=[255,255,255,200]
        if not all(math.isfinite(x) for x in [heading,elevation,*color]):return
        set_rotation(light,heading,elevation)
        light.data.color=tuple(srgb(max(0,min(1,x/255))) for x in color[:3])
        light.data.energy=max(0,color[3]/100)
        spread=float(data.get('SunSpreadAngle','0.53'))
        if math.isfinite(spread):light.data.angle=math.radians(max(0,min(180,spread)))
        _lights[light.data.as_pointer()]=entity
        _previews[entity.as_pointer()]=light
        _state[entity.as_pointer()]=snapshot(entity,light)
    except (ValueError,TypeError):return


def export_pairs(entity,pairs,heading=None,elevation=None):
    light=light_for(entity)
    if light is None:return pairs
    previous=_state.get(entity.as_pointer())
    if previous and previous[0]!=entity.get('wl_pairs','[]'):return pairs
    if heading is None:heading,elevation=angles(light)
    color=' '.join(str(round(max(0,min(1,encoded(c)))*255)) for c in light.data.color)
    changes={'angles':f'0 {number(math.degrees(heading)%360)} 0',
             'pitch':number(-math.degrees(elevation)),
             '_light':color+' '+number(light.data.energy*100)}
    if any(k=='SunSpreadAngle' for k,v in pairs):changes['SunSpreadAngle']=number(math.degrees(light.data.angle))
    return replace(pairs,changes)


def write_entity(entity,heading=None,elevation=None):
    light=light_for(entity)
    pairs=export_pairs(entity,json.loads(entity.get('wl_pairs','[]')),heading,elevation)
    entity['wl_pairs']=json.dumps(pairs)
    _state[entity.as_pointer()]=snapshot(entity,light)
    # Keep only sun-owned fields current; preserve unrelated inspector edits.
    settings=getattr(bpy.context.scene,'wavelength',None)
    if settings:
        from . import ui
        if ui._entity_property_target(entity)[2]==settings.entity_editor_binding:
            current=dict(pairs)
            for item in settings.fields:
                if item.key not in {'angles','pitch','_light','SunSpreadAngle'} or item.key not in current:continue
                item.value=current[item.key]
                if item.kind in {'float','integer'}:
                    item.kind='float';item.number=float(item.value)


def set_direction(entity,heading,elevation):
    light=light_for(entity)
    if light is None:light=ensure(entity)
    if not light:return
    elevation=max(-math.pi/2,min(math.pi/2,elevation))
    set_rotation(light,heading,elevation)
    write_entity(entity,heading,elevation)


def queue(entity):
    _pending[entity.as_pointer()]=entity
    if not bpy.app.timers.is_registered(flush):bpy.app.timers.register(flush,first_interval=.02)


def flush():
    global _busy
    _busy=True;started=time.monotonic()
    try:
        for key,preview in list(_previews.items()):
            try:
                if preview.parent is None or not is_sun(preview.parent):
                    data=preview.data;_lights.pop(data.as_pointer(),None)
                    bpy.data.objects.remove(preview,do_unlink=True)
                    if not data.users:bpy.data.lights.remove(data)
                    _previews.pop(key,None);_state.pop(key,None)
            except ReferenceError:_previews.pop(key,None);_state.pop(key,None)
        while _pending and time.monotonic()-started<.005:
            key,entity=_pending.popitem()
            try:
                light=light_for(entity)
                if not is_sun(entity):
                    if light:
                        data=light.data;_lights.pop(data.as_pointer(),None)
                        bpy.data.objects.remove(light,do_unlink=True)
                        if not data.users:bpy.data.lights.remove(data)
                    _state.pop(key,None);continue
                if light is None:ensure(entity);continue
                current=snapshot(entity,light);previous=_state.get(key)
                if previous is None or current[0]!=previous[0]:from_entity(entity,light)
                elif current!=previous:write_entity(entity)
            except ReferenceError:_state.pop(key,None)
    finally:_busy=False
    return .02 if _pending else None


@persistent
def changed(scene,depsgraph):
    if _busy or not workspace.active():return
    for update in depsgraph.updates:
        block=update.id.original
        if isinstance(block,bpy.types.Object):
            entity=entity_for(block)
            if entity:queue(entity)
            elif block.as_pointer() in _state:queue(block)
        elif isinstance(block,bpy.types.Light):
            entity=_lights.get(block.as_pointer())
            if entity:
                try:queue(entity)
                except ReferenceError:_lights.pop(block.as_pointer(),None)
        elif isinstance(block,bpy.types.Scene) and _previews:
            if not bpy.app.timers.is_registered(flush):bpy.app.timers.register(flush,first_interval=.02)


@persistent
def loaded(*_):
    _state.clear();_lights.clear();_pending.clear();_previews.clear()
    for obj in list(bpy.data.objects):
        if is_sun(obj):queue(obj)
        elif obj.get('wl_sun_preview') and obj.parent is None:
            data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
            if not data.users:bpy.data.lights.remove(data)


def heading_get(self):
    entity=entity_for(self.id_data);light=light_for(entity) if entity else None
    return angles(light)[0] if light else 0


def elevation_get(self):
    entity=entity_for(self.id_data);light=light_for(entity) if entity else None
    return angles(light)[1] if light else 0


class WLSunControls(bpy.types.PropertyGroup):
    heading:bpy.props.FloatProperty(name='Light Heading',subtype='ANGLE',
        get=heading_get,set=lambda self,value:set_direction(entity_for(self.id_data),value,elevation_get(self)))
    elevation:bpy.props.FloatProperty(name='Sun Elevation',subtype='ANGLE',min=-math.pi/2,max=math.pi/2,
        get=elevation_get,set=lambda self,value:set_direction(entity_for(self.id_data),heading_get(self),value))


class WL_OT_sun_preview(bpy.types.Operator):
    bl_idname='wavelength.sun_preview';bl_label='Preview Scene Lighting'
    bl_description='Use actual scene lights and world in Material Preview for interactive sun shadows'
    def execute(self,context):
        for area in context.screen.areas:
            if area.type=='VIEW_3D':
                shading=area.spaces.active.shading
                shading.type='MATERIAL';shading.use_scene_lights=True;shading.use_scene_world=True
        return {'FINISHED'}


class WL_OT_add_sun(bpy.types.Operator):
    bl_idname='wavelength.add_sun';bl_label='Add Wavelength Sun';bl_options={'REGISTER','UNDO'}
    bl_description='Create an engine light_environment with a real Sun light and viewport direction rings'
    @classmethod
    def poll(cls,context):
        settings=getattr(context.scene,'wavelength',None)
        return workspace.active(context) and settings is not None and (profiles.is_source(settings.engine) or profiles.is_goldsrc(settings.engine))
    def execute(self,context):
        from .ui import _spawn_point_entity
        _spawn_point_entity(context,'light_environment')
        return {'FINISHED'}


def draw_add(self,context):
    if WL_OT_add_sun.poll(context):
        self.layout.separator();self.layout.operator('wavelength.add_sun',text='Wavelength Sun',icon='LIGHT_SUN')


class WL_PT_sun(bpy.types.Panel):
    bl_idname='WL_PT_sun';bl_label='Sun Direction & Preview'
    bl_space_type='PROPERTIES';bl_region_type='WINDOW';bl_context='object'
    @classmethod
    def poll(cls,context):return workspace.active(context) and entity_for(context.object) is not None
    def draw(self,context):
        entity=entity_for(context.object);light=light_for(entity);l=self.layout;l.use_property_split=True
        l.prop(entity.wl_sun,'heading');l.prop(entity.wl_sun,'elevation')
        if light:
            l.prop(light.data,'color');l.prop(light.data,'energy',text='Preview Strength')
            l.prop(light.data,'angle',text='Sun Size')
        l.operator('wavelength.sun_preview',icon='LIGHT_SUN')
        l.label(text='Drag the rings or rotate the Sun light in the viewport.')


class WL_GGT_sun(bpy.types.GizmoGroup):
    bl_idname='WL_GGT_sun';bl_label='Wavelength Sun Direction'
    bl_space_type='VIEW_3D';bl_region_type='WINDOW';bl_options={'3D','PERSISTENT'}
    @classmethod
    def poll(cls,context):
        entity=entity_for(context.object)
        return workspace.active(context,'gizmos') and entity is not None and light_for(entity) is not None
    def setup(self,context):
        self.entity=None;self.rings=[]
        for prop,color,scale in (('heading',(1,.7,.15),1.3),('elevation',(.3,.7,1),1)):
            ring=self.gizmos.new('GIZMO_GT_dial_3d');ring.color=color;ring.alpha=.7
            ring.color_highlight=(1,1,1);ring.alpha_highlight=1;ring.line_width=3;ring.scale_basis=scale
            ring.use_draw_modal=True;ring.use_draw_value=True
            ring.target_set_handler('offset',get=lambda p=prop:getattr(self.entity.wl_sun,p) if self.entity else 0,
                                    set=lambda value,p=prop:setattr(self.entity.wl_sun,p,value))
            self.rings.append(ring)
        self.arrow=self.gizmos.new('GIZMO_GT_arrow_3d');self.arrow.hide_select=True
        self.arrow.color=(1,.8,.2);self.arrow.alpha=.8;self.arrow.length=1.8;self.arrow.line_width=3
    def draw_prepare(self,context):
        self.entity=entity_for(context.object);light=light_for(self.entity)
        origin=light.matrix_world.translation;heading,elevation=angles(light)
        self.rings[0].matrix_basis=Matrix.Translation(origin)
        normal=Vector((-math.sin(heading),math.cos(heading),0))
        self.rings[1].matrix_basis=Matrix.Translation(origin)@normal.to_track_quat('Z','Y').to_matrix().to_4x4()
        self.arrow.matrix_basis=Matrix.Translation(origin)@direction(heading,elevation).to_track_quat('Z','Y').to_matrix().to_4x4()


CLASSES=(WLSunControls,WL_OT_sun_preview,WL_OT_add_sun,WL_PT_sun,WL_GGT_sun)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls);_registered.append(cls)
    bpy.types.Object.wl_sun=bpy.props.PointerProperty(type=WLSunControls)
    bpy.types.VIEW3D_MT_light_add.append(draw_add)
    for handlers,callback in ((bpy.app.handlers.depsgraph_update_post,changed),(bpy.app.handlers.load_post,loaded),
                             (bpy.app.handlers.undo_post,loaded),(bpy.app.handlers.redo_post,loaded)):
        if callback not in handlers:handlers.append(callback)
    if not bpy.app.background:bpy.app.timers.register(bootstrap,first_interval=.2)


def bootstrap():
    loaded();return None


def unregister():
    try:bpy.types.VIEW3D_MT_light_add.remove(draw_add)
    except (ValueError,RuntimeError):pass
    for callback in (flush,bootstrap):
        if bpy.app.timers.is_registered(callback):bpy.app.timers.unregister(callback)
    for handlers,callback in ((bpy.app.handlers.depsgraph_update_post,changed),(bpy.app.handlers.load_post,loaded),
                             (bpy.app.handlers.undo_post,loaded),(bpy.app.handlers.redo_post,loaded)):
        if callback in handlers:handlers.remove(callback)
    _pending.clear();_state.clear();_lights.clear();_previews.clear()
    if hasattr(bpy.types.Object,'wl_sun'):del bpy.types.Object.wl_sun
    for cls in reversed(_registered):bpy.utils.unregister_class(cls)
    _registered.clear()
