"""Live Edit Mode edge dimensions in the active profile's display units.

Read the edit BMesh, not the last committed mesh datablock. Draw only screen-space
text; this never changes Blender's mesh, unit settings, or built-in overlays.
"""
import math
import bpy
import bmesh
import blf
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d
from . import profiles, workspace

MAX_EDGES = 20000
MAX_LABELS = 160


def enabled(context):
    settings = getattr(context.scene, 'wavelength', None)
    space = context.space_data
    return bool(context.mode == 'EDIT_MESH' and workspace.active(context)
                and workspace.active(context, 'grid') and settings
                and settings.show_edge_measurements and space
                and space.type == 'VIEW_3D' and space.overlay.show_overlays
                and context.region and context.region.type == 'WINDOW')


def format_length(settings, length):
    """Grid subdivisions control snapping, never the length of an engine unit."""
    from .grid import engine_enabled
    engine = engine_enabled(settings)
    value = profiles.world_to_engine(settings, length) if engine else length
    if not math.isfinite(value):
        return ''
    # Three decimals keep off-grid edits visible without floating-point tails.
    value = round(value, 3)
    return f'{value:g}' + (' u' if engine else ' m')


def edge_segments(context):
    """Yield selected, unhidden edit edges, including multi-object Edit Mode.

    Object matrices matter: non-uniform scale, rotation and parent transforms
    must all be reflected in the displayed physical dimension.
    """
    visited = 0
    for obj in context.objects_in_mode:
        if obj.type != 'MESH' or not obj.visible_get(view_layer=context.view_layer):
            continue
        mesh = bmesh.from_edit_mesh(obj.data)
        matrix = obj.matrix_world
        normal_matrix = matrix.to_3x3().inverted_safe().transposed()
        for edge in mesh.edges:
            visited += 1
            if visited > MAX_EDGES:
                return
            if edge.hide or not edge.select:
                continue
            a, b = (matrix @ v.co for v in edge.verts)
            if (b - a).length_squared < 1e-16:
                continue
            normals = tuple(normal_matrix @ face.normal for face in edge.link_faces if not face.hide)
            yield a, b, normals


def label_candidates(context):
    region, view = context.region, context.region_data
    settings, space = context.scene.wavelength, context.space_data
    if view is None:
        return
    eye = view.view_matrix.inverted().translation
    toward_view = view.view_rotation @ Vector((0, 0, 1))
    xray = space.shading.show_xray or space.shading.type == 'WIREFRAME'
    for a, b, normals in edge_segments(context):
        midpoint = (a + b) * .5
        toward = eye - midpoint if view.is_perspective else toward_view
        if not xray and normals and all(normal.dot(toward) <= 1e-8 for normal in normals):
            continue
        clip = view.perspective_matrix @ midpoint.to_4d()
        if clip.w <= 0 or not -clip.w <= clip.z <= clip.w:
            continue
        pa = location_3d_to_region_2d(region, view, a)
        pb = location_3d_to_region_2d(region, view, b)
        if pa is None or pb is None or (pb-pa).length < 34:
            continue
        point = location_3d_to_region_2d(region, view, midpoint)
        if point is None or not (0 < point.x < region.width and 0 < point.y < region.height):
            continue
        text = format_length(settings, (b-a).length)
        if text:
            yield point, text


def draw():
    context = bpy.context
    if not enabled(context):
        return
    font = 0
    blf.size(font, 13 * context.preferences.system.ui_scale)
    blf.enable(font, blf.SHADOW)
    blf.shadow(font, 3, 0, 0, 0, .95)
    blf.shadow_offset(font, 1, -1)
    blf.color(font, 1, .87, .48, 1)
    occupied = []
    try:
        for point, text in label_candidates(context):
            width, height = blf.dimensions(font, text)
            x = point.x - width * .5
            # Try nearby placements before suppressing an overlapping label.
            for offset in (9, 25, -height-9):
                y = point.y + offset
                box = (x-4, y-3, x+width+4, y+height+3)
                if box[0] < 0 or box[1] < 0 or box[2] > context.region.width or box[3] > context.region.height:
                    continue
                if any(box[0] < b[2] and box[2] > b[0] and box[1] < b[3] and box[3] > b[1] for b in occupied):
                    continue
                blf.position(font, x, y, 0)
                blf.draw(font, text)
                occupied.append(box)
                break
            if len(occupied) >= MAX_LABELS:
                break
    finally:
        blf.disable(font, blf.SHADOW)
