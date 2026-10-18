"""Build the exact candidate in an x64 Visual Studio Developer shell."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(args,**kw):return subprocess.run(list(map(str,args)),check=True,**kw)
def require(condition,message):
 if not condition:raise ValueError(message)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('source','build','blender','optix-root'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--jobs',type=int,default=3);p.add_argument('--configure-only',action='store_true');a=p.parse_args()
 lock=json.loads((ROOT/'native/blender/source-5.2.3-candidate.json').read_text());source=a.source.resolve();build=a.build.resolve()
 for tool in ('git','cmake','ninja','lib','dumpbin','cl'):
  if not shutil.which(tool):raise SystemExit('Missing '+tool+'; use an x64 Visual Studio Developer shell')
 for path,key in ((source,'source_commit'),(source/'lib/windows_x64','windows_dependencies_commit')):
  require(subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()==lock[key],key+' mismatch')
 kernel=a.blender.resolve().parent/'cycles_kernel_oneapi_aot.dll';require(hashlib.sha256(kernel.read_bytes()).hexdigest()==lock['oneapi_aot_sha256'],'Kernel checksum mismatch')
 definition=ROOT/'native/blender/oneapi-5.2.3-candidate.def';expected=definition.read_text().split('EXPORTS\n',1)[1].split()
 output=subprocess.check_output(['dumpbin','/EXPORTS',str(kernel)]).decode('utf-8',errors='replace');require(re.findall(r'^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]+\s+(oneapi_\w+)',output,re.M)==expected,'Kernel export mismatch')
 folder=build/'prebuilt';folder.mkdir(parents=True,exist_ok=True);library=folder/'cycles_kernel_oneapi_aot.lib';run(['lib','/DEF:'+str(definition),'/MACHINE:X64','/OUT:'+str(library)])
 patch=ROOT/'native/blender'/lock['source_patch'];require(hashlib.sha256(patch.read_bytes()).hexdigest()==lock['source_patch_sha256'],'Patch checksum mismatch')
 if subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=source,capture_output=True).returncode:
  run(['git','apply','--check',patch],cwd=source);run(['git','apply',patch],cwd=source)
 run(['cmake','-S',source,'-B',build,'-G','Ninja','-C',source/'build_files/cmake/config/blender_release.cmake','-DCMAKE_BUILD_TYPE=Release','-DWITH_GTESTS=OFF','-DWITH_CYCLES_CUDA_BINARIES=OFF','-DWITH_CYCLES_HIP_BINARIES=OFF','-DWITH_CYCLES_ONEAPI_BINARIES=OFF','-DCYCLES_ONEAPI_PREBUILT_IMPORT_LIBRARY='+library.as_posix(),'-DOPTIX_ROOT_DIR='+a.optix_root.resolve().as_posix()])
 if not a.configure_only:run(['cmake','--build',build,'--parallel',max(1,a.jobs)])
if __name__=='__main__':main()
