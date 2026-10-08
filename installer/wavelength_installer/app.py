"""Bundled-runtime entry point: add/remove both Wavelength components together."""
import argparse
import json
import sys
from pathlib import Path
from .lifecycle import install,remove,status

def main():
    parser=argparse.ArgumentParser(description='Wavelength installer — Python add-on + native Blender patch')
    parser.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--state',type=Path,default=Path.home()/'.local/share/wavelength/install')
    sub=parser.add_subparsers(dest='action',required=True)
    add=sub.add_parser('install',help='Install both components; rejects unsupported Blender builds')
    add.add_argument('--blender',required=True,type=Path)
    add.add_argument('--addons',required=True,type=Path)
    sub.add_parser('remove',help='Restore original Blender and previous add-on, if any')
    sub.add_parser('recover',help='Roll back an interrupted installation/removal')
    sub.add_parser('status')
    if len(sys.argv)==1 and sys.stdin.isatty():
        print('Wavelength: Python add-on + native patch')
        print('1. Install  2. Remove  3. Status  4. Recover')
        choice=input('Choose [3]: ').strip() or '3'
        action={'1':'install','2':'remove','3':'status','4':'recover'}.get(choice)
        if not action:parser.exit(1,'Unknown choice\n')
        argv=[action]
        if action=='install':argv+=['--blender',input('Blender executable/AppImage: ').strip(),'--addons',input('Blender scripts/addons directory: ').strip()]
        args=parser.parse_args(argv)
    else:args=parser.parse_args()
    try:
        if args.action=='install':result=install(args.bundle,args.blender,args.addons,args.state)
        elif args.action in {'remove','recover'}:result=remove(args.state)
        else:result=status(args.state)
    except (OSError,ValueError,RuntimeError) as exc:
        parser.exit(1,f'Wavelength: {exc}\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
