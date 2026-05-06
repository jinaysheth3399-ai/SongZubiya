#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvRoot = Join-Path $ProjectRoot ".venv"
$SitePackages = Join-Path $VenvRoot "Lib\site-packages"
$PyvenvCfg = Join-Path $VenvRoot "pyvenv.cfg"

if (!(Test-Path -LiteralPath $SitePackages)) {
    throw "Could not find virtualenv site-packages at: $SitePackages"
}

$exclusionPaths = @($SitePackages)

if (Test-Path -LiteralPath $PyvenvCfg) {
    $pythonHome = Get-Content -LiteralPath $PyvenvCfg |
        Where-Object { $_ -match "^home\s*=\s*(.+)$" } |
        ForEach-Object { $Matches[1].Trim() } |
        Select-Object -First 1

    if ($pythonHome) {
        $pythonDlls = Join-Path $pythonHome "DLLs"
        if (Test-Path -LiteralPath $pythonDlls) {
            $exclusionPaths += $pythonDlls
        }
    }
}

Write-Host "Adding Microsoft Defender path exclusions:"
$exclusionPaths | ForEach-Object { Write-Host "  $_" }

Add-MpPreference -ExclusionPath $exclusionPaths

Write-Host "Done. Restart any stuck Python/uvicorn processes before trying again."
