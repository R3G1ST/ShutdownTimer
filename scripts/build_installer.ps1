$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

& (Join-Path $PSScriptRoot 'build_exe.ps1')
if ($LASTEXITCODE -ne 0) {
    throw "build_exe.ps1 failed with exit code $LASTEXITCODE"
}

$candidates = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    'C:\Program Files\Inno Setup 6\ISCC.exe'
)

$iscc = $null
foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) {
        $iscc = $candidate
        break
    }
}

if (-not $iscc) {
    throw 'ISCC.exe not found. Install Inno Setup 6.'
}

Write-Host "Using ISCC: $iscc"

& $iscc 'installer\setup.iss'
if ($LASTEXITCODE -ne 0) {
    throw "ISCC failed with exit code $LASTEXITCODE"
}

$setup = Join-Path $Root 'installer\Output\ShutdownTimer-Setup-1.0.0.exe'
if (-not (Test-Path -LiteralPath $setup)) {
    throw "Installer output not found: $setup"
}

$size = (Get-Item -LiteralPath $setup).Length
$sizeMb = '{0:N2}' -f ($size / 1MB)
Write-Host "Installer: $setup"
Write-Host "Size: $sizeMb MB ($size bytes)"
