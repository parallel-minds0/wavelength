"""Temporary world-axis guides shared by keyboard and gizmo transforms."""
import bpy
import gpu
from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from . import workspace

_guides=[]

class Guide:
    def __init__(self,context,pivot,axis):
        self.area=context.area;self.region=context.region.as_pointer()
        self.pivot=Vector(pivot);self.axis=axis
        self.handle=bpy.types.SpaceView3D.draw_handler_add(self.draw,(),'WINDOW','POST_VIEW')
        _guides.append(self);self.area.tag_redraw()
    def draw(self):
        context=bpy.context
        if self.axis not in 'XYZ' or self.axis=='FREE':return
        if not context.region or context.region.as_pointer()!=self.region:return
        if not workspace.active(context,'gizmos'):return
        index='XYZ'.index(self.axis);direction=Vector(tuple(float(i==index) for i in range(3)))
        extent=max(context.space_data.clip_end,context.region_data.view_distance*10,1)
        theme=context.preferences.themes[0].user_interface
        color=tuple(getattr(theme,'axis_'+self.axis.lower()))[:3]+(.9,)
        shader=gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        batch=batch_for_shader(shader,'LINES',{'pos':(self.pivot-direction*extent,self.pivot+direction*extent)})
        depth=gpu.state.depth_test_get();blend=gpu.state.blend_get()
        try:
            gpu.state.depth_test_set('NONE');gpu.state.blend_set('ALPHA')
            shader.bind();shader.uniform_float('viewportSize',gpu.state.viewport_get()[2:])
            shader.uniform_float('lineWidth',1.5);shader.uniform_float('color',color);batch.draw(shader)
        finally:gpu.state.depth_test_set(depth);gpu.state.blend_set(blend)
    def stop(self):
        if self.handle:bpy.types.SpaceView3D.draw_handler_remove(self.handle,'WINDOW');self.handle=None
        if self in _guides:_guides.remove(self)
        try:self.area.tag_redraw()
        except ReferenceError:pass

def start(owner,context,pivot):
    owner._axis_guide=Guide(context,pivot,owner.axis)

def update(owner):
    guide=getattr(owner,'_axis_guide',None)
    if guide:
        guide.axis=owner.axis;guide.area.tag_redraw()

def finish(owner,context):
    guide=getattr(owner,'_axis_guide',None)
    if guide:guide.stop();owner._axis_guide=None
    if context.area:context.area.header_text_set(None);context.area.tag_redraw()

def clear():
    for guide in tuple(_guides):guide.stop()
