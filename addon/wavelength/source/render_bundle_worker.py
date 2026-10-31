"""Prepare each unique render asset and write one shared Blender library."""
import json,sys,traceback
from pathlib import Path
from types import SimpleNamespace


def run(folder):
    import bpy
    from wavelength.source import source_assets,model_import,worker_status
    from wavelength.source.library_prepare_worker import write,parent_alive
    folder=Path(folder);request=json.loads((folder/'request.json').read_text(encoding='utf-8'))
    settings=SimpleNamespace(**request['settings'],id_data={'wl_source_blender_rendering':True})
    blocks=set();errors=[];models={};materials={};all_materials={}
    def status(**value):worker_status.publish(folder/'status.jsonl',value)
    try:
        count=len(request['materials'])+len(request['models']);done=0
        for name in request['materials']:
            if not parent_alive(request['parent_pid']):return
            try:
                mat=source_assets.material(settings,name);materials[name]=mat.name;all_materials[mat.name]=mat.name;blocks.add(mat)
            except (OSError,ValueError,RuntimeError) as exc:errors.append(name+': '+str(exc))
            done+=1;status(state='PREPARING',done=done,total=count)
        for key,item in request['models'].items():
            if not parent_alive(request['parent_pid']):return
            path,skin,body=item
            try:
                try:mesh,_=model_import.mesh(settings,path,skin,body)
                except ValueError as exc:
                    if str(exc)!='Invalid model skin/body selection':raise
                    mesh,_=model_import.mesh(settings,path,0,0)
                models[key]=mesh.name;blocks.add(mesh)
                for mat in mesh.materials:
                    if mat:all_materials[mat.name]=mat.name
            except (OSError,ValueError,RuntimeError) as exc:errors.append(path+': '+str(exc))
            done+=1;status(state='PREPARING',done=done,total=count)
        destination=Path(request['bundle']);library=destination.with_suffix('.blend')
        destination.parent.mkdir(parents=True,exist_ok=True)
        temporary=library.with_suffix('.tmp.blend')
        status(state='PACKING',done=count,total=count)
        # A single dependency closure preserves shared materials/images and mesh
        # slots. The editor reads this library once, not once per asset.
        bpy.data.libraries.write(str(temporary),blocks,fake_user=True,compress=False)
        temporary.replace(library)
        write(destination,dict(library=str(library),requests=materials,materials=all_materials,models=models,errors=errors))
        status(state='READY',done=count,total=count)
    except Exception as exc:
        traceback.print_exc();status(state='ERROR',message=str(exc))


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    run(sys.argv[sys.argv.index('--')+1])
