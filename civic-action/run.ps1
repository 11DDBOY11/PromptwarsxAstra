# PowerShell script to run Civic Action on Windows
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 1. Backend venv
if (-not (Test-Path "backend\.venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv backend\.venv
}

# 2. Activate venv & install backend requirements
Write-Host "Installing backend dependencies..."
& ".\backend\.venv\Scripts\python.exe" -m pip install -q -r backend\requirements.txt

# 3. Build frontend if dist doesn't exist
if (-not (Test-Path "frontend\dist")) {
    Write-Host "Installing frontend dependencies and building..."
    Set-Location "frontend"
    npm install
    npm run build
    Set-Location $scriptDir
}

# 4. Optional .env
if (Test-Path "backend\.env") {
    Get-Content "backend\.env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}

# 5. Run uvicorn
Write-Host "Starting Civic Action server at http://localhost:8000 ..."
Set-Location "backend"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

