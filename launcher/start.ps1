# Starts the Chez Mona launcher and opens it in an Edge app window.
# Usage: .\start.ps1 station    (all 6 cooking stations)
#        .\start.ps1 fridge A   (fridges A and B)
# Leave out the fridge letter and the script asks for it. It prefixes the
# fridge's order numbers so the two fridges never print the same one.
# Options: -Port N -NoBrowser (default port: 8765 station, 8766 fridge)
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateSet('station', 'fridge')]
    [string]$Role,
    [Parameter(Position = 1)]
    [string]$Letter,
    [int]$Port,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv was not found. Install it from https://docs.astral.sh/uv/ and try again.'
}

if ($Role -eq 'station') {
    if ($Letter) { throw "Stations don't take a number or letter. Run .\start.ps1 station" }
} else {
    while ($Letter -notmatch '^[A-Za-z]$') {
        if ($Letter) { Write-Host "'$Letter' is not a fridge letter." }
        $Letter = (Read-Host 'Which fridge is this laptop? Type A or B').Trim()
    }
    $Letter = $Letter.ToUpper()
}

if (-not $Port) { $Port = @{ station = 8765; fridge = 8766 }[$Role] }
$url = "http://localhost:$Port/"

function Test-PortBusy([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try { return $client.ConnectAsync('127.0.0.1', $Port).Wait(500) } catch { return $false } finally { $client.Dispose() }
}
if (Test-PortBusy $Port) {
    throw "Port $Port is already in use, probably by another Chez Mona window. Press Ctrl+C in that window first, or pass -Port."
}

$serverArgs = @('run', 'python', '-u', '-m', 'chez_mona', '--port', $Port, '--role', $Role)
if ($Letter) { $serverArgs += @('--letter', $Letter) }
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

Write-Host "Chez Mona $("$Role $Letter".Trim()) running on $url. Press Ctrl+C here to stop it."
Wait-Process -Id $server.Id
