#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把必应官方每日壁纸归档补齐到 bing-wallpaper.md（只增不改，已有日期一律保留原记录）。

数据来源：cn.bing.com（zh-CN）每日壁纸归档
  https://api.github.com/repos/flow2000/bing-wallpaper-api/contents/data/zh-CN_all.json
  （该归档与 cn.bing.com/th?id=OHR.* 一一对应；可回溯到 2016-03-05，
    这也是必应中文站每日一图公开可查的最早日期）

用法：
  python tools/backfill_from_archive.py                    # 联网拉取归档后补齐
  python tools/backfill_from_archive.py --archive x.json   # 用本地已下载的归档文件
  python tools/backfill_from_archive.py --dry-run          # 只统计不写文件
"""

import argparse
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate  # noqa: E402

ARCHIVE_URL = ("https://api.github.com/repos/flow2000/bing-wallpaper-api/"
               "contents/data/zh-CN_all.json")
CACHE = os.path.join(generate.ROOT, "tools", ".bing-archive-cache.json")


def fetch(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github.raw",
        "User-Agent": "bingimg-backfill",
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def load_archive(path=None, url=ARCHIVE_URL):
    if path:
        raw = open(path, "rb").read()
    else:
        print("下载归档数据 ...")
        raw = fetch(url)
        with open(CACHE, "wb") as f:
            f.write(raw)
    data = json.loads(raw.decode("utf-8"))
    return data["data"] if isinstance(data, dict) else data


def oh_id(url):
    """从图片地址中取出形如 OHR.Xxx_ZH-CN123 的 Bing 图片 ID。"""
    m = re.search(r"[?&]id=([A-Za-z0-9._\-]+?)(?:_\d+x\d+)?\.(?:jpe?g|png)", url)
    if not m:
        # cdn.bimg.cc/bing/2018/OHR.xxx_1920x1080.jpg 这类不带 ?id= 的地址
        m = re.search(r"(OHR\.[A-Za-z0-9._\-]+?)(?:_\d+x\d+)?\.(?:jpe?g|png)", url)
    if not m:
        raise ValueError("无法解析图片 ID: %s" % url)
    return m.group(1)


def clean(desc):
    """避免破坏 Markdown 表格 / 链接语法。"""
    return desc.replace("|", "｜").replace("]", "］").strip()


def normalize(item):
    date = item["datetime"][:10]
    desc = clean(item.get("copyright") or item.get("title") or "")
    try:
        url = "https://cn.bing.com/th?id=%s_UHD.jpg" % oh_id(item["url"])
    except ValueError:
        # 极少数历史条目没有 OHR 前缀，cn.bing.com 上已不存在，保留归档原图地址
        url = item["url"].replace("http://", "https://")
    return date, desc, url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", help="本地归档 JSON 路径")
    ap.add_argument("--url", default=ARCHIVE_URL)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-generate", action="store_true", help="只更新 bing-wallpaper.md，不重建页面")
    args = ap.parse_args()

    entries = generate.read_entries()
    have = {e[0] for e in entries}
    before = len(entries)

    archive = load_archive(args.archive, args.url)
    added = []
    for item in archive:
        date, desc, url = normalize(item)
        if date in have or not desc:
            continue
        have.add(date)
        added.append((date, desc, url))

    added.sort(reverse=True)
    print("已有 %d 条，归档 %d 条，新增 %d 条" % (before, len(archive), len(added)))
    if added:
        print("新增区间：%s ~ %s" % (added[-1][0], added[0][0]))
    if args.dry_run:
        return 0

    merged = sorted(entries + added, key=lambda e: e[0], reverse=True)
    with open(generate.BING_MD, "w", encoding="utf-8", newline="") as f:
        f.write(generate.to_markdown(merged))

    if not args.no_generate:
        n, m = generate.write_all()
        print("已重建：%d 条记录 / %d 个月份" % (n, m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
