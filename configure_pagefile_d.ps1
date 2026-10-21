# Requires an elevated PowerShell and a restart to take effect.
$ErrorActionPreference = "Stop"
$memoryKey = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
$backup = "D:\gt\data\pagefile-registry-backup.txt"
$current = (Get-ItemProperty -LiteralPath $memoryKey -Name PagingFiles -ErrorAction SilentlyContinue).PagingFiles
Set-Content -LiteralPath $backup -Value ($current -join [Environment]::NewLine) -Encoding ascii

# Disable automatic pagefile placement and put the managed pagefile on D:.
$computer = Get-CimInstance -ClassName Win32_ComputerSystem
Set-CimInstance -InputObject $computer -Property @{AutomaticManagedPagefile = $false} | Out-Null
Set-ItemProperty -LiteralPath $memoryKey -Name PagingFiles -Type MultiString -Value @("D:\pagefile.sys 8192 16384")

Write-Host "Configured D:\pagefile.sys with 8192-16384 MB. Restart Windows to apply."
