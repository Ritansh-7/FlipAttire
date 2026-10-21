"""Fetch real fashion photos from Pexels (free API key in D:\\gt\\.env).

Pool: ~18 portrait photos x 6 garment categories -> 100+ fashion shots.
Pexels images are hotlinkable; attribution handled in the storefront footer.
Key is NEVER printed or stored anywhere except .env.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

TMP = Path(r"D:\gt\tmp\pexels")
QUERIES = {
    "tops": ["plain t-shirt apparel", "folded t-shirts stack"],
    "bottoms": ["blue jeans denim", "jeans trousers fashion"],
    "dresses": ["summer dress fashion", "elegant dress model"],
    "jackets": ["denim jacket fashion", "leather jacket style"],
    "shoes": ["sneakers product photography", "shoes fashion"],
    "accessories": ["leather handbag product", "fashion handbag style"],
}
PER_POOL = 18
SAMPLES = 2


def load_key() -> str:
    for line in Path(r"D:\gt\.env").read_text(encoding="utf-8").splitlines():
        if line.startswith("PEXELS_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(".env has no PEXELS_API_KEY")


def pexels(path: str, params: dict, key: str) -> dict:
    url = "https://api.pexels.com/v1/" + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "HMStyleLab/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sized(url: str) -> str:
    base = url.split("?")[0]
    return base + "?auto=compress&cs=tinysrgb&w=600&h=750&fit=crop"


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
                data = pexels("search", {"query": query, "per_page": 20, "orientation": "portrait"}, key)
            except Exception as exc:
                print(f"   query FAIL {query}: {type(exc).__name__}")
                continue
            for photo in data.get("photos", []):
                pid = photo.get("id")
                if pid in seen:
                    continue
                src = (photo.get("src") or {}).get("large") or (photo.get("src") or {}).get("original")
                if not src:
                    continue
                seen[pid] = {
                    "id": pid,
                    "url": sized(src),
                    "photographer": photo.get("photographer", ""),
                    "w": photo.get("width", 0),
                    "h": photo.get("height", 0),
                }
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
    out = TMP / "pexels_pools.json"
    out.write_text(json.dumps(pools, indent=1), encoding="utf-8")
    total = sum(len(v) for v in pools.values())
    print(f"WROTE {out} total={total}")
    for pool, items in pools.items():
        print(f"  {pool}: {len(items)}")


if __name__ == "__main__":
    sys.exit(main())
