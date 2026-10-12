#!/usr/bin/env python3
"""Generate an installer delta from original and internally built executables.

Requires bsdiff4==1.2.6 in the maintainer environment only. End-user installation
uses the standard-library decoder, and never invokes a compiler or downloads Blender.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installer.wavelength_installer.delta_patch import apply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--patched', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--platform', choices=['linux-x86_64', 'windows-x86_64'], required=True)
    args = parser.parse_args()
    import bsdiff4
    original, patched = args.original.read_bytes(), args.patched.read_bytes()
    if not all(name in patched for name in (b'wavelength_grid_enabled', b'wavelength_grid_spacing', b'wavelength_grid_subdivisions')):
        raise SystemExit('Internal build has no native grid API')
    if original == patched:
        raise SystemExit('Input is already patched')
    payload = bsdiff4.diff(original, patched)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    name = args.platform+'-'+sha(original)[:16]+'.bsdiff'
    entry = {'platform': args.platform, 'input_sha256': sha(original), 'output_sha256': sha(patched),
             'output_size': len(patched), 'patch_sha256': sha(payload), 'file': name, 'native_grid_abi': 1}
    if apply(original, payload, entry) != patched:
        raise SystemExit('Standard-library patch round-trip failed')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/name).write_bytes(payload)
    manifest = args.output/'manifest.json'
    data = json.loads(manifest.read_text()) if manifest.exists() else {'schema': 1, 'patches': []}
    data['patches'] = [e for e in data['patches'] if (e['platform'],e['input_sha256']) != (entry['platform'],entry['input_sha256'])] + [entry]
    manifest.write_text(json.dumps(data, indent=2)+'\n')
    print(json.dumps(entry, indent=2))

if __name__ == '__main__': main()
