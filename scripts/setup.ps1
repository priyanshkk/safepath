$ErrorActionPreference = "Stop"

python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Failed to create virtual environment" }

$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements-dev.txt

Write-Host "Setup complete. Activate with: .\.venv\Scripts\Activate.ps1"
Write-Host "Verify with: python -m unittest discover -s tests -v"
