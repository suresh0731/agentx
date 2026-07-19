#Requires -Version 5.1
<#
.SYNOPSIS
    Start AgentX backend and UI locally on Windows (no Docker).

.DESCRIPTION
    Starts the FastAPI API server and the Vite dev server for agentx-ui.
    SQLite and LangGraph pipeline workers run in-process inside the API.

.PARAMETER Dev
    Enable uvicorn --reload for development.

.PARAMETER Setup
    Install Python and Node dependencies before starting.

.PARAMETER BackendOnly
    Start only the API server.

.PARAMETER UiOnly
    Start only the UI dev server.

.PARAMETER BindHost
    Bind address for the API server (default: 127.0.0.1).

.PARAMETER ApiPort
    API port (default: 8001).

.PARAMETER UiPort
    UI dev server port (default: 5173).

.PARAMETER NoNewWindow
    Run the API in the current console (backend only; UI is not started).

.EXAMPLE
    .\scripts\start-local.ps1

.EXAMPLE
    .\scripts\start-local.ps1 -Dev -Setup
#>
[CmdletBinding()]
param(
    [switch]$Dev,
    [switch]$Setup,
    [switch]$BackendOnly,
    [switch]$UiOnly,
    [string]$BindHost = "127.0.0.1",
    [int]$ApiPort = 8001,
    [int]$UiPort = 5173,
    [switch]$NoNewWindow
)

$ErrorActionPreference = "Stop"

if ($BackendOnly -and $UiOnly) {
    throw "Use only one of -BackendOnly or -UiOnly."
}

$StartBackend = -not $UiOnly
$StartUi = -not $BackendOnly

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$UiRoot = Join-Path $ProjectRoot "agentx-ui"
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvUvicorn = Join-Path $VenvDir "Scripts\uvicorn.exe"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$NodeModules = Join-Path $UiRoot "node_modules"

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-Command([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Escape-SingleQuoted([string]$Value) {
    return $Value -replace "'", "''"
}

function Ensure-PythonVenv {
    if (-not $StartBackend) {
        return
    }

    if (-not (Test-Path $VenvPython)) {
        Write-Step ".venv not found — running setup"
        & (Join-Path $PSScriptRoot "setup.ps1")
        if (-not (Test-Path $VenvPython)) {
            throw ".venv was not created. Run .\scripts\setup.ps1 manually and check for errors."
        }
        return
    }

    if ($Setup) {
        Write-Step "Re-installing Python dependencies (-Setup)"
        & $VenvPython -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
        & $VenvPython -m pip install -r $Requirements
        if ($LASTEXITCODE -ne 0) { throw "pip install failed." }
        return
    }

    if (-not (Test-Path $VenvUvicorn)) {
        Write-Step "Installing Python dependencies"
        & $VenvPython -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
        & $VenvPython -m pip install -r $Requirements
        if ($LASTEXITCODE -ne 0) { throw "pip install failed." }
    }
}

function Ensure-NodeModules {
    if (-not $StartUi) {
        return
    }

    if (-not (Test-Command "npm")) {
        throw "npm is not on PATH. Install Node.js 18+ and try again."
    }

    if ($Setup -or -not (Test-Path $NodeModules)) {
        Write-Step "Installing UI dependencies (npm install)"
        Push-Location $UiRoot
        try {
            & npm install
        }
        finally {
            Pop-Location
        }
    }
}

function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [hashtable]$Environment = @{},
        [string]$Command
    )

    $escapedDir = Escape-SingleQuoted $WorkingDirectory
    $escapedCommand = Escape-SingleQuoted $Command

    $envLines = foreach ($key in $Environment.Keys) {
        $value = Escape-SingleQuoted ([string]$Environment[$key])
        "`$env:$key = '$value'"
    }

    $windowScript = @"
`$Host.UI.RawUI.WindowTitle = '$(Escape-SingleQuoted $Title)'
Set-Location '$escapedDir'
$($envLines -join "`n")
$Command
"@

    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $windowScript
    ) | Out-Null
}

function Wait-ForHttp {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
        Start-Sleep -Seconds 1
        try {
            $null = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing
            return $true
        }
        catch {
            # Service still starting
        }
    }

    return $false
}

Push-Location $ProjectRoot
try {
    Write-Host ""
    Write-Host "AgentX local startup (no Docker)" -ForegroundColor Green
    Write-Host "Project: $ProjectRoot"
    Write-Host ""

    if ($NoNewWindow -and $StartUi) {
        Write-Warning "-NoNewWindow starts only the API. Omit it to launch the UI in a separate window."
        $StartUi = $false
    }

    Ensure-PythonVenv
    Ensure-NodeModules

    if ($StartBackend) {
        $reloadFlag = if ($Dev) { " --reload" } else { "" }
        $uvicornCmd = "& '$VenvUvicorn' agentx.main:app --host $BindHost --port $ApiPort$reloadFlag"

        Write-Step "Starting API on http://${BindHost}:$ApiPort"
        Write-Host "    Health: http://${BindHost}:$ApiPort/health"
        Write-Host "    API:    http://${BindHost}:$ApiPort/api/v1"
        Write-Host ""

        if ($NoNewWindow) {
            $env:PYTHONPATH = Join-Path $ProjectRoot "src"
            $env:AGENTX_DEBUG = if ($Dev) { "true" } else { "false" }
            Invoke-Expression $uvicornCmd
            return
        }

        Start-ServiceWindow `
            -Title "API" `
            -WorkingDirectory $ProjectRoot `
            -Environment @{
                PYTHONPATH = (Join-Path $ProjectRoot "src")
                AGENTX_DEBUG = if ($Dev) { "true" } else { "false" }
            } `
            -Command $uvicornCmd

        Write-Step "Waiting for API health check"
        $healthUrl = "http://${BindHost}:$ApiPort/health"
        if (Wait-ForHttp -Url $healthUrl) {
            Write-Host "API is ready at $healthUrl" -ForegroundColor Green
        }
        else {
            Write-Warning "API did not respond within 30s. Check the API window for errors."
        }
    }

    if ($StartUi) {
        $uiUrl = "http://localhost:$UiPort"
        $uiCmd = "npm run dev -- --host localhost --port $UiPort"

        Write-Step "Starting UI on $uiUrl"
        Write-Host ""

        Start-ServiceWindow `
            -Title "UI" `
            -WorkingDirectory $UiRoot `
            -Command $uiCmd

        Write-Step "Waiting for UI dev server"
        if (Wait-ForHttp -Url $uiUrl) {
            Write-Host "UI is ready at $uiUrl" -ForegroundColor Green
        }
        else {
            Write-Warning "UI did not respond within 30s. Check the UI window for errors."
        }
    }

    if ($StartBackend -and $StartUi) {
        Write-Host ""
        Write-Host "Open http://localhost:$UiPort in your browser." -ForegroundColor Green
    }
}
finally {
    Pop-Location
}
