#Requires -Version 5.1
<#
.SYNOPSIS
    Create .venv and install Python + UI dependencies.

.EXAMPLE
    .\scripts\setup.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$UiRoot = Join-Path $ProjectRoot "agentx-ui"
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Requirements = Join-Path $ProjectRoot "requirements.txt"

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-PythonLauncher {
    foreach ($candidate in @("py -3.11", "py -3", "python", "python3")) {
        $name, $arg = $candidate -split " ", 2
        if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
            continue
        }

        try {
            if ($arg) {
                & $name $arg -c "import sys; print(sys.version_info >= (3, 11))" 2>$null | Out-Null
                if ($LASTEXITCODE -ne 0) { continue }
                return @{ Executable = $name; VenvArgs = @($arg, "-m", "venv") }
            }

            $version = & $name -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null
            if ($LASTEXITCODE -ne 0) { continue }

            $parts = $version.Trim().Split(".")
            if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
                Write-Warning "Found $name ($version) but Python 3.11+ is required."
                continue
            }

            return @{ Executable = $name; VenvArgs = @("-m", "venv") }
        }
        catch {
            continue
        }
    }

    throw @"
Python 3.11+ was not found.

Install Python from https://www.python.org/downloads/ and check
'Add python.exe to PATH' during setup, then open a new PowerShell window.
"@
}

function Ensure-Venv {
    if (Test-Path $VenvPython) {
        Write-Step ".venv already exists at $VenvDir"
        return
    }

    $python = Get-PythonLauncher
    Write-Step "Creating virtual environment at .venv"
    $venvArgs = @($python.VenvArgs + $VenvDir)
    & $python.Executable @venvArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create .venv (exit code $LASTEXITCODE)."
    }
    if (-not (Test-Path $VenvPython)) {
        throw "python -m venv finished but $VenvPython was not created."
    }

    Write-Host "Created .venv successfully." -ForegroundColor Green
}

function Install-PythonDeps {
    if (-not (Test-Path $VenvPython)) {
        throw ".venv is missing. Run setup again or create it with: python -m venv .venv"
    }

    Write-Step "Installing Python dependencies into .venv"
    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }

    & $VenvPython -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

    Write-Step "Installing agentx package (editable)"
    & $VenvPython -m pip install -e $ProjectRoot
    if ($LASTEXITCODE -ne 0) { throw "pip install -e . failed." }
}

function Install-UiDeps {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm is not on PATH. Install Node.js 18+ from https://nodejs.org/"
    }

    Write-Step "Installing UI dependencies (npm install)"
    Push-Location $UiRoot
    try {
        & npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed." }
    }
    finally {
        Pop-Location
    }
}

Push-Location $ProjectRoot
try {
    Write-Host ""
    Write-Host "AgentX setup" -ForegroundColor Green
    Write-Host "Project: $ProjectRoot"
    Write-Host ""

    Ensure-Venv
    Install-PythonDeps
    Install-UiDeps

    Write-Host ""
    Write-Host "Setup complete." -ForegroundColor Green
    Write-Host "Start the app with: .\scripts\start-local.ps1"
}
finally {
    Pop-Location
}
