"""Bundled-runtime entry point: add/remove both Wavelength components together."""
import argparse
import json
import sys
from pathlib import Path
from .lifecycle import install,remove,status,recover,repair,read_receipt
from .instances import select

def main():
    parser=argparse.ArgumentParser(description='wavelength installer — Python add-on + native Blender patch')
    parser.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--state',type=Path,default=Path.home()/'.local/share/wavelength/install')
    parser.add_argument('-v','--verbose',action='store_true')
    sub=parser.add_subparsers(dest='action',required=True)
    add=sub.add_parser('install',help='Install wavelength; use --force for optional native support')
    add.add_argument('--blender',type=Path)
    add.add_argument('--addons',type=Path)
    add.add_argument('--allow-unverified',action='store_true',help='Attempt structurally compatible experimental native patch; never ignore byte validation')
    add.add_argument('--force',action='store_true',help='Install Python even when native support is unavailable')
    add.add_argument('--require-native',action='store_true',help='Roll back if native support is unavailable')
    add.add_argument('--accept-experimental-risk',action='store_true',help='Explicitly accept experimental limitations without an interactive prompt')
    add.add_argument('--existing',choices=['replace','side-by-side','abort'])
    for name in ('uninstall','remove'):
        command=sub.add_parser(name,help='Uninstall Python and native components')
        command.add_argument('--force',action='store_true')
        command.add_argument('--keep-state',action='store_true')
    fix=sub.add_parser('repair',help='Repair the selected installation')
    fix.add_argument('--blender',type=Path)
    fix.add_argument('--addons',type=Path)
    fix.add_argument('--force',action='store_true')
    fix.add_argument('--require-native',action='store_true')
    sub.add_parser('recover',help='Roll back an interrupted installation/removal')
    sub.add_parser('status')
    diagnostic=sub.add_parser('diagnose',help='Read-only structural shader inspection')
    diagnostic.add_argument('--blender',type=Path,required=True)
    for command in sub.choices.values():
        command.add_argument('--instance')
        command.add_argument('--yes',action='store_true')
        command.add_argument('-v','--verbose',action='store_true',default=argparse.SUPPRESS)
    if len(sys.argv)==1 and sys.stdin.isatty():
        print('wavelength: Python add-on + native patch',file=sys.stderr)
        print('1. Install  2. Uninstall  3. Repair  4. Status  5. Recover  6. Experimental install  7. Force install',file=sys.stderr)
        choice=input('Choose [4]: ').strip() or '4'
        action={'1':'install','2':'uninstall','3':'repair','4':'status','5':'recover','6':'install','7':'install'}.get(choice)
        if not action:parser.exit(1,'Unknown choice\n')
        argv=[action]
        if action=='install':
            for option,prompt in [('--blender','Blender executable (blank: auto): '),('--addons','Add-ons directory (blank: auto): ')]:
                value=input(prompt).strip()
                if value:argv += [option,value]
        if choice=='7':argv.append('--force')
        if choice=='6':argv.append('--allow-unverified')
        args=parser.parse_args(argv)
    else:args=parser.parse_args()
    try:
        interactive=sys.stdin.isatty() and not args.yes
        def choose(items):
            print('Instances: '+', '.join(items),file=sys.stderr)
            return input('Instance ID: ').strip()
        state_root=args.state.expanduser().resolve()
        args.state=select(state_root,args.instance,choose=choose if interactive else None)
        selected_id="default" if args.state==state_root else args.state.name
        if args.action=='install':
            accepted=False
            if args.accept_experimental_risk and not args.allow_unverified:
                raise ValueError('--accept-experimental-risk requires --allow-unverified')
            if args.allow_unverified and not args.force:
                from .experimental import LIMITATIONS
                print(LIMITATIONS,file=sys.stderr)
                accepted=args.accept_experimental_risk
                if not accepted and interactive:
                    accepted=input('Type INSTALL EXPERIMENTAL to accept these limitations: ').strip()=='INSTALL EXPERIMENTAL'
                if not accepted:raise ValueError('Cancelled; explicit confirmation required (CLI: --accept-experimental-risk). Nothing installed.')
            from .discovery import discover
            args.blender,args.addons=discover(args.blender,args.addons,args.state)
            existing=args.existing or 'replace'
            if args.existing is None and interactive and (read_receipt(args.state)['phase'] not in {'not-installed','removed'} or (args.addons/'wavelength').exists()):
                choice=input('Existing installation: [1] Replace, [2] Side-by-side, [3] Cancel: ').strip()
                existing={'1':'replace','2':'side-by-side'}.get(choice,'abort')
            from .source_bundle import bundle_from_source
            with bundle_from_source(args.bundle) as bundle:
                result=install(bundle,args.blender,args.addons,state_root,instance=selected_id,allow_unverified=args.allow_unverified,confirm_experimental=accepted,force=args.force,require_native=args.require_native,existing=existing)
        elif args.action in {'remove','uninstall'}:result=remove(args.state,force=args.force,keep_state=args.keep_state)
        elif args.action=='repair':
            from .source_bundle import bundle_from_source
            with bundle_from_source(args.bundle) as bundle:
                result=repair(bundle,args.state,blender=args.blender,addons=args.addons,force=args.force,require_native=args.require_native)
        elif args.action=='recover':result=recover(args.state)
        elif args.action=='diagnose':
            from .experimental import analyze
            result=analyze(args.blender.expanduser().read_bytes())
            result.pop('changes',None)
        else:result=status(args.state)
    except (OSError,ValueError,RuntimeError) as exc:
        parser.exit(getattr(exc,'exit_code',1),f'wavelength: {exc}\n')
    print('wavelength: '+result.get('phase',result.get('action','done'))+'; native '+result.get('native_state',result.get('state','unknown')),file=sys.stderr)
    if args.verbose and result.get('native_reason'):print(result['native_reason'],file=sys.stderr)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
