"""Context capabilities and object meaning; independent of Blender execution."""
import json

UTILITY_CLASSES={'func_areaportal','func_areaportalwindow','func_occluder','func_ladder','func_simpleladder','func_monsterclip','func_clip'}
UTILITY_TEXTURES={'null','nodraw','clip','origin','aaatrigger','trigger','hint','skip','tools/toolsclip','tools/toolsplayerclip','tools/toolsnpcclip','tools/toolstrigger','tools/toolshint','tools/toolsskip','tools/toolsorigin','tools/toolsnodraw','tools/toolsareaportal','tools/toolsoccluder'}

# docs:begin capability-policy
def capabilities(mode='EDIT',workspace_enabled=True,editing=True,overlays=True,preparation=True,rendering=False):
    """Return allowed operations without mutating scene or workspace state."""
    # Inspection/export/render remain available when authoring tools are suspended.
    result={'INSPECT','EXPORT','RENDER'}
    if mode=='EDIT' and workspace_enabled and not rendering:
        if editing:result.add('EDIT')
        if overlays:result.add('GRID')
        if editing and overlays:result.add('HANDLES')
        if preparation:result.add('PREPARE')
    return frozenset(result)
# docs:end capability-policy

def role(obj,engine=''):
    if obj.get('wl_csg_target'):return 'HELPER'
    if obj.get('wl_asset_template') or obj.get('wl_entity_browser_template'):return 'LIBRARY'
    override=getattr(obj,'wavelength_context_role','AUTO')
    if override!='AUTO':return override
    if obj.get('wl_sun_preview') and getattr(obj,'type','')=='LIGHT':return 'CONTENT'
    if obj.get('wl_entity_icon_reference') or obj.get('wl_cutter_guide') or obj.get('wl_editor_helper'):return 'HELPER'
    if obj.get('wl_model_reference'):return 'CONTENT'
    owner=obj.get('wl_custom_model_owner')
    if owner:
        definition=owner.get('wl_custom_model')
        if definition and definition.wavelength_model.collision==obj:return 'HELPER'
        return 'CONTENT'
    kind=obj.get('wl_role','')
    if kind in {'ENTITY_ICON_SOURCE','ENTITY_ICON_REFERENCE','EDITOR_HELPER','LEAK_PATH'}:return 'HELPER'
    if kind=='ENTITY' and getattr(obj,'type','')=='EMPTY':return 'HELPER'
    if kind=='BRUSH':
        try:classname=dict(json.loads(obj.get('wl_entity_pairs','[]'))).get('classname','')
        except (TypeError,ValueError):classname=''
        if classname.startswith('trigger_') or classname in UTILITY_CLASSES:return 'HELPER'
        if engine!='blender':
            data=getattr(obj,'data',None);names={str(m.get('wl_texture','')).lower() for m in getattr(data,'materials',[]) if m and m.get('wl_texture')}
            if not names and data:
                try:names={str(f.get('texture','')).lower() for f in json.loads(data.get('wl_faces','{}')).values() if f.get('texture')}
                except (TypeError,ValueError):pass
            if names and names<=UTILITY_TEXTURES:return 'HELPER'
    return 'CONTENT'

def allows(context,feature=None):
    scene=getattr(context,'scene',None);ws=getattr(context,'workspace',None)
    enabled=bool(ws and ws.get('wl_workspace',getattr(ws,'name','')=='wavelength') and ws.get('wl_enabled',True))
    state=getattr(scene,'wavelength_context',None)
    from . import context_state
    caps=capabilities(getattr(state,'mode','EDIT'),enabled,getattr(state,'editing',True),getattr(state,'overlays',True),getattr(state,'preparation',True),context_state.rendering(scene))
    key={'grid':'GRID','gizmos':'HANDLES','preparation':'PREPARE','inspection':'INSPECT','export':'EXPORT','render':'RENDER'}.get(feature,'EDIT')
    if key=='PREPARE' and context_state.rendering():return False
    return key in caps and (not feature or feature in {'preparation','inspection','export','render','snapping'} or bool(ws and ws.get('wl_'+feature,True)))

def preparation_active(scene):
    import bpy
    if bpy.context.scene==scene and allows(bpy.context,'preparation'):return True
    for window in bpy.context.window_manager.windows:
        if window.scene!=scene:continue
        with bpy.context.temp_override(window=window):
            if allows(bpy.context,'preparation'):return True
    return False

def operation_allowed(context,operator):
    if '_OT_' in operator:
        namespace,name=operator.split('_OT_',1);operator=namespace.lower()+'.'+name
    # Explicit File-menu IO remains available outside the authoring workspace.
    if operator in {'wavelength.import_map','wavelength.export_map','wavelength.validate','wavelength.validate_alpha','wavelength.build_logs','wavelength.save_project'}:return allows(context,'export')
    return allows(context)
