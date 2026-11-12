#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 bing.ee123.net 回填 2010-01-01 ~ 2016-03-04 的必应壁纸。

该站按日期返回 {imgurl, imgtitle, imgcopyright, date}，
图片是镜像站的 1080P 静态地址（/img/cn/fhd/YYYY/MM/DD.jpg）。
早期日期没有数据时它会返回当天 cn.bing.com 的地址作为兜底，需按域名过滤。
"""

import argparse
import concurrent.futures as futures
import datetime
import html
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate  # noqa: E402

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ee123-cache.json")
API = "https://bing.ee123.net/img/?date=%s&size=1920x1080&imgtype=jpg&type=json"
START = datetime.date(2010, 1, 1)
END = datetime.date(2016, 3, 4)


def fetch(day):
    url = API % day.strftime("%Y%m%d")
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
    return None


def probe(url):
    try:
        out = subprocess.run(["curl", "-s", "-o", "/dev/null", "-r", "0-0", "-m", "20",
                              "-w", "%{http_code}", url], capture_output=True, timeout=30)
        return int(out.stdout.decode().strip() or 0)
    except Exception:
        return 0


def clean(s):
    return html.unescape(s or "").replace("\u00a0", " ").strip()


def build(day, data):
    if not data:
        return None, "请求失败"
    img = data.get("imgurl", "")
    if "/img/cn/fhd/" not in img:
        return None, "无存档"
    title = clean(data.get("imgtitle"))
    copy = clean(data.get("imgcopyright"))
    if "©" in copy and not copy.startswith("©"):
        copy = "© " + copy.replace("©", "").strip()
    desc = ("%s (%s)" % (title, copy)) if copy else title
    # 方括号 / 竖线会破坏 markdown 链接与表格解析
    desc = desc.replace("[", "［").replace("]", "］").replace("|", "｜")
    return (day.isoformat(), desc, img), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--write", action="store_true", help="校验通过后写回 bing-wallpaper.md")
    args = ap.parse_args()

    days = [START + datetime.timedelta(days=i) for i in range((END - START).days + 1)]
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    todo = [d for d in days if d.isoformat() not in cache]
    print("共 %d 天，待抓取 %d（缓存 %d）" % (len(days), len(todo), len(days) - len(todo)))

    def work(day):
        return day.isoformat(), fetch(day)

    with futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, (k, v) in enumerate(ex.map(work, todo), 1):
            cache[k] = v
            if i % 100 == 0:
                print("  ... %d/%d" % (i, len(todo)))
                json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)

    rows, missing = [], []
    for day in days:
        item, why = build(day, cache.get(day.isoformat()))
        if item:
            rows.append(item)
        else:
            missing.append((day.isoformat(), why))
    print("可用 %d 天，缺失 %d 天" % (len(rows), len(missing)))
    for m in missing[:20]:
        print("  缺:", m[0], m[1])

    print("校验图片可访问性 ...")
    bad = []

    def check(item):
        return item, probe(item[2])

    with futures.ThreadPoolExecutor(max_workers=24) as ex:
        for i, (item, code) in enumerate(ex.map(check, rows), 1):
            if code != 206:
                bad.append((item[0], code, item[2]))
            if i % 300 == 0:
                print("  ... %d/%d（异常 %d）" % (i, len(rows), len(bad)))
    print("图片异常 %d 条" % len(bad))
    for b in bad[:20]:
        print("  异常:", b[0], b[1], b[2])

    report = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ee123-report.json")
    json.dump({"rows": len(rows), "missing": missing, "bad": bad},
              open(report, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if not args.write:
        print("未写回（加 --write 生效）")
        return

    if bad:
        print("存在异常图片，停止写回")
        return

    old = generate.read_entries()
    old_dates = {e[0] for e in old}
    add = [r for r in rows if r[0] not in old_dates]
    merged = sorted(list(old) + add, key=lambda e: e[0], reverse=True)
    with open(generate.BING_MD, "w", encoding="utf-8", newline="") as f:
        f.write(generate.to_markdown(merged))
    print("新增 %d 条，总条目 %d，最早 %s" % (len(add), len(merged), merged[-1][0]))


if __name__ == "__main__":
    main()
