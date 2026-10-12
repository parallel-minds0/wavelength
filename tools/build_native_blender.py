#!/usr/bin/env python3
"""Apply the native grid patch to matching Blender sources and build a separate executable."""
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(args,**kw):return subprocess.run(args,check=True,**kw)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--jobs',type=int,default=4)
    parser.add_argument('--configure-only',action='store_true')
    parser.add_argument('--cmake-arg', action='append', default=[],
                        help='Additional CMake definition, for example --cmake-arg=-DWITH_X11_XINPUT=OFF')
    args=parser.parse_args()
    lock=json.loads((ROOT/'native/blender/source.json').read_text())
    source=args.source.resolve();build=args.build.resolve()
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if revision!=lock['commit']:raise SystemExit('Use the exact Blender source commit in native/blender/source.json')
    patch=ROOT/'native/blender/grid-5.2.2.patch'
    applied=subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=source,capture_output=True).returncode==0
    if not applied:
        run(['git','apply','--check',str(patch)],cwd=source)
        run(['git','apply',str(patch)],cwd=source)
    run(['cmake','-S',str(source),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
         '-DWITH_CYCLES_DEVICE_CUDA=OFF','-DWITH_CYCLES_DEVICE_HIP=OFF',
         '-DWITH_CYCLES_DEVICE_ONEAPI=OFF','-DWITH_CYCLES_DEVICE_OPTIX=OFF','-DWITH_GTESTS=OFF', *args.cmake_arg])
    if not args.configure_only:
        run(['cmake','--build',str(build),'--parallel',str(max(1,args.jobs))])
        run(['cmake','--install',str(build),'--prefix',str(build/'bin')])
if __name__=='__main__':main()
