"""Third Pexels batch: expand MEN pools (~12 -> ~30 each) for variety, no repeats.

Appends to pexels_pools2.json entries (skips duplicate photo ids).
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
    "tops_men": ["man t-shirt", "man polo shirt", "man white shirt"],
    "bottoms_men": ["man trousers", "man shorts", "man chinos pants"],
    "jackets_men": ["man blazer", "man hoodie", "man coat"],
}
TARGET = 30
SAMPLES = 1


def main() -> None:
    key = load_key()
    out = TMP / "pexels_pools2.json"
    pools: dict[str, list[dict]] = json.loads(out.read_text(encoding="utf-8"))
    for pool, queries in QUERIES.items():
        print(f"== {pool} (have {len(pools.get(pool, []))})", flush=True)
        seen: dict[int, dict] = {p["id"]: p for p in pools.get(pool, [])}
        for query in queries:
            if len(seen) >= TARGET + 6:
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
        kept: list[dict] = list(pools.get(pool, []))
        have_ids = {p["id"] for p in kept}
        for info in seen.values():
            if len(kept) >= TARGET:
                break
            if info["id"] in have_ids:
                continue
            if alive(info["url"]):
                kept.append(info)
                name = str(info["photographer"]).encode("ascii", "replace").decode()
                print(f"   OK {info['id']} {name[:40]}", flush=True)
            time.sleep(0.3)
        pools[pool] = kept
    out.write_text(json.dumps(pools, indent=1), encoding="utf-8")
    total = sum(len(v) for v in pools.values())
    print(f"WROTE {out} total={total}")
    for pool in ("tops_men", "bottoms_men", "jackets_men"):
        print(f"  {pool}: {len(pools[pool])}")


if __name__ == "__main__":
    sys.exit(main())
