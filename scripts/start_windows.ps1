# Build (if needed) and run the FinAlly Docker container.
# Usage: .\scripts\start_windows.ps1 [-Build]
param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ImageName = "finally"
$ContainerName = "finally"
$VolumeName = "finally-data"
$Port = 8000
$Url = "http://localhost:$Port"

Set-Location $RepoRoot

if (-not (Test-Path ".env")) {
    Write-Error "No .env file found at repo root. Copy .env.example to .env and set OPENROUTER_API_KEY."
    exit 1
}

$imageExists = docker image inspect $ImageName 2>$null
if ($Build -or -not $imageExists) {
    Write-Host "Building image $ImageName..."
    docker build -t $ImageName .
}

$existing = docker ps -aq -f "name=^$ContainerName`$"
if ($existing) {
    $running = docker ps -q -f "name=^$ContainerName`$"
    if ($running) {
        Write-Host "FinAlly is already running at $Url"
        exit 0
    }
    Write-Host "Removing stopped container $ContainerName..."
    docker rm $ContainerName | Out-Null
}

docker volume create $VolumeName | Out-Null

Write-Host "Starting FinAlly..."
docker run -d `
    --name $ContainerName `
    -p "${Port}:8000" `
    -v "${VolumeName}:/app/db" `
    --env-file .env `
    -e DB_PATH=/app/db/finally.db `
    $ImageName | Out-Null

Write-Host "FinAlly is running at $Url"
Start-Process $Url
