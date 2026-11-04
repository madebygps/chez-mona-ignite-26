# Starts the Chez Mona launcher and opens it in an Edge app window.
# Usage: .\start.ps1 [-Port 8765] [-NoBrowser]
param(
    [int]$Port,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv was not found. Install it from https://docs.astral.sh/uv/ and try again.'
}

if (-not $Port) {
    $config = if (Test-Path station.json) { 'station.json' } else { 'station.example.json' }
    $Port = (Get-Content $config -Raw | ConvertFrom-Json).port
    if (-not $Port) { $Port = 8765 }
}
$url = "http://localhost:$Port/"

$server = Start-Process uv -ArgumentList 'run', 'python', '-u', '-m', 'chez_mona', '--port', $Port -NoNewWindow -PassThru

$ready = $false
for ($i = 0; $i -lt 60 -and -not $server.HasExited; $i++) {
    try {
        Invoke-WebRequest "$($url)api/labs" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $ready) {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id }
    throw "The launcher did not start on $url. Check the output above."
}

if (-not $NoBrowser) {
    $edge = @(
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $edge) { $edge = 'msedge' }
    Start-Process $edge -ArgumentList "--app=$url", '--start-maximized'
}

Write-Host "Launcher running on $url. Press Ctrl+C here to stop it."
Wait-Process -Id $server.Id
