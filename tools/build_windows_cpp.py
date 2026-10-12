#!/usr/bin/env python3
"""Cross-compile the standalone Wavelength C ABI library on Linux; never run it.

This library exposes grid math only. It is not the Blender renderer patch.
"""
import argparse
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolchain',type=Path,required=True,help='Extracted LLVM-MinGW directory')
    parser.add_argument('--output',type=Path,default=ROOT/'build/windows-cpp')
    args=parser.parse_args()
    compiler=args.toolchain.resolve()/'bin/x86_64-w64-mingw32-clang++'
    args.output.mkdir(parents=True,exist_ok=True)
    output=args.output/'wavelength_grid.dll'
    subprocess.run([str(compiler),'-std=c++17','-O2','-shared','-static-libgcc','-static-libstdc++','-DWAVELENGTH_NATIVE_BUILD',
                    str(ROOT/'native/src/wavelength_grid.cpp'),str(ROOT/'native/src/wavelength_abi.cpp'),
                    '-I',str(ROOT/'native/include'),'-o',str(output)],check=True)
    print(output)

if __name__=='__main__':main()
