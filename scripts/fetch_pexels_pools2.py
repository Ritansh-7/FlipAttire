"""Second Pexels pool batch: gender-aware + garment-specific photos.

Writes D:\\gt\\tmp\\pexels\\pexels_pools2.json (merged into pexels-photos.ts later).
Reuses connection helpers from fetch_pexels_photos (same .env key).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"D:\gt\scripts")
from fetch_pexels_photos import alive, load_key, pexels, sized

TMP = Path(r"D:\gt\tmp\pexels")
QUERIES = {
    "tops_men": ["man white t-shirt", "man wearing tshirt"],
    "tops_women": ["woman white t-shirt", "woman wearing tshirt"],
    "bottoms_men": ["man jeans", "man denim jeans"],
    "bottoms_women": ["woman jeans", "woman denim"],
    "jackets_men": ["man leather jacket", "man wearing jacket"],
    "jackets_women": ["woman jacket", "woman blazer"],
    "socks": ["socks", "colorful socks"],
    "swimwear": ["one piece swimsuit", "swimsuit"],
    "belts": ["leather belt", "belt fashion"],
    "kids": ["kids fashion", "children clothes"],
}
PER_POOL = 12
SAMPLES = 1


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
                seen[pid] = {"id": pid, "url": sized(src), "photographer": photo.get("photographer", "")}
            time.sleep(1)
        kept: list[dict] = []
        for info in seen.values():
            if len(kept) >= PER_POOL:
                break
            if alive(info["url"]):
                kept.append(info)
                name = str(info["photographer"]).encode("ascii", "replace").decode()
                print(f"   OK {info['id']} {name[:40]}", flush=True)
            time.sleep(0.3)
        pools[pool] = kept
        for i, info in enumerate(kept[:SAMPLES]):
            dest = TMP / f"batch2_{pool}_{i}.jpg"
            try:
                import urllib.request

                req = urllib.request.Request(info["url"], headers={"User-Agent": "HMStyleLab/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as fh:
                    fh.write(resp.read())
                print(f"   sample -> {dest}")
            except Exception as exc:
                print(f"   sample FAIL: {type(exc).__name__}")
    out = TMP / "pexels_pools2.json"
    out.write_text(json.dumps(pools, indent=1), encoding="utf-8")
    total = sum(len(v) for v in pools.values())
    print(f"WROTE {out} total={total}")
    for pool, items in pools.items():
        print(f"  {pool}: {len(items)}")


if __name__ == "__main__":
    sys.exit(main())
