Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$env:TEMP = "D:\gt\tmp\web-user"
$env:TMP = "D:\gt\tmp\web-user"
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
Set-Location "D:\gt\web_user"
& "D:\gt\.venv\Scripts\python.exe" -m http.server 8503 --bind 127.0.0.1
