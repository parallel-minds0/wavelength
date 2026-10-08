#!/usr/bin/env python3
"""Standalone patcher CLI. No modifications without an explicit install command."""
import argparse
import json
from pathlib import Path
from wavelength_installer.core import discover_compilers, discover_python_runtimes, inspect_blender, patch_compatibility, build_native, install_addon, patch_blender
from wavelength_installer.renderer_probe import probe_renderer, write_probe
from wavelength_installer.native_bridge import NativeGrid
from wavelength_installer.binary_patch import apply_recipe

def main():
    p=argparse.ArgumentParser(description='Wavelength installer foundation')
    sub=p.add_subparsers(dest='command', required=True)
    sub.add_parser('compilers')
    sub.add_parser('python-runtimes')
    compat=sub.add_parser('patch-compatibility');compat.add_argument('blender_binary')
    inspect=sub.add_parser('inspect');inspect.add_argument('blender_binary')
    build=sub.add_parser('build-native');build.add_argument('--compiler')
    install=sub.add_parser('install-addon');install.add_argument('addon_zip');install.add_argument('scripts_addons')
    probe=sub.add_parser('probe-native');probe.add_argument('library');probe.add_argument('--step',type=float,default=0.4064);probe.add_argument('--coordinate',type=float,default=0.8128)
    safe_patch=sub.add_parser('apply-verified-patch');safe_patch.add_argument('blender_binary');safe_patch.add_argument('recipe_json');safe_patch.add_argument('output_binary')
    renderer=sub.add_parser('probe-renderer');renderer.add_argument('blender_binary');renderer.add_argument('--report')
    sub.add_parser('patch-blender')
    args=p.parse_args()
    if args.command=='compilers':print(json.dumps(discover_compilers(),indent=2))
    elif args.command=='python-runtimes':print(json.dumps(discover_python_runtimes(),indent=2))
    elif args.command=='patch-compatibility':print(json.dumps(patch_compatibility(args.blender_binary),indent=2))
    elif args.command=='inspect':print(json.dumps(inspect_blender(args.blender_binary),indent=2))
    elif args.command=='build-native':print(build_native(Path(__file__).resolve().parents[1]/'native',Path(__file__).resolve().parents[1]/'build',args.compiler))
    elif args.command=='install-addon':print(install_addon(args.addon_zip,args.scripts_addons))
    elif args.command=='probe-native':print(json.dumps({'highlight': NativeGrid(args.library).is_highlight_line(args.coordinate,args.step)}))
    elif args.command=='apply-verified-patch':print(apply_recipe(args.blender_binary,args.recipe_json,args.output_binary))
    elif args.command=='probe-renderer':
        print(write_probe(args.blender_binary,args.report) if args.report else json.dumps(probe_renderer(args.blender_binary),indent=2))
    elif args.command=='patch-blender':patch_blender()
if __name__=='__main__':main()
