"""Fetch fashion photos from Pixabay (free API key in D:\\gt\\.env as PIXABAY_API_KEY).

Pool: ~18 portrait photos x 6 garment categories.
Pixabay CDN images are hotlinkable; no attribution required (appreciated).
Key is NEVER printed or stored anywhere except .env.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

TMP = Path(r"D:\gt\tmp\pixabay")
QUERIES = {
    "tops": ["t-shirt fashion", "folded t-shirts"],
    "bottoms": ["jeans denim fashion", "blue jeans"],
    "dresses": ["summer dress fashion", "dress model"],
    "jackets": ["jacket fashion", "leather jacket"],
    "shoes": ["sneakers", "shoes fashion"],
    "accessories": ["handbag", "leather bag fashion"],
}
PER_POOL = 18
SAMPLES = 2


def load_key() -> str:
    for line in Path(r"D:\gt\.env").read_text(encoding="utf-8").splitlines():
        if line.startswith("PIXABAY_API_KEY=") and line.split("=", 1)[1].strip():
            return line.split("=", 1)[1].strip()
    raise RuntimeError("PIXABAY_API_KEY missing in D:\\gt\\.env")


def pixabay(params: dict, key: str) -> dict:
    params = {"key": key, **params}
    url = "https://pixabay.com/api/?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "HMStyleLab/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def alive(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HMStyleLab/1.0"}, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> None:
    key = load_key()
    TMP.mkdir(parents=True, exist_ok=True)
    pools: dict[str, list[dict]] = {}
    for pool, queries in QUERIES.items():
        print(f"== {pool}", flush=True)
        seen: dict[int, dict] = {}
        for query in queries:
            if len(seen) >= PER_POOL + 6:
                break
            try:
                data = pixabay(
                    {
                        "q": query,
                        "image_type": "photo",
                        "orientation": "vertical",
                        "category": "fashion",
                        "per_page": 20,
                        "safesearch": "true",
                    },
                    key,
                )
            except Exception as exc:
                print(f"   query FAIL {query}: {type(exc).__name__}")
                continue
            for hit in data.get("hits", []):
                pid = hit.get("id")
                if pid in seen:
                    continue
                url = hit.get("webformatURL") or hit.get("largeImageURL")
                if not url:
                    continue
                seen[pid] = {"id": pid, "url": url, "photographer": hit.get("user", "")}
            time.sleep(1)
        kept: list[dict] = []
        for info in seen.values():
            if len(kept) >= PER_POOL:
                break
            if alive(info["url"]):
                kept.append(info)
                print(f"   OK {info['id']} {str(info['photographer'])[:40]}")
            time.sleep(0.3)
        pools[pool] = kept
        for i, info in enumerate(kept[:SAMPLES]):
            dest = TMP / f"{pool}_{i}.jpg"
            try:
                req = urllib.request.Request(info["url"], headers={"User-Agent": "HMStyleLab/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as fh:
                    fh.write(resp.read())
                print(f"   sample -> {dest}")
            except Exception as exc:
                print(f"   sample FAIL: {type(exc).__name__}")
    out = TMP / "pixabay_pools.json"
    out.write_text(json.dumps(pools, indent=1), encoding="utf-8")
    total = sum(len(v) for v in pools.values())
    print(f"WROTE {out} total={total}")
    for pool, items in pools.items():
        print(f"  {pool}: {len(items)}")


if __name__ == "__main__":
    sys.exit(main())
