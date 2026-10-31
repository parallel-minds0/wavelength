"""Source QAngle poses: Rz(yaw) @ Ry(pitch) @ Rx(roll), in map axes."""
import json
import math
from mathutils import Euler


def rotation(pairs):
    values=dict(pairs)
    if 'angles' in values:
        angles=[float(v) for v in values['angles'].split()]
        if len(angles)!=3:raise ValueError('Source angles require pitch yaw roll')
        pitch,yaw,roll=angles
    else:
        yaw=float(values.get('angle','0'));pitch=roll=0.
        if yaw in (-1.,-2.):pitch,yaw=(-90. if yaw==-1. else 90.),0.
    if not all(math.isfinite(v) for v in (pitch,yaw,roll)):raise ValueError('Source angles must be finite')
    return Euler(tuple(math.radians(v) for v in (roll,pitch,yaw)),'XYZ')


def apply(obj,pairs,force=False):
    values=dict(pairs);token=json.dumps([values.get('angles'),values.get('angle')])
    if not force and obj.get('_wl_source_angles')==token:return
    obj.rotation_mode='XYZ';obj.rotation_euler=rotation(pairs)
    obj['_wl_source_angles']=token


def migrate(scene):
    """Repair legacy unrotated imports while retaining existing manual rotations."""
    for obj in scene.objects:
        if obj.get('wl_role')!='ENTITY' or obj.get('wl_custom_model') or '_wl_source_angles' in obj:continue
        pairs=json.loads(obj.get('wl_pairs','[]'));values=dict(pairs)
        if obj.matrix_world.to_quaternion().angle<1e-6:apply(obj,pairs)
        else:obj['_wl_source_angles']=json.dumps([values.get('angles'),values.get('angle')])


def export_pairs(obj,pairs):
    from . import formats
    current=obj.matrix_world.to_quaternion().to_matrix()
    original=rotation(pairs).to_matrix()
    if max(abs(current[i][j]-original[i][j]) for i in range(3) for j in range(3))<1e-5:
        return pairs  # Preserve original literals, including legacy angle keys.
    euler=current.to_euler('XYZ')
    angles=' '.join(formats.number(math.degrees(euler[i])) for i in (1,2,0))
    return [(k,v) for k,v in pairs if k not in {'angle','angles'}]+[('angles',angles)]
