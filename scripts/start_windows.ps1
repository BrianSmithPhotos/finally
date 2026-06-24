# FinAlly - start script (Windows PowerShell). Idempotent: safe to re-run.
#
#   .\scripts\start_windows.ps1            # build image if missing, then run
#   .\scripts\start_windows.ps1 -Build     # force a rebuild, then run
#   .\scripts\start_windows.ps1 -Open       # also open the browser
#
# Builds the 'finally' image, runs the 'finally' container with the
# 'finally-data' volume mounted at /app/db, maps port 8000, reads .env.

param(
    [switch]$Build,
    [switch]$Open
)

$ErrorActionPreference = "Stop"

$ImageName     = "finally"
$ContainerName = "finally"
$VolumeName    = "finally-data"
$Port          = "8000"
$Url           = "http://localhost:$Port"

# Resolve project root (this script lives in scripts/).
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir
Set-Location $RootDir

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker is not installed or not on PATH."
    exit 1
}

# Ensure an .env exists (the container reads it via --env-file).
if (-not (Test-Path ".env")) {
    Write-Host "No .env found; creating one from .env.example."
    Write-Host "  -> Edit .env and set OPENROUTER_API_KEY for chat to work."
    Copy-Item ".env.example" ".env"
}

# Build the image if missing or if -Build was passed.
$existingImage = docker images -q $ImageName
if ($Build -or [string]::IsNullOrEmpty($existingImage)) {
    Write-Host "Building image '$ImageName'..."
    docker build -t $ImageName .
} else {
    Write-Host "Image '$ImageName' already present (use -Build to rebuild)."
}

# Remove any existing container with this name (idempotent restart).
$existing = docker ps -aq -f "name=^$ContainerName$"
if (-not [string]::IsNullOrEmpty($existing)) {
    Write-Host "Removing existing container '$ContainerName'..."
    docker rm -f $ContainerName | Out-Null
}

Write-Host "Starting container '$ContainerName'..."
docker run -d `
    --name $ContainerName `
    --env-file .env `
    -p "$($Port):8000" `
    -v "$($VolumeName):/app/db" `
    --restart unless-stopped `
    $ImageName | Out-Null

Write-Host ""
Write-Host "FinAlly is starting at: $Url"
Write-Host "  Logs:  docker logs -f $ContainerName"
Write-Host "  Stop:  .\scripts\stop_windows.ps1"

if ($Open) {
    Start-Process $Url
}
