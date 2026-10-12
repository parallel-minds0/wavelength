# Run in an x64 Visual Studio Developer PowerShell. Prepares only; does not compile.
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed: $LASTEXITCODE" }
}
if (Test-Path C:/wl-source) { throw 'C:/wl-source already exists; use a fresh directory or inspect it before continuing.' }
$env:GIT_LFS_SKIP_SMUDGE = '1'
try {
    Invoke-Checked git @('clone','--depth','1','--branch','v5.2.2','https://github.com/blender/blender.git','C:/wl-source')
} finally { Remove-Item Env:GIT_LFS_SKIP_SMUDGE -ErrorAction SilentlyContinue }
$expected = (Get-Content "$repo/native/blender/source.json" | ConvertFrom-Json).commit
if ((git -C C:/wl-source rev-parse HEAD).Trim() -ne $expected) { throw 'Source revision mismatch' }
Invoke-Checked git @('-C','C:/wl-source','config','lfs.url','https://projects.blender.org/blender/blender.git/info/lfs')
Invoke-Checked git @('-C','C:/wl-source','lfs','pull')
Invoke-Checked git @('-C','C:/wl-source','-c','submodule.lib/windows_x64.update=checkout','submodule','update','--init','--depth','1','lib/windows_x64')
Invoke-Checked git @('-C','C:/wl-source','apply',"$repo/native/blender/grid-5.2.2.patch")
Invoke-WebRequest -Uri https://codeload.github.com/NVIDIA/optix-dev/tar.gz/refs/tags/v8.0.0 -OutFile C:/optix.tar.gz
if ((Get-FileHash C:/optix.tar.gz -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'b32e74c9f5c13549ff3a9760076271b5b6ec28f93fe6a8dd0bde74d7e5c58e05') { throw 'OptiX checksum mismatch' }
Invoke-Checked tar @('-xzf','C:/optix.tar.gz','-C','C:/')
Invoke-Checked cmake @('-S','C:/wl-source','-B','C:/wl-build','-G','Ninja','-C','C:/wl-source/build_files/cmake/config/blender_release.cmake','-DCMAKE_BUILD_TYPE=Release','-DOPTIX_ROOT_DIR=C:/optix-dev-8.0.0','-DWITH_GTESTS=OFF','-DWITH_CYCLES_CUDA_BINARIES=OFF','-DWITH_CYCLES_HIP_BINARIES=OFF','-DWITH_CYCLES_ONEAPI_BINARIES=OFF')
Write-Host 'Ready. Compile with: cmake --build C:/wl-build --parallel 4'
Write-Host 'Output: C:/wl-build/bin/blender.exe'
