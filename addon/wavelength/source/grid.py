"""World-anchored engine grid, drawn analytically on the GPU.

A full viewport triangle pair intersects the world plane per pixel. There is no
camera-centred line buffer or finite patch to run out of lines when panning.
"""
import bpy
from . import profiles

_handles = []
_shader = None
_batch = None
_error = None


def engine_enabled(settings):
    return settings is not None and settings.engine != 'blender' and settings.grid_mode == 'ENGINE'


def update(settings, context):
    # The native grid, unit system, subdivisions and visibility are never changed.
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D': area.tag_redraw()


def _create_shader():
    import gpu
    from gpu_extras.batch import batch_for_shader
    global _shader, _batch
    info = gpu.types.GPUShaderCreateInfo()
    info.vertex_in(0, 'VEC2', 'position')
    interface = gpu.types.GPUStageInterfaceInfo('wl_grid_interface')
    interface.smooth('VEC3', 'near_point')
    interface.smooth('VEC3', 'far_point')
    info.vertex_out(interface)
    info.fragment_out(0, 'VEC4', 'color')
    info.push_constant('MAT4', 'view_projection')
    info.push_constant('FLOAT', 'spacing')
    info.push_constant('INT', 'plane_axis')
    info.push_constant('VEC2', 'axis_visibility')
    info.depth_write('ANY')
    info.vertex_source('''void main() {
    mat4 inv = inverse(view_projection);
    vec4 a = inv * vec4(position, -1.0, 1.0);
    vec4 b = inv * vec4(position,  1.0, 1.0);
    near_point = a.xyz / a.w;
    far_point = b.xyz / b.w;
    gl_Position = vec4(position, 0.0, 1.0);
}''')
    info.fragment_source('''
float line_coverage(vec2 p, vec2 footprint, float interval) {
    vec2 d = abs(mod(p + interval * 0.5, interval) - interval * 0.5);
    vec2 coverage = 1.0 - smoothstep(vec2(0.25), vec2(1.25), d / footprint);
    return max(coverage.x, coverage.y);
}
void main() {
    vec3 ray = far_point - near_point;
    if (abs(ray[plane_axis]) < 1e-8) discard;
    float t = -near_point[plane_axis] / ray[plane_axis];
    if (t < 0.0 || t > 1.0) discard;
    vec3 world = near_point + t * ray;
    vec2 p = plane_axis == 2 ? world.xy : (plane_axis == 1 ? world.xz : world.yz);
    vec2 footprint = max(fwidth(p), vec2(1e-7));
    float pixel_world = max(footprint.x, footprint.y);
    // Only the selected interval is yellow. Subpixel lines fade out instead of
    // being relabelled as larger yellow units. Coarser context stays neutral.
    float selected = line_coverage(p, footprint, spacing) *
                     smoothstep(2.0, 6.0, spacing / pixel_world);
    float context_line = 0.0; // Blender supplies the adaptive neutral grid.
    float alpha = max(selected * 0.65, context_line * 0.28);
    vec2 axis_coverage = 1.0 - smoothstep(vec2(0.25), vec2(1.25), abs(p) / footprint);
    alpha *= 1.0 - max(axis_coverage.x * axis_visibility.x, axis_coverage.y * axis_visibility.y);
    if (alpha < 0.005) discard;
    color = vec4(mix(vec3(0.43), vec3(1.0, 0.85, 0.10), selected), alpha);
    vec4 clip = view_projection * vec4(world, 1.0);
    gl_FragDepth = clamp(0.5 * clip.z / clip.w + 0.5 - 0.000002, 0.0, 1.0);
}
''')
    _shader = gpu.shader.create_from_info(info)
    _batch = batch_for_shader(_shader, 'TRIS', {'position': [(-1,-1),(1,-1),(1,1),(-1,-1),(1,1),(-1,1)]})


def _draw_grid():
    import gpu
    global _error
    context = bpy.context
    from .workspace import active
    if not active(context, 'grid'): return
    settings = getattr(context.scene, 'wavelength', None)
    if not engine_enabled(settings) or not context.space_data.overlay.show_overlays:
        return
    region = context.region_data
    if region is None:
        return
    try:
        if _shader is None:
            _create_shader()
        axis = 2
        # Front/side/top orthographic views use the corresponding world plane;
        # arbitrary views, including camera view, use the XY floor.
        if not region.is_perspective:
            from mathutils import Vector
            forward = region.view_rotation @ Vector((0,0,1))
            dominant = max(range(3), key=lambda i: abs(forward[i]))
            if abs(forward[dominant]) > 0.9999:
                axis = dominant
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.depth_mask_set(False)
        _shader.bind()
        _shader.uniform_float('view_projection', region.perspective_matrix)
        _shader.uniform_float('spacing', profiles.active_grid_step_meters(settings))
        _shader.uniform_int('plane_axis', axis)
        overlay = context.space_data.overlay
        axes = (overlay.show_axis_x, overlay.show_axis_y, overlay.show_axis_z)
        plane = (0, 1) if axis == 2 else ((0, 2) if axis == 1 else (1, 2))
        _shader.uniform_float('axis_visibility', (float(axes[plane[1]]), float(axes[plane[0]])))
        _batch.draw(_shader)
        _error = None
    except Exception as exc:
        if _error != str(exc):
            print('Wavelength grid:', exc)
        _error = str(exc)
    finally:
        gpu.state.depth_mask_set(False)
        gpu.state.depth_test_set('NONE')
        gpu.state.blend_set('NONE')


def _draw_label():
    import blf
    from .workspace import active
    if not active(bpy.context, 'grid'): return
    settings = getattr(bpy.context.scene, 'wavelength', None)
    if not engine_enabled(settings) or not bpy.context.space_data.overlay.show_overlays:
        return
    blf.size(0, 15)
    blf.color(0, 1.0, 0.85, 0.10, 1.0)
    blf.position(0, 20, 46, 0)
    label = 'GRID ERROR: ' + _error if _error else f'GRID SNAP  |  {settings.grid_step} engine units'
    blf.draw(0, label)


def register():
    if not _handles:
        _handles.append(bpy.types.SpaceView3D.draw_handler_add(_draw_grid, (), 'WINDOW', 'POST_VIEW'))
        _handles.append(bpy.types.SpaceView3D.draw_handler_add(_draw_label, (), 'WINDOW', 'POST_PIXEL'))


def unregister():
    global _shader, _batch
    for handle in _handles:
        bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
    _handles.clear()
    _shader = _batch = None
