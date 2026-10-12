# Bootstrap only the checksum-pinned private runtime; never use system Python.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
    throw 'This installer requires Windows x86_64.'
}
$lock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime-lock.json') -Raw | ConvertFrom-Json
$runtime = $lock.runtimes.'windows-x86_64'
$destination = Join-Path $root 'runtime'
if (Test-Path -LiteralPath (Join-Path $destination 'python.exe')) { exit 0 }
$temporary = Join-Path $root ('.runtime-' + [Guid]::NewGuid().ToString('N'))
$guard = $null
try {
    $guard = [IO.File]::Open((Join-Path $root '.runtime-windows.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    New-Item -ItemType Directory -Path $temporary | Out-Null
    $archive = Join-Path $temporary 'python.zip'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri $runtime.url -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $runtime.sha256) {
        throw 'Runtime SHA-256 mismatch. Nothing installed.'
    }
    $staging = Join-Path $temporary 'runtime'
    Expand-Archive -LiteralPath $archive -DestinationPath $staging
    if (Test-Path -LiteralPath $destination) { throw 'Incomplete runtime directory exists; preserve it and retry in a fresh source directory.' }
    Move-Item -LiteralPath $staging -Destination $destination
} finally {
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
    if ($null -ne $guard) { $guard.Dispose() }
}
