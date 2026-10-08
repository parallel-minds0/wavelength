#!/usr/bin/env python3
"""Download hash-pinned official source excerpts and run the read-only grid probe."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from installer.wavelength_installer.grid_source_probe import probe_source

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,default=ROOT/'build/blender-source')
    args=p.parse_args()
    lock=json.loads((ROOT/'patches/blender-source-lock.json').read_text())
    for relative,digest in lock['files'].items():
        target=args.cache/relative
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==digest:continue
        url=f"https://raw.githubusercontent.com/blender/blender/{lock['commit']}/{relative}"
        data=urllib.request.urlopen(url,timeout=30).read()
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError(f'Source hash mismatch: {relative}')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    report=probe_source(args.cache)
    report['commit']=lock['commit']
    destination=args.cache/'source-report.json'
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(destination)
    if not report['complete']:raise SystemExit(2)

if __name__=='__main__':main()
