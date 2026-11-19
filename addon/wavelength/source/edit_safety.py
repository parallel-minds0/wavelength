"""Keep background edit-mesh access outside native topology transactions."""
def topology_modal_active(context):
    """Python BMesh wrappers can allocate layers even during read-only iteration.

    Native mesh tools retain CustomData pointers across modal events. Do not let
    observers create wrappers or reproject UVs until those tools release them.
    Simple native translate/rotate/resize remain eligible for live projection.
    """
    manager=getattr(context,'window_manager',None)
    windows=getattr(manager,'windows',())
    for window in windows:
        for operator in getattr(window,'modal_operators',()):
            name=getattr(operator,'bl_idname','') or getattr(getattr(operator,'bl_rna',None),'identifier','')
            if name.startswith(('MESH_OT_','mesh.')) or name in {
                'TRANSFORM_OT_edge_slide','TRANSFORM_OT_vert_slide',
                'transform.edge_slide','transform.vert_slide'}:
                return True
    return False
