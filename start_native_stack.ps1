Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = "D:\gt"
$java = "$root\tools\jdk17\bin\java.exe"
$kafka = "$root\tools\kafka"
$kafkaConfig = "$root\infra\kafka\server.properties"
$prometheus = "$root\tools\prometheus\prometheus.exe"
$grafana = "$root\tools\grafana\bin\grafana.exe"
$console = "$root\tools\redpanda-console\redpanda-console.exe"

$env:JAVA_HOME = "$root\tools\jdk17"
$env:Path = "$root\tools\jdk17\bin;" + $env:Path
$env:KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:TEMP = "$root\tmp\native-stack"
$env:TMP = $env:TEMP
$env:GF_PATHS_DATA = "$root\data\grafana"
$env:GF_PATHS_LOGS = "$root\data\grafana\logs"
$env:GF_PATHS_PLUGINS = "$root\data\grafana\plugins"
$env:GF_PATHS_PROVISIONING = "$root\infra\grafana-native\provisioning"
$env:GF_SERVER_HTTP_ADDR = "127.0.0.1"
$env:GF_SERVER_HTTP_PORT = "3000"
$env:GF_SECURITY_ADMIN_USER = "admin"
$env:GF_SECURITY_ADMIN_PASSWORD = "hmadmin"
$env:KAFKA_HEAP_OPTS = "-Xms256M -Xmx512M"
$env:JAVA_TOOL_OPTIONS = "-Djava.io.tmpdir=$root\tmp\native-stack"
New-Item -ItemType Directory -Force -Path $env:TEMP, "$root\data\kafka-logs", "$root\data\prometheus", "$root\data\grafana" | Out-Null
New-Item -ItemType Directory -Force -Path "$root\data\native-logs" | Out-Null

if(-not (Test-Path "$root\data\kafka-cluster-id.txt")) {
    $id = (& "$kafka\bin\windows\kafka-storage.bat" random-uuid).Trim()
    Set-Content -LiteralPath "$root\data\kafka-cluster-id.txt" -Value $id -Encoding ascii
    & "$kafka\bin\windows\kafka-storage.bat" format -t $id -c $kafkaConfig
}

function Start-NativeProcess([string]$name, [string]$file, [string]$arguments, [string]$workingDirectory) {
    $running = if($name -in @("kafka", "api")) {
        $port = if($name -eq "kafka") { 9092 } else { 8000 }
        [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    } else { [bool](Get-Process -Name $name -ErrorAction SilentlyContinue) }
    if(-not $running) {
        Start-Process -FilePath $file -ArgumentList $arguments -WorkingDirectory $workingDirectory -WindowStyle Hidden -RedirectStandardOutput "$root\data\native-logs\$name.out.log" -RedirectStandardError "$root\data\native-logs\$name.err.log"
        Write-Host "Started $name"
    } else { Write-Host "$name already running" }
}

Start-NativeProcess "kafka" "$kafka\bin\windows\kafka-run-class.bat" "kafka.Kafka `"$kafkaConfig`"" $kafka
# Wait for the broker before starting dependents (Console exits fatally if Kafka isn't reachable).
for ($i = 0; $i -lt 30; $i++) {
    if (Get-NetTCPConnection -LocalPort 9092 -State Listen -ErrorAction SilentlyContinue) { break }
    Start-Sleep -Seconds 2
}
Start-NativeProcess "prometheus" $prometheus "--config.file=$root\infra\prometheus\prometheus-native.yml --storage.tsdb.path=$root\data\prometheus --web.listen-address=127.0.0.1:9090" "$root\tools\prometheus"
Start-NativeProcess "grafana" $grafana "server --homepath=$root\tools\grafana" "$root\tools\grafana"
Start-NativeProcess "redpanda-console" $console "--config.filepath=$root\infra\redpanda\console.yaml" "$root\tools\redpanda-console"
Start-NativeProcess "api" "$root\.venv\Scripts\python.exe" "-m uvicorn hm_recommender.api:app --host 127.0.0.1 --port 8000" $root
Write-Host "Native stack: API 8000 | Kafka 9092 | Kafka UI 8080 | Prometheus 9090 | Grafana 3000"
