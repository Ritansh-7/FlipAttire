Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
# Production mode: lean server (~200MB) instead of dev mode (~650MB+).
# Run this once to build, then it serves the built site on :3001.
$env:TEMP = "D:\gt\tmp\next-storefront"
$env:TMP = "D:\gt\tmp\next-storefront"
$env:NEXT_PUBLIC_RECOMMENDER_URL = "http://127.0.0.1:8000"
$env:NEXT_PUBLIC_RECOMMENDER_ONLY = "true"
$env:NODE_OPTIONS = "--max-old-space-size=1536"
$node = "C:\Users\ritan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$yarn = "D:\gt\my-clothing-store\.yarn\releases\yarn-4.12.0.cjs"
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
if (Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Port 3001 busy — stop the dev server first (Get-Process node | Stop-Process)."
    exit 1
}
Set-Location "D:\gt\my-clothing-store"
if (-not (Test-Path ".next\BUILD_ID")) {
    Write-Host "Building production bundle (one-time, a few minutes)…"
    & $node $yarn next build
}
Write-Host "Serving production storefront at http://localhost:3001/in"
& $node $yarn next start -p 3001
