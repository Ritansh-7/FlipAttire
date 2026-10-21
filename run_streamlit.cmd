@echo off
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"
set "VECLIB_MAXIMUM_THREADS=1"
set "BLIS_NUM_THREADS=1"
set "SPARK_LOCAL_DIRS=D:\gt\tmp"
set "PIP_CACHE_DIR=D:\gt\cache\pip"
call "D:\gt\.venv\Scripts\streamlit.exe" run "D:\gt\streamlit_app.py" --server.port 8501
