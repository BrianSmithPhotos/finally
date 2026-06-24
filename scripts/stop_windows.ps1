# FinAlly - stop script (Windows PowerShell). Idempotent: safe to re-run.
# Stops and removes the container. PRESERVES the 'finally-data' volume (data
# persists across restarts).
#
#   .\scripts\stop_windows.ps1

$ErrorActionPreference = "Stop"

$ContainerName = "finally"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker is not installed or not on PATH."
    exit 1
}

$existing = docker ps -aq -f "name=^$ContainerName$"
if (-not [string]::IsNullOrEmpty($existing)) {
    Write-Host "Stopping and removing container '$ContainerName'..."
    docker rm -f $ContainerName | Out-Null
    Write-Host "Done. The 'finally-data' volume was preserved."
} else {
    Write-Host "No container named '$ContainerName' is running."
}
