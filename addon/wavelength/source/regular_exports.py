"""Adapters for Blender's Python exporters; preserve every exporter option."""
import importlib
import bpy

_fbx=None
_original_single=None
_original_save=None
_contexts=[]

def _fbx_save(operator,context,*args,**kwargs):
    _contexts.append(context)
    try:return _original_save(operator,context,*args,**kwargs)
    finally:_contexts.pop()

def _fbx_single(operator,scene,depsgraph,*args,**kwargs):
    from .export_scope import Scope
    context=_contexts[-1] if _contexts else None
    owner=context.scene if context and scene.name.startswith('FBX') else scene
    layer=context.view_layer if context and context.scene==owner else None
    scope=Scope(owner,layer)
    objects=kwargs.get('context_objects')
    if objects is None:objects=scene.objects
    kwargs['context_objects']=tuple(obj for obj in objects if scope.includes(obj))
    return _original_single(operator,scene,depsgraph,*args,**kwargs)

def install():
    global _fbx,_original_single,_original_save
    if _fbx:return
    try:_fbx=importlib.import_module('io_scene_fbx.export_fbx_bin')
    except ImportError:return
    _original_single=_fbx.save_single;_original_save=_fbx.save
    _fbx.save_single=_fbx_single;_fbx.save=_fbx_save

def uninstall():
    global _fbx,_original_single,_original_save
    if _fbx:
        if _fbx.save_single is _fbx_single:_fbx.save_single=_original_single
        if _fbx.save is _fbx_save:_fbx.save=_original_save
    _fbx=None;_original_single=None;_original_save=None;_contexts.clear()


def filter_gltf_tree(tree,settings):
    from .export_scope import Scope
    scope=Scope(bpy.context.scene,bpy.context.view_layer)
    for node in tree.nodes.values():
        obj=getattr(node,'blender_object',None)
        if obj is not None and not scope.includes(obj):node.keep_tag=False
