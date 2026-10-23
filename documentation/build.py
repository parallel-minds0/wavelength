#!/usr/bin/env python3
"""Build this handbook using the implementation checkout's documentation tools."""
import subprocess,sys
from pathlib import Path

def main():
    sources=Path(__file__).resolve().parent
    setting=sources/'.code-root'
    code=(sources/setting.read_text(encoding='utf-8-sig').strip()).resolve() if setting.is_file() else sources.parent
    tool=code/'tools/docs.py'
    if not tool.is_file():raise SystemExit('Set documentation/.code-root to the implementation checkout, relative to documentation/, or run its tools/docs.py with --source pointing here.')
    args=sys.argv[1:] or ['build','--format','all']
    subprocess.run([sys.executable,str(tool),*args,'--source',str(sources)],cwd=code,check=True)

if __name__=='__main__':main()
