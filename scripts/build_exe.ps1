$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

foreach ($dir in @('build', 'dist')) {
    $path = Join-Path $Root $dir
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}

$venvPython = Join-Path $Root '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    $python = $venvPython
} else {
    $python = 'python'
}

& $python -m PyInstaller build.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$exe = Join-Path $Root 'dist\ShutdownTimer.exe'
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Build output not found: $exe"
}

$size = (Get-Item -LiteralPath $exe).Length
$sizeMb = '{0:N2}' -f ($size / 1MB)
Write-Host "Built: $exe"
Write-Host "Size: $sizeMb MB ($size bytes)"
