Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location "D:\gt"
& powershell -NoProfile -ExecutionPolicy Bypass -File "D:\gt\start_native_stack.ps1"
Start-Sleep -Seconds 8
if (-not (Get-NetTCPConnection -LocalPort 8503 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','D:\gt\run_user_web.ps1'
}
if (-not (Get-NetTCPConnection -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','D:\gt\run_admin_streamlit.ps1'
}
if (-not (Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','D:\gt\my-clothing-store\run_storefront.ps1'
}
Write-Host "User storefront: http://localhost:3001/in"
Write-Host "Admin control room: http://localhost:8502"
Write-Host "API: http://localhost:8000/docs"
