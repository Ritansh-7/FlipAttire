"""Fetch real garment product photos from Wikimedia Commons (free license, hotlink OK).

Batched + throttled to respect Commons API limits: one categorymembers call and
batched imageinfo calls per garment category.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "HMStyleLab/1.0 (local fashion demo; contact: admin@localhost)"}
API = "https://commons.wikimedia.org/w/api.php"
TMP = Path(r"D:\gt\tmp\garment")
WANT = {
    "tops": "Category:T-shirts",
    "bottoms": "Category:Jeans",
    "dresses": "Category:Dresses",
    "jackets": "Category:Jackets",
    "shoes": "Category:Sneakers",
    "accessories": "Category:Handbags",
}
PER_POOL = 20
SAMPLES = 2


def log(msg: str) -> None:
    print(msg.encode("ascii", "replace").decode(), flush=True)


def api(params: dict, tries: int = 4) -> dict:
    params = {"action": "query", "format": "json", **params}
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < tries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def members(category: str, limit: int = 90) -> list[str]:
    titles: list[str] = []
    cont: str | None = None
    while len(titles) < limit:
        params = {
            "generator": "categorymembers",
            "gcmtitle": category,
            "gcmtype": "file",
            "gcmlimit": 50,
        }
        if cont:
            params["gcmcontinue"] = cont
        data = api(params)
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            break
        titles.extend(p["title"] for p in pages.values())
        cont = (data.get("continue") or {}).get("gcmcontinue")
        time.sleep(1)
        if not cont:
            break
    return titles[:limit]


def thumbs(titles: list[str]) -> list[dict]:
    out: list[dict] = []
    for i in range(0, len(titles), 40):
        chunk = titles[i : i + 40]
        data = api(
            {
                "titles": "|".join(chunk),
                "prop": "imageinfo",
                "iiprop": "url|size|mediatype",
                "iiurlwidth": 600,
            }
        )
        for page in data.get("query", {}).get("pages", {}).values():
            for info in page.get("imageinfo", []):
                if info.get("mediatype") != "BITMAP":
                    continue
                url = (info.get("thumburl") or info.get("url") or "").split("?")[0]
                if not url or info.get("width", 0) < 500:
                    continue
                out.append({"title": page.get("title", ""), "url": url, "w": info.get("width", 0), "h": info.get("height", 0)})
        time.sleep(1)
    return out


def alive(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    pools: dict[str, list[dict]] = {}
    for pool, category in WANT.items():
        log(f"== {pool} <- {category}")
        kept: list[dict] = []
        try:
            candidates = thumbs(members(category))
        except Exception as exc:
            log(f"   category fetch failed: {exc}")
            pools[pool] = []
            continue
        for info in candidates:
            if len(kept) >= PER_POOL:
                break
            if alive(info["url"]):
                kept.append(info)
                log(f"   OK {info['w']}x{info['h']} {info['title'][:60]}")
            time.sleep(0.3)
        pools[pool] = kept
        for i, info in enumerate(kept[:SAMPLES]):
            dest = TMP / f"{pool}_{i}.jpg"
            try:
                req = urllib.request.Request(info["url"], headers=UA)
                with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as fh:
                    fh.write(resp.read())
                log(f"   sample -> {dest}")
            except Exception as exc:
                log(f"   sample FAIL: {exc}")
    out = TMP / "garment_pools.json"
    out.write_text(json.dumps(pools, indent=1), encoding="utf-8")
    total = sum(len(v) for v in pools.values())
    log(f"WROTE {out} total={total}")
    for pool, items in pools.items():
        log(f"  {pool}: {len(items)}")


if __name__ == "__main__":
    sys.exit(main())
