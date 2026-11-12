#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import re
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BING_MD = os.path.join(ROOT, "bing-wallpaper.md")
README = os.path.join(ROOT, "README.md")
PICTURE_DIR = os.path.join(ROOT, "picture")
DOCS_DIR = os.path.join(ROOT, "docs")
TEMPLATE = os.path.join(DOCS_DIR, "bing-template.html")

MD_HEADER = "## Bing Wallpaper"

SIDEBAR_MENU = ('<a href="{url}" onclick="w3_close()" class="w3-bar-item w3-button {color} w3-large">'
                '{title}</a>')
MONTH_TAG = ('<a class="w3-tag w3-button w3-hover-green {color} w3-margin-bottom" href="{url}">'
             '{title}</a>')
IMG_CARD = ('<div class="w3-third " style="position: relative;">\n'
            '  <img class="smallImg" src="{small}"  style="width:95%;" />'
            ' <img class="bigImg" src="{big}" style="width:95%" '
            'onload="imgloading(this)">\n'
            ' <p>{date} <a href="{url}" target="_blank">Download 4k</a> </p>\n'
            '</div>')

THUMB_PARAMS = "pid=hp&w=384&h=216&rs=1&c=4"


def read_entries(path=BING_MD):
    """读取 bing-wallpaper.md，返回 [(date, desc, url)]，保持文件中的顺序（新 -> 旧）。"""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    entries = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        date = s[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            continue
        desc = s[14:s.index("]")]
        url = s[s.rindex("(") + 1:s.rindex(")")]
        entries.append((date, desc, url))
    return entries


def to_markdown(entries):
    """bing-wallpaper.md 的完整内容。"""
    buf = [MD_HEADER, "\n"]
    for date, desc, url in entries:
        buf.append("%s | [%s](%s) \n\n" % (date, desc, url))
    return "".join(buf)


def with_params(url, params):
    """拼查询参数：地址本身已带 ? 时用 &，否则用 ?（cdn.bimg.cc 这类静态路径必须用 ?）。"""
    return url + ("&" if "?" in url else "?") + params


def _large_block(item):
    _, desc, url = item
    return "![](%s)Today: [%s](%s)" % (with_params(url, "w=1000"), desc, url)


def _table(items):
    out = ["|      |      |      |\n", "| :----: | :----: | :----: |\n"]
    i = 1
    for date, desc, url in items:
        out.append("|![](%s)%s [download 4k](%s)" % (with_params(url, THUMB_PARAMS), date, url))
        if i % 3 == 0:
            out.append("|\n")
        i += 1
    if i % 3 != 1:
        out.append("|")
    return "".join(out)


def month_readme(month, items):
    parts = ["## Bing Wallpaper (%s)\n" % month, _large_block(items[0]), "\n", _table(items)]
    return "".join(parts)


def archive_table(entries, cn_label=True):
    """按年份分行的归档表格；替代原来“每 8 个链接硬换行 + 结尾悬空 |”的写法。"""
    months = []
    for date, _, _ in entries:
        m = date[:7]
        if m not in months:
            months.append(m)
    by_year = OrderedDict()
    for m in months:
        by_year.setdefault(m[:4], []).append(m)

    out = ["| 年份 | 归档月份 |\n", "| :---: | :--- |\n"]
    for year in sorted(by_year, reverse=True):
        cells = []
        for m in sorted(by_year[year]):
            label = "%s年%s月" % (m[:4], m[5:7]) if cn_label else m
            cells.append("[%s](/picture/%s/)" % (label, m))
        out.append("| %s | %s |\n" % (year, " · ".join(cells)))
    return "".join(out)


def index_readme(entries, legacy=False):
    head = ["## Bing Wallpaper\n", _large_block(entries[0]), "\n", _table(entries[:30]), "\n",
            "### 历史归档：\n"]
    if legacy:
        months = []
        for date, _, _ in entries:
            m = date[:7]
            if m not in months:
                months.append(m)
        buf = []
        i = 0
        for m in months:
            buf.append("[%s](/picture/%s/) | " % (m, m))
            i += 1
            if i % 8 == 0:
                buf.append("\n")
        head.append("".join(buf))
        return "".join(head)
    head.append("\n")
    head.append(archive_table(entries))
    return "".join(head)


def month_map(entries):
    mm = OrderedDict()
    for item in entries:
        mm.setdefault(item[0][:7], []).append(item)
    return mm


def html_page(entries, mm, month=None):
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    head_item = entries[0] if month is None else mm[month][0]
    html = html.replace("${head_img_small}", with_params(head_item[2], "pid=hp&w=100"))
    html = html.replace("${head_img_big}", with_params(head_item[2], "pid=hp&w=2000"))
    html = html.replace("${head_img_desc}", head_item[1])
    html = html.replace("${head_title}", "Bing Wallpaper" if month is None else "Bing Wallpaper(%s)" % month)

    sidebar = []
    for m in mm:
        color = "w3-green" if m == month else "w3-hover-green"
        sidebar.append(SIDEBAR_MENU.format(url=m + ".html", color=color, title=m))
    html = html.replace("${sidabar}", "".join(sidebar))

    cards = entries[:30] if month is None else mm[month]
    html = html.replace("${img_card_list}",
                        "".join(IMG_CARD.format(url=u, date=d,
                                                small=with_params(u, "pid=hp&w=50"),
                                                big=with_params(u, THUMB_PARAMS))
                                for d, _, u in cards))

    tags = []
    for m in mm:
        color = "w3-green" if m == month else "w3-light-grey"
        tags.append(MONTH_TAG.format(url=m + ".html", color=color, title=m) + " ")
    html = html.replace("${month_history}", "".join(tags))
    return html


def write_all(legacy_index=False):
    entries = read_entries()
    mm = month_map(entries)

    with open(BING_MD, "w", encoding="utf-8", newline="") as f:
        f.write(to_markdown(entries))
    with open(README, "w", encoding="utf-8", newline="") as f:
        f.write(index_readme(entries, legacy=legacy_index))

    for m in mm:
        d = os.path.join(PICTURE_DIR, m)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "README.md"), "w", encoding="utf-8", newline="") as f:
            f.write(month_readme(m, mm[m]))
        with open(os.path.join(DOCS_DIR, m + ".html"), "w", encoding="utf-8", newline="") as f:
            f.write(html_page(entries, mm, m))

    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8", newline="") as f:
        f.write(html_page(entries, mm, None))
    return len(entries), len(mm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy-index", action="store_true",
                    help="用旧版归档列表格式（8 个一行、结尾悬空 |）生成 README.md，仅用于回归校验")
    args = ap.parse_args()
    n, m = write_all(legacy_index=args.legacy_index)
    print("entries=%d months=%d" % (n, m))


if __name__ == "__main__":
    sys.exit(main())
