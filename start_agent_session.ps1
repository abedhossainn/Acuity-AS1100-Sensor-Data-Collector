$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Get-PythonCommand {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @("py", "-3") }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @("python") }

    throw "Python 3 is required but was not found in PATH."
}

function Test-AgentHealthy {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8010/health" -TimeoutSec 3
        return $health.status -eq "ok"
    } catch {
        return $false
    }
}

if (Test-AgentHealthy) {
    Write-Host "Host sensor agent is already running on http://127.0.0.1:8010" -ForegroundColor Green
    exit 0
}

$pyCmd = Get-PythonCommand
$pyExe = $pyCmd[0]
$pyArgsPrefix = @()
if ($pyCmd.Length -gt 1) { $pyArgsPrefix = $pyCmd[1..($pyCmd.Length - 1)] }

$agentReq = Join-Path $root "host_agent/requirements.txt"
if (Test-Path $agentReq) {
    $checkArgs = @()
    $checkArgs += $pyArgsPrefix
    $checkArgs += @("-c", "import fastapi,uvicorn,serial")
    & $pyExe @checkArgs 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing host-agent dependencies..." -ForegroundColor Yellow
        $pipArgs = @()
        $pipArgs += $pyArgsPrefix
        $pipArgs += @("-m", "pip", "install", "-r", $agentReq)
        & $pyExe @pipArgs
    }
}

$agentArgs = @()
$agentArgs += $pyArgsPrefix
$agentArgs += @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8010")

Write-Host "Starting host sensor agent in this terminal..." -ForegroundColor Cyan
Write-Host "Close this terminal or press Ctrl+C to stop the agent." -ForegroundColor Yellow
Set-Location (Join-Path $root "host_agent")
& $pyExe @agentArgs
