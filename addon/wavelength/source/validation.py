"""Engine-facing scene validation for the pre-alpha."""
import json, math
from . import profiles, system_tree

def _diag(sev,code,msg,obj=None):
    d={'schema_version':1,'severity':sev,'code':code,'message':msg}
    if obj is not None:d['object']=obj.name
    return d

def validate(scene):
    out=[];s=scene.wavelength;step=profiles.active_grid_step_meters(s);eps=1e-5
    names={};targets=[];entity_groups={};ids={};counts={'brushes':0,'faces':0,'entities':0}
    for obj in scene.objects:
        role=obj.get('wl_role')
        if obj.get('wl_exclude'):continue
        oid=obj.get('wl_id')
        if oid:
            if oid in ids:out.append(_diag('error','DUPLICATE_ID',f'Duplicate Wavelength object ID also used by {ids[oid].name}',obj))
            else:ids[oid]=obj
        if role=='BRUSH':
            counts['brushes']+=1;counts['faces']+=len(obj.data.polygons) if obj.type=='MESH' else 0
            if obj.type!='MESH' or len(obj.data.polygons)<4:out.append(_diag('error','INVALID_BRUSH','Brush has insufficient mesh geometry',obj));continue
            if obj.modifiers:out.append(_diag('warning','BRUSH_MODIFIERS','Brush has Blender modifiers; export uses base mesh',obj))
            if step:
                for v in obj.data.vertices:
                    p=obj.matrix_world@v.co
                    if any(abs(c/step-round(c/step))>eps for c in p):out.append(_diag('warning','OFF_GRID','Brush contains off-grid vertices',obj));break
            for p in obj.data.polygons:
                if p.area<=1e-10:out.append(_diag('error','ZERO_AREA_FACE','Brush contains a zero-area face',obj));break
            try:records=json.loads(obj.data.get('wl_faces','{}'))
            except Exception:records={};out.append(_diag('error','FACE_DATA','Brush face metadata is invalid JSON',obj))
            if len(records)!=len(obj.data.polygons):out.append(_diag('warning','FACE_METADATA_COUNT','Face metadata count differs from polygon count',obj))
            for tex in system_tree.brush_textures(obj):
                if tex in {'clip','origin','aaatrigger','hint','skip'} and s.engine=='blender':out.append(_diag('warning','ENGINE_TEXTURE_IN_BLENDER',f'Special engine texture {tex} used with No Engine profile',obj))
            if obj.get('wl_entity_id'):entity_groups.setdefault(obj['wl_entity_id'],[]).append(obj)
        elif role=='ENTITY':
            counts['entities']+=1
            try:pairs=json.loads(obj.get('wl_pairs','[]'))
            except Exception:pairs=[];out.append(_diag('error','ENTITY_DATA','Entity properties are invalid JSON',obj))
            vals=dict(pairs);tn=vals.get('targetname');target=vals.get('target')
            classname=vals.get('classname','')
            if not classname:out.append(_diag('error','ENTITY_CLASS_MISSING','Point entity has no classname',obj))
            for key,value in pairs:
                low=str(value).casefold()
                if key=='model' and low and not (low.endswith('.mdl') or low.endswith('.spr') or low.startswith('*')):out.append(_diag('warning','ASSET_EXTENSION',f'Model property has unusual path: {value}',obj))
                if key in {'target','targetname'} and any(ch.isspace() for ch in str(value)):out.append(_diag('warning','TARGET_WHITESPACE',f'{key} contains whitespace: {value!r}',obj))
            if tn:names.setdefault(tn,[]).append(obj)
            if target:targets.append((target,obj))
    for target,obj in targets:
        if target not in names:out.append(_diag('warning','MISSING_TARGET',f'Target {target!r} does not exist',obj))
    for name,objs in names.items():
        if len(objs)>1:out.append(_diag('info','DUPLICATE_TARGETNAME',f'{len(objs)} entities share targetname {name!r}'))
    if profiles.is_goldsrc(scene.wavelength.engine):
        # Classic BSP29/GoldSrc hard limits vary by toolchain; these conservative warnings
        # are authoring guidance, not compile-failure predictions.
        if counts['entities']>900:out.append(_diag('warning','ENTITY_COUNT_HIGH',f"{counts['entities']} point entities; approaching classic engine limits"))
        if counts['faces']>30000:out.append(_diag('warning','FACE_COUNT_HIGH',f"{counts['faces']} source faces; compile complexity is high"))
    for gid,objs in entity_groups.items():
        pairs={o.get('wl_entity_pairs','[]') for o in objs}
        if len(pairs)>1:out.append(_diag('error','BRUSH_ENTITY_PROPERTIES','Brush entity solids have conflicting properties',objs[0]))
    return out
