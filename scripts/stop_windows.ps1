# Stop and remove the FinAlly container. Leaves the data volume untouched.
$ErrorActionPreference = "Stop"

$ContainerName = "finally"

$existing = docker ps -aq -f "name=^$ContainerName`$"
if ($existing) {
    Write-Host "Stopping FinAlly..."
    docker stop $ContainerName | Out-Null
    docker rm $ContainerName | Out-Null
    Write-Host "FinAlly stopped."
} else {
    Write-Host "FinAlly is not running."
}
