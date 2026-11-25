"""Godot environment bundle adapter. Runtime policy stays in the game.

GLBs contain terrain modules and shared prototypes, never flattened forests.
Schema-1 JSON retains masks, rules, IDs, overrides and Y-up instance matrices.
"""
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

import bpy
from mathutils import Matrix
from . import environment_layers as layers, mesh_assets

AXIS=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))


def godot_transform(matrix):
    result=AXIS @ Matrix(matrix) @ AXIS.inverted()
    # Godot Transform3D constructor: basis columns followed by origin.
    return [result[r][c] for c in range(4) for r in range(3)]


def export_mesh(context,obj,directory,name,world=True,material_override=False):
    """Reuse the validated mesh exporter from an isolated evaluated scene."""
    mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(context.evaluated_depsgraph_get()),
                                        preserve_all_data_layers=True,depsgraph=context.evaluated_depsgraph_get())
    if material_override:mesh.materials.clear()
    scene=bpy.data.scenes.new('.wavelength environment export')
    clone=bpy.data.objects.new(name,mesh);scene.collection.objects.link(clone)
    # Prototype placement is separate from authored local geometry and scale.
    clone.matrix_world=obj.matrix_world if world else Matrix.Identity(4)
    window=context.window;previous=window.scene if window else None
    try:
        if window:window.scene=scene
        with context.temp_override(scene=scene,view_layer=scene.view_layers[0]):
            return mesh_assets.export(context,str(directory),engine='godot4',name=name)[0]
    finally:
        if window:window.scene=previous
        bpy.data.objects.remove(clone,do_unlink=True);bpy.data.scenes.remove(scene)
        if mesh.users==0:bpy.data.meshes.remove(mesh)


def export(context,objects,directory):
    if context.mode!='OBJECT':raise ValueError('Leave paint/edit mode before exporting the environment')
    objects=list(objects)
    if not objects:raise ValueError('Select terrain meshes with environment layers')
    from .export_scope import Scope
    scope=Scope(context.scene,context.view_layer)
    if any(not scope.includes(o) or o.get('wl_exclude') for o in objects):
        raise ValueError('Selected terrain is excluded from export; enable its inclusion first')
    if any(o.get('wl_environment_edit') for o in context.scene.objects):
        raise ValueError('Keep or discard pending placement corrections before export')
    if len({layers.identity(o) for o in objects})!=len(objects):
        raise ValueError('Terrain copies have duplicate identities; assign independent IDs before exporting')
    if not str(directory).strip():raise ValueError('Choose an environment export directory')
    destination=Path(bpy.path.abspath(directory)).resolve()
    if destination.exists() and not (destination/'environment.json').is_file():
        raise ValueError('Choose a new directory or a previous environment bundle')
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.wl-environment-',dir=destination.parent))
    document={'schema':1,'engine':'godot4','meters_per_unit':1.,'up_axis':'Y',
              'matrix_layout':'basis_columns_then_origin','terrain':[],'prototypes':{},'batches':[],
              'runtime_policy':'Game owns streaming, collisions, lighting, seasons and gameplay'}
    try:
        for obj in objects:
            uid=layers.identity(obj)
            painted=any(l.enabled and l.kind=='MATERIAL' for l in obj.wavelength_environment_layers)
            path=export_mesh(context,obj,stage/'terrain',uid,material_override=painted or bool(obj.wavelength_environment_native_material))
            entry={'id':uid,'name':obj.name,'mesh':path.relative_to(stage).as_posix(),'layers':[]}
            surface=layers.Surface(context,obj)
            try:
                from .environment_materials import export_description
                entry['material_adapter']=export_description(obj,surface,stage)
                # Coordinates match the evaluated world-space terrain GLB.
                mask_document={'schema':1,'space':'godot_world_meters',
                               'vertices':[list((AXIS @ v.to_4d()).to_3d()) for v in surface.vertices],
                               'triangles':surface.triangles,'masks':{}}
                for layer in obj.wavelength_environment_layers:
                    values=[];index=surface.groups.get(layer.mask)
                    if index is None:raise ValueError(f'{obj.name}: missing mask {layer.mask}')
                    for vertex in surface.mesh.vertices:
                        values.append(next((g.weight for g in vertex.groups if g.group==index),0.))
                    mask_document['masks'][layer.uid]=values
                    data={'id':layer.uid,'name':layer.name,'kind':layer.kind,'enabled':layer.enabled,'mode':layer.mode,
                          'mask_group':layer.mask,'material':layer.material.name if layer.material else None,
                          'overrides_blender_world':layers.overrides(layer)}
                    if layer.mode=='PLACEMENTS' and layer.placements:
                        data['adopted_source']=layer.source_origin
                    entry['layers'].append(data)
                    if layer.kind!='DISTRIBUTION' or not layer.enabled:continue
                    prototypes=layers.palette(layer)
                    data['rules']={key:getattr(layer,key) for key in
                                   ('density','cell_size','seed','max_slope','scale_min','scale_max','align_normal')}
                    data['palette']=[{'id':layers.identity(p),'weight':p.wavelength_environment_weight} for p in prototypes]
                    for prototype in prototypes:
                        key=layers.identity(prototype)
                        if key not in document['prototypes']:
                            native=prototype.wavelength_environment_godot_scene.strip()
                            if native:
                                if not native.startswith('res://') or '..' in native.split('/'):
                                    raise ValueError('Native prototype references must be Godot res:// paths')
                                reference=native
                            else:
                                output=export_mesh(context,prototype,stage/'prototypes',key,world=False)
                                reference=output.relative_to(stage).as_posix()
                            document['prototypes'][key]={'name':prototype.name,'scene':reference}
                    batches={}
                    for record in layers.records(context,obj,layer,surface):
                        transform=godot_transform(record['matrix'])
                        # Export partitions are data, not a streaming implementation.
                        key=(record['prototype'],math.floor(transform[9]/128),math.floor(transform[11]/128))
                        batches.setdefault(key,[]).append({'id':record['id'],'transform':transform})
                    for (prototype,x,z),items in sorted(batches.items()):
                        document['batches'].append({'terrain':uid,'layer':layer.uid,'prototype':prototype,
                                                   'cell':[x,z],'instances':items})
                masks=stage/'masks'/f'{uid}.json';masks.parent.mkdir(exist_ok=True)
                masks.write_text(json.dumps(mask_document,separators=(',',':')),encoding='utf-8')
                entry['masks']=masks.relative_to(stage).as_posix()
                document['terrain'].append(entry)
            finally:surface.close()
        script=Path(__file__).parents[1]/'environment/adapters/godot/environment_loader.gd'
        shutil.copyfile(script,stage/'environment_loader.gd')
        (stage/'environment.tscn').write_text('[gd_scene load_steps=2 format=3]\n\n[ext_resource type="Script" path="environment_loader.gd" id="1"]\n\n[node name="WavelengthEnvironment" type="Node3D"]\nscript = ExtResource("1")\nmanifest_path = "environment.json"\n',encoding='utf-8')
        (stage/'environment.json').write_text(json.dumps(document,indent=2,allow_nan=False),encoding='utf-8')
        # Stage all work first. Swap only this explicit generated bundle.
        backup=None
        if destination.exists():
            backup=Path(tempfile.mkdtemp(prefix='.wl-environment-old-',dir=destination.parent))
            backup.rmdir();os.replace(destination,backup)
        try:os.replace(stage,destination)
        except OSError:
            if backup:os.replace(backup,destination)
            raise
        if backup and backup.parent==destination.parent and backup.name.startswith('.wl-environment-old-'):
            try:shutil.rmtree(backup)
            except OSError as exc:
                # Windows asset watchers may still hold an old imported GLB.
                # The new bundle is already committed; do not report it as failed.
                document.setdefault('warnings',[]).append(f'Previous generated files retained at {backup}: {exc}')
                (destination/'environment.json').write_text(json.dumps(document,indent=2,allow_nan=False),encoding='utf-8')
        return destination/'environment.json',document
    finally:
        if stage.exists() and stage.parent==destination.parent and stage.name.startswith('.wl-environment-'):
            shutil.rmtree(stage)


class WL_OT_export_environment(bpy.types.Operator):
    bl_idname='wavelength.export_environment';bl_label='Export Environment to Godot'
    directory:bpy.props.StringProperty(name='Bundle Directory',subtype='DIR_PATH')
    def invoke(self,context,event):
        context.window_manager.fileselect_add(self);return {'RUNNING_MODAL'}
    def execute(self,context):
        try:
            objects=[o for o in context.selected_objects if o.type=='MESH' and o.wavelength_environment_layers]
            path,document=export(context,objects,self.directory)
            count=sum(len(b['instances']) for b in document['batches'])
            self.report({'INFO'},f'Exported {len(objects)} terrain modules and {count} instances: {path}')
        except (ValueError,RuntimeError,OSError) as exc:
            self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}


def register():
    bpy.types.Object.wavelength_environment_godot_scene=bpy.props.StringProperty(name='Godot Prototype Scene',description='Optional existing res:// scene; blank exports local mesh prototype')
    bpy.utils.register_class(WL_OT_export_environment)


def unregister():
    bpy.utils.unregister_class(WL_OT_export_environment)
    del bpy.types.Object.wavelength_environment_godot_scene
