import bpy,sys,json,traceback
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import wavelength
print('REGISTER begin',flush=True);wavelength.register();print('REGISTER done',flush=True)
from wavelength.source import workspace,system_tree,system_tree_view as tree
bpy.context.preferences.view.show_splash=False
stage=0
out=root/'build/system-tree';out.mkdir(parents=True,exist_ok=True)
def test():
 global stage
 try:
  print('STAGE',stage,flush=True)
  c=bpy.context
  if stage==0:
   ws=workspace.ensure(c);c.window.workspace=ws
   c.scene.wavelength.engine='source_hl2_windows'
   obj=bpy.data.objects.new('prop_static.001',None);c.collection.objects.link(obj);obj['wl_role']='ENTITY';obj['wl_pairs']=json.dumps([['classname','prop_static']])
   ref=bpy.data.objects.new('Prop Model',bpy.data.meshes.new('Prop Mesh'));c.collection.objects.link(ref);ref.parent=obj;ref['wl_role']='MODEL_REFERENCE';ref['wl_model_reference']=True
   stage=1;return 4
  if stage==1:
   trees=[]
   for a in c.screen.areas:
    with c.temp_override(area=a):
     if tree.is_tree(c):trees.append(a)
   assert len(trees)==1,[(a.type,a.x,a.y,a.width,a.height) for a in c.screen.areas]
   a=trees[0];above=[o for o in c.screen.areas if o.type=='OUTLINER' and o.x==a.x];below=[o for o in c.screen.areas if o.type=='PROPERTIES' and o!=a and o.x==a.x]
   assert above and below and above[0].y>a.y>below[0].y
   assert bpy.ops.wavelength.system_category_visibility(category='PROPS')=={'FINISHED'}
   assert c.scene.objects['prop_static.001'].hide_get() and c.scene.objects['Prop Model'].hide_get()
   assert bpy.ops.wavelength.system_category_visibility(category='PROPS')=={'FINISHED'}
   assert not c.scene.objects['Prop Model'].hide_get()
   tree.ensure(c)
   bpy.ops.screen.screenshot(filepath=str(out/'system-tree.png'))
   bpy.ops.wm.save_as_mainfile(filepath=str(out/'system-tree.blend'))
   stage=2;return 1
  elif stage==2:
   stage=3;bpy.ops.wm.open_mainfile(filepath=str(out/'system-tree.blend'));return 2
  else:
   assert any(a.type=='PROPERTIES' and a.spaces.active.show_properties_scene and not a.spaces.active.show_properties_object for a in c.screen.areas)
   print('PASS System Tree: middle right slot, idempotent layout, props and model visibility',flush=True)
   tree.unregister();print('PASS tree unregister',flush=True);tree.register();print('PASS tree re-register',flush=True)
   c.window.workspace=bpy.data.workspaces['Layout']
   wavelength.unregister();print('PASS unregister',flush=True);bpy.ops.wm.quit_blender()
 except Exception:
  traceback.print_exc();print('FAIL System Tree',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(test,first_interval=2,persistent=True)

