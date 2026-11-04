# Starts the Chez Mona launcher and opens it in an Edge app window.
# Usage: .\start.ps1 station
#        .\start.ps1 fridge
# Options: -Port 8765 -NoBrowser
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateSet('station', 'fridge')]
    [string]$Role,
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

function Test-PortBusy([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try { return $client.ConnectAsync('127.0.0.1', $Port).Wait(500) } catch { return $false } finally { $client.Dispose() }
}
if (Test-PortBusy $Port) {
    throw "Port $Port is already in use, probably by another Chez Mona window. Press Ctrl+C in that window first, or pass -Port."
}

$serverArgs = @('run', 'python', '-u', '-m', 'chez_mona', '--port', $Port, '--role', $Role)
$server = Start-Process uv -ArgumentList $serverArgs -NoNewWindow -PassThru

$ready = $false
for ($i = 0; $i -lt 60 -and -not $server.HasExited; $i++) {
    try {
        $labs = Invoke-RestMethod "$($url)api/labs" -TimeoutSec 2
        if ($labs.station.role -ne $Role) { throw "Port $Port is answered by a $($labs.station.role), not a $Role." }
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

Write-Host "Chez Mona $Role running on $url. Press Ctrl+C here to stop it."
Wait-Process -Id $server.Id
