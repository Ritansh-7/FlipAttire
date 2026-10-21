"""Fetch the missing shoes pool + prune noisy titles, keeping 100+ garment photos."""
from __future__ import annotations

import json
import re
import sys
import time

sys.path.insert(0, r"D:\gt\scripts")
from fetch_garment_photos import TMP, alive, log, members, thumbs

DROP = re.compile(
    r"parade|festival|concert|market|wedding|funeral|church|mosque|museum|protest|"
    r"rally|marathon|conference|ceremony|graduation|carnival|procession|war\b|"
    r"army|military|soldier|football|soccer|baseball|ambigram|drawing|\bpng\b|logo",
    re.IGNORECASE,
)


def main() -> None:
    pools = json.loads((TMP / "garment_pools.json").read_text(encoding="utf-8"))
    log("== shoes <- Category:Shoes")
    kept: list[dict] = []
    try:
        for info in thumbs(members("Category:Shoes", 90)):
            if len(kept) >= 20:
                break
            if alive(info["url"]):
                kept.append(info)
                log(f"   OK {info['w']}x{info['h']} {info['title'][:60]}")
            time.sleep(0.3)
    except Exception as exc:
        log(f"   shoes fetch failed: {exc}")
    pools["shoes"] = kept
    for i, info in enumerate(kept[:2]):
        dest = TMP / f"shoes_{i}.jpg"
        try:
            import urllib.request

            req = urllib.request.Request(info["url"], headers={"User-Agent": "HMStyleLab/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as fh:
                fh.write(resp.read())
            log(f"   sample -> {dest}")
        except Exception as exc:
            log(f"   sample FAIL: {exc}")

    for pool, items in pools.items():
        before = len(items)
        pools[pool] = [x for x in items if not DROP.search(x["title"])]
        log(f"  {pool}: {before} -> {len(pools[pool])} after prune")
    out = TMP / "garment_pools.json"
    out.write_text(json.dumps(pools, indent=1), encoding="utf-8")
    log(f"WROTE {out} total={sum(len(v) for v in pools.values())}")


if __name__ == "__main__":
    sys.exit(main())
