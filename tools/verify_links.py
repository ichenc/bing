#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import concurrent.futures as futures
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate  # noqa: E402

CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".link-cache.json")
MIN_BYTES = 20000
TIMEOUT = 10


def probe(url, timeout=TIMEOUT):
    """探测地址是否可用，返回 ((status, length), status_code)。"""
    try:
        out = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-r", "0-0", "-m", str(timeout),
             "-w", "%{http_code}", url],
            capture_output=True, timeout=timeout + 10)
        code = int((out.stdout or b"0").decode().strip() or 0)
    except Exception:
        return (0, 0), 0
    # 206 = Range 命中真实图片；早期用 HEAD 探测留下的缓存是 200 + Content-Length
    return (code, MIN_BYTES if code == 206 else 0), code


def ok(res):
    status, length = res
    return status == 206 or (status == 200 and length >= MIN_BYTES)


def image_id(url):
    m = re.search(r"(OHR\.[A-Za-z0-9._\-]+?)(?:_\d+x\d+|_UHD)?\.(?:jpe?g|png)", url)
    return m.group(1) if m else None


def candidates(date, url):
    out = [url]
    oid = image_id(url)
    if oid:
        year = date[:4]
        for cand in ("https://cdn.bimg.cc/bing/%s/%s_1920x1080.jpg" % (year, oid),
                     "https://cdn.bimg.cc/bing/%s/%s_UHD.jpg" % (year, oid)):
            if cand not in out:
                out.append(cand)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查，不修改文件")
    ap.add_argument("--no-generate", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="忽略缓存重新探测")
    ap.add_argument("--deep", action="store_true",
                    help="对仍失效的地址做长超时重试，并尝试相邻年份目录")
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()

    cache = {}
    if os.path.exists(CACHE_PATH) and not args.refresh:
        cache = json.load(open(CACHE_PATH, encoding="utf-8"))

    entries = generate.read_entries()
    todo = [e for e in entries if e[2] not in cache]
    print("共 %d 条，待探测 %d 条（已缓存 %d）" % (len(entries), len(todo), len(entries) - len(todo)))

    def work(e):
        res, _ = probe(e[2])
        return e[2], res

    if todo:
        with futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            for k, (url, res) in enumerate(ex.map(work, todo), 1):
                cache[url] = list(res)
                if k % 100 == 0:
                    print("  ... %d/%d" % (k, len(todo)))
                    json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))
        json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))

    dead = [e for e in entries if not ok(tuple(cache.get(e[2], [0, 0])))]
    print("失效地址 %d 条" % len(dead))

    fixed = []
    if dead and not args.check:
        def repair(e):
            # --deep：不看历史缓存，长超时重试，并额外试相邻年份目录
            if args.deep:
                oid = image_id(e[2])
                year = int(e[0][:4])
                probe_list = []
                if oid:
                    for y in (year, year - 1, year + 1):
                        probe_list.append("https://cdn.bimg.cc/bing/%d/%s_1920x1080.jpg" % (y, oid))
                    probe_list.append("https://cdn.bimg.cc/bing/%d/%s_UHD.jpg" % (year, oid))
                for cand in probe_list:
                    for _ in range(2):
                        got, _code = probe(cand, timeout=25)
                        if ok(got):
                            cache[cand] = list(got)
                            return (e[0], e[1], cand)
                return None
            for cand in candidates(e[0], e[2])[1:]:
                res = tuple(cache[cand]) if cand in cache else None
                if res is None:
                    got, _ = probe(cand)
                    cache[cand] = list(got)
                    res = got
                if ok(res):
                    return (e[0], e[1], cand)
            return None

        with futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            for k, item in enumerate(ex.map(repair, dead), 1):
                if item:
                    fixed.append(item)
                if k % 50 == 0:
                    print("  ... 修复 %d/%d（成功 %d）" % (k, len(dead), len(fixed)))
                    json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))
        json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))
        print("可替换 %d 条，仍无可用地址 %d 条" % (len(fixed), len(dead) - len(fixed)))

    if args.check:
        for e in dead[:10]:
            print("  失效:", e[0], e[2][:100])
        return 0

    if fixed:
        mapping = {d: u for d, _, u in fixed}
        merged = [(d, desc, mapping.get(d, u)) for d, desc, u in entries]
        with open(generate.BING_MD, "w", encoding="utf-8", newline="") as f:
            f.write(generate.to_markdown(merged))
        print("已更新 %d 条图片地址" % len(fixed))

    if fixed and not args.no_generate:
        n, m = generate.write_all()
        print("已重建：%d 条记录 / %d 个月份" % (n, m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
