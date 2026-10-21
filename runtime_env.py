from __future__ import annotations

import os
from pathlib import Path


def configure() -> None:
    """Keep this process' temporary, cache and numerical work on D:."""
    root = Path("D:/gt")
    temp = root / "tmp" / "streamlit"
    config = root / ".streamlit"
    temp.mkdir(parents=True, exist_ok=True)
    config.mkdir(parents=True, exist_ok=True)
    values = {
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "BLIS_NUM_THREADS": "1",
        "TEMP": str(temp),
        "TMP": str(temp),
        "STREAMLIT_CONFIG_DIR": str(config),
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        "SPARK_LOCAL_DIRS": str(root / "tmp"),
        "PIP_CACHE_DIR": str(root / "cache" / "pip"),
    }
    for key, value in values.items():
        os.environ[key] = value


configure()
