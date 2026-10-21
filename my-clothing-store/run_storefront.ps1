Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$env:TEMP = "D:\gt\tmp\next-storefront"
$env:TMP = "D:\gt\tmp\next-storefront"
$env:NEXT_PUBLIC_RECOMMENDER_URL = "http://127.0.0.1:8000"
$env:NEXT_PUBLIC_RECOMMENDER_ONLY = "true"
$env:NODE_OPTIONS = "--max-old-space-size=1024"
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
if (Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Next storefront already running at http://localhost:3001/in"
    exit 0
}
Set-Location "D:\gt\my-clothing-store"
& "C:\Users\ritan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" ".yarn\releases\yarn-4.12.0.cjs" next dev -p 3001
