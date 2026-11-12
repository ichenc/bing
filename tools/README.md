# tools 使用说明

这里的脚本用于**补齐历史数据**、**修复死链**和**重建静态页面**，只依赖 Python 3 标准库（外加 `curl`），
没有 JDK / Maven 也能跑。日常更新仍由 `.github/workflows/maven.yml` 里的 Java 程序负责，两边输出格式保持一致。

## 1. generate.py —— 重建全部静态产物

```bash
python tools/generate.py            # 按 bing-wallpaper.md 重建 README.md、picture/*、docs/*
python tools/generate.py --legacy-index   # 用旧版归档列表格式，仅用于回归对比
```

生成内容与 Java 版（`src/main/java`）逐字节一致，改动 Java 之后建议用它验证一次。

## 2. backfill_from_archive.py —— 补齐历史记录

```bash
python tools/backfill_from_archive.py                  # 联网拉取归档并补齐
python tools/backfill_from_archive.py --archive x.json  # 用本地归档文件
python tools/backfill_from_archive.py --dry-run         # 只看统计
```

数据来源：`flow2000/bing-wallpaper-api` 的 `data/zh-CN_all.json`（cn.bing.com 每日一图的归档，
与 `cn.bing.com/th?id=OHR.*` 一一对应）。已有日期一律保留原记录，只补齐缺失的日期。

> 必应中文站（cn.bing.com）能公开回溯到的最早一天是 **2016-03-05**，
> 在此之前没有可用的官方每日一图记录；国际版 2009 年的图片 Bing 早已下线，链接全部失效。

## 3. verify_links.py —— 检查 / 修复死链

```bash
python tools/verify_links.py --check     # 只统计失效数量
python tools/verify_links.py             # 失效地址换成官方 CDN 并重建页面
```

必应只在 `cn.bing.com` 上长期保留最近几年的图，更早的图仍可从官方 CDN 取：

1. `cn.bing.com/th?id={id}_UHD.jpg`（原始 4K 地址）
2. `cdn.bimg.cc/bing/{年}/{id}_UHD.jpg`（官方 CDN，4K）
3. `cdn.bimg.cc/bing/{年}/{id}_1920x1080.jpg`（官方 CDN，1080P）

注意 CDN 是**静态路径**，追加参数必须用 `?` 而不是 `&`，否则 404 —— 生成器里的
`with_params()` / `Images.withParams()` 就是处理这件事的。

## 4. fix_contributors.sh —— 把小号从 Contributors 里去掉

```bash
bash tools/fix_contributors.sh
```

详见脚本头部注释。要点：

1. **根因**：`maven.yml` 里 `git config user.email` 用的是 `ichenc@163.com`，该邮箱绑定在小号
   `AiChenX` 上，于是每天一次、累计 1400+ 次自动提交全部记到了小号名下。
2. **止血**：把 `maven.yml` 的邮箱改成主账号的 `101170810+ichenc@users.noreply.github.com`，
   并把 `MY_GIT_TOKEN` 换成主账号的 PAT（小号的 token 推送同样算到小号头上）。
3. **清理**：用脚本把历史提交的 author / committer 邮箱改写成主账号邮箱，`git push --force` 后
   Contributors 会重新计算（缓存通常几小时内刷新，最慢 24 小时）。
