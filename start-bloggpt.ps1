[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$backendDir = Join-Path $projectRoot "server"
$frontendDir = Join-Path $projectRoot "client\bloggpt"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js, then run this launcher again."
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    throw "Frontend dependencies are missing. Run 'npm install' in client\bloggpt once."
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    $backendCommand = "uv run uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload"
}
elseif (Test-Path $venvPython) {
    $backendCommand = "& '$venvPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload"
}
else {
    throw "No backend runtime found. Install uv, or create the project's .venv as described in README.md."
}

$backendScript = "Set-Location '$backendDir'; `$Host.UI.RawUI.WindowTitle = 'BlogGPT Backend'; $backendCommand"
$frontendScript = "Set-Location '$frontendDir'; `$Host.UI.RawUI.WindowTitle = 'BlogGPT Frontend'; npm run dev"

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendScript
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendScript

Write-Host "BlogGPT is starting:"
Write-Host "  Frontend: http://localhost:3000"
Write-Host "  Backend:  http://127.0.0.1:8002"
