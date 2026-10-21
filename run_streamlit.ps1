Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Keep BLAS libraries from creating one worker per logical CPU. This avoids
# OpenBLAS startup allocation failures on Windows and makes memory use stable.
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"
$env:VECLIB_MAXIMUM_THREADS = "1"
$env:BLIS_NUM_THREADS = "1"
$env:TEMP = "D:\gt\tmp\streamlit"
$env:TMP = "D:\gt\tmp\streamlit"
$env:STREAMLIT_CONFIG_DIR = "D:\gt\.streamlit"
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
$env:SPARK_LOCAL_DIRS = "D:\gt\tmp"
$env:PIP_CACHE_DIR = "D:\gt\cache\pip"
$env:HM_UI_LOAD_HISTORY = "0"
$env:KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
New-Item -ItemType Directory -Force -Path $env:TEMP, $env:STREAMLIT_CONFIG_DIR | Out-Null

& "D:\gt\.venv\Scripts\streamlit.exe" run "D:\gt\streamlit_app.py" --server.port 8501
