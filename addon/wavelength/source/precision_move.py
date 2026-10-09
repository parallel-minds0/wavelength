"""One undoable map-unit transform, without settle-time corrections."""
import bpy
from bpy_extras import view3d_utils
from mathutils import Vector
from . import workspace,profiles
_KEYS=[]

class WL_OT_precision_move(bpy.types.Operator):
    bl_idname='wavelength.precision_move';bl_label='Move on Engine Grid';bl_options={'REGISTER','UNDO','BLOCKING'}
    axis:bpy.props.EnumProperty(items=[('FREE','View plane',''),('X','X',''),('Y','Y',''),('Z','Z','')],default='FREE')
    @classmethod
    def poll(cls,context):return workspace.active(context,'snapping') and context.area and context.area.type=='VIEW_3D' and context.mode=='OBJECT' and context.selected_objects and context.scene.wavelength.engine!='blender' and context.scene.wavelength.grid_mode=='ENGINE'
    def invoke(self,context,event):
        self._objects=[(o,o.matrix_world.copy()) for o in context.selected_objects if not any(p.select_get() for p in self.parents(o))]
        self._anchor=context.object.matrix_world.translation.copy();self._mouse=Vector((event.mouse_region_x,event.mouse_region_y));self._value='';self._step=profiles.active_grid_step_meters(context.scene.wavelength)
        self._start=view3d_utils.region_2d_to_location_3d(context.region,context.region_data,self._mouse,self._anchor)
        context.window_manager.modal_handler_add(self);context.area.header_text_set('Move: X/Y/Z constrain · type engine units · Ctrl free move · Enter confirm · Esc cancel')
        return {'RUNNING_MODAL'}
    @staticmethod
    def parents(obj):
        while obj.parent:obj=obj.parent;yield obj
    def restore(self):
        for obj,matrix in self._objects:
            if obj.name in bpy.data.objects:obj.matrix_world=matrix
    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'} or not workspace.active(context,'snapping'):
            self.restore();context.area.header_text_set(None);return {'CANCELLED'}
        if event.type in {'LEFTMOUSE','RET','NUMPAD_ENTER'} and event.value=='PRESS':
            context.area.header_text_set(None);return {'FINISHED'}
        if event.value=='PRESS':
            if event.type in {'X','Y','Z'}:self.axis=event.type
            elif event.type=='BACK_SPACE':self._value=self._value[:-1]
            elif event.unicode and event.unicode in '0123456789.-':self._value+=event.unicode
        if event.type=='MOUSEMOVE' or event.value=='PRESS':
            point=view3d_utils.region_2d_to_location_3d(context.region,context.region_data,(event.mouse_region_x,event.mouse_region_y),self._anchor)
            delta=point-self._start
            if self.axis!='FREE':
                index='XYZ'.index(self.axis)
                # Project mouse travel onto a screen-space unit axis; works with
                # standard move-gizmo arrows as well as keyboard constraints.
                a=view3d_utils.location_3d_to_region_2d(context.region,context.region_data,self._anchor)
                unit=Vector((0,0,0));unit[index]=self._step
                b=view3d_utils.location_3d_to_region_2d(context.region,context.region_data,self._anchor+unit)
                amount=delta[index]
                if a is not None and b is not None and (b-a).length_squared>1e-8:amount=(Vector((event.mouse_region_x,event.mouse_region_y))-self._mouse).dot(b-a)/(b-a).length_squared*self._step
                delta=Vector((0,0,0));delta[index]=amount
            if self._value:
                try:
                    value=profiles.engine_to_world(context.scene.wavelength,float(self._value));direction=Vector((1,0,0)) if self.axis=='FREE' else Vector(tuple(float(i=='XYZ'.index(self.axis)) for i in range(3)));delta=direction*value
                except ValueError:return {'RUNNING_MODAL'}
            elif not event.ctrl:
                for i in range(3):
                    if self.axis=='FREE' or i=='XYZ'.index(self.axis):delta[i]=round((self._anchor[i]+delta[i])/self._step)*self._step-self._anchor[i]
            for obj,matrix in self._objects:
                updated=matrix.copy();updated.translation+=delta;obj.matrix_world=updated
            context.area.tag_redraw()
        return {'RUNNING_MODAL'}

class WL_GGT_move(bpy.types.GizmoGroup):
    bl_idname='WL_GGT_move';bl_label='Wavelength Grid Move';bl_space_type='VIEW_3D';bl_region_type='WINDOW';bl_options={'3D','PERSISTENT'}
    @classmethod
    def poll(cls,context):
        return bool(WL_OT_precision_move.poll(context) and workspace.active(context,'gizmos') and context.workspace.tools.from_space_view3d_mode(context.mode,create=False) and context.workspace.tools.from_space_view3d_mode(context.mode,create=False).idname=='wavelength.precision_move_tool')
    def setup(self,context):
        self.arrows=[]
        for axis,color in zip('XYZ',((.8,.15,.15),(.15,.8,.15),(.15,.3,.9))):
            arrow=self.gizmos.new('GIZMO_GT_arrow_3d');arrow.color=color;arrow.alpha=.8;arrow.color_highlight=color;arrow.alpha_highlight=1;arrow.target_set_operator('wavelength.precision_move').axis=axis;self.arrows.append(arrow)
    def draw_prepare(self,context):
        from mathutils import Matrix
        for i,arrow in enumerate(self.arrows):
            direction=Vector(tuple(float(j==i) for j in range(3)));matrix=direction.to_track_quat('Z','Y').to_matrix().to_4x4();matrix.translation=context.object.matrix_world.translation;arrow.matrix_basis=matrix
class WL_Tool_move(bpy.types.WorkSpaceTool):
    bl_space_type='VIEW_3D';bl_context_mode='OBJECT';bl_idname='wavelength.precision_move_tool';bl_label='Engine Grid Move';bl_description='Move geometry on exact map-unit increments';bl_icon='ops.transform.translate';bl_widget='WL_GGT_move'

def register():
    for cls in (WL_OT_precision_move,WL_GGT_move):bpy.utils.register_class(cls)
    bpy.utils.register_tool(WL_Tool_move,after={'builtin.move'})
    kc=bpy.context.window_manager.keyconfigs.addon
    if kc:
        km=kc.keymaps.new(name='Object Mode',space_type='EMPTY');item=km.keymap_items.new('wavelength.precision_move','G','PRESS');_KEYS.append((km,item))
def unregister():
    for km,item in _KEYS:km.keymap_items.remove(item)
    _KEYS.clear();bpy.utils.unregister_tool(WL_Tool_move)
    for cls in (WL_GGT_move,WL_OT_precision_move):bpy.utils.unregister_class(cls)
