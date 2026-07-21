[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$backendDir = Join-Path $projectRoot "server"
$frontendDir = Join-Path $projectRoot "client\bloggpt"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

function Test-ListeningPort {
    param([Parameter(Mandatory)][int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        return $connection.AsyncWaitHandle.WaitOne(250) -and $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js, then run this launcher again."
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    throw "Frontend dependencies are missing. Run 'npm install' in client\bloggpt once."
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    $backendCommand = "uv run uvicorn app.main:app --host 127.0.0.1 --port 8002"
}
elseif (Test-Path $venvPython) {
    $backendCommand = "& '$venvPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8002"
}
else {
    throw "No backend runtime found. Install uv, or create the project's .venv as described in README.md."
}

$backendScript = "Set-Location '$backendDir'; `$Host.UI.RawUI.WindowTitle = 'BlogGPT Backend'; $backendCommand"
$frontendScript = "Set-Location '$frontendDir'; `$Host.UI.RawUI.WindowTitle = 'BlogGPT Frontend'; npm.cmd run dev"

if (Test-ListeningPort -Port 8002) {
    Write-Warning "Backend port 8002 is already in use. Keeping the existing backend instead of starting a duplicate."
}
else {
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendScript
}

$frontendPort = 3000..3010 | Where-Object { Test-ListeningPort -Port $_ } | Select-Object -First 1
if ($frontendPort) {
    Write-Warning "A frontend is already running on port $frontendPort. Keeping it instead of starting a duplicate."
}
else {
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendScript
    $frontendPort = 3000
}

Write-Host "BlogGPT is starting:"
Write-Host "  Frontend: http://localhost:$frontendPort"
Write-Host "  Backend:  http://127.0.0.1:8002"
