#!/usr/bin/env bash
#
# 把历史提交里小号（AiChenX / ichenc@163.com）的署名改写为主账号（ichenc），
# 这样 GitHub 仓库页面的 Contributors 里就只剩一个账号。
#
# 原理：Contributors 是按默认分支里每个提交的 author 邮箱匹配账号算出来的。
#       自动提交一直用 ichenc@163.com，而这个邮箱绑定在小号上，所以 1456 次
#       自动提交全部算给了 AiChenX。改掉邮箱后重新计算即可消失。
#
# 用法：
#   bash tools/fix_contributors.sh                 # 默认克隆到 ./bingimg-rewrite
#   bash tools/fix_contributors.sh <repo-url> <dir>
#
# 脚本只做本地改写和自检，最后一步 push 需要你手动确认执行。

set -euo pipefail

OLD_EMAIL="ichenc@163.com"
NEW_NAME="ichenc"
NEW_EMAIL="101170810+ichenc@users.noreply.github.com"

REPO_URL="${1:-https://github.com/ichenc/bingimg.git}"
WORKDIR="${2:-bingimg-rewrite}"

if [ -e "$WORKDIR" ]; then
  echo "目录 $WORKDIR 已存在，请先删除或换一个目录名"; exit 1
fi

git clone "$REPO_URL" "$WORKDIR"
cd "$WORKDIR"

echo "== 改写前的署名统计 =="
git log --format='%an <%ae> | %cn <%ce>' | sort | uniq -c | sort -rn | head -10

MAILMAP="$(mktemp)"
printf '%s <%s> <%s>\n' "$NEW_NAME" "$NEW_EMAIL" "$OLD_EMAIL" > "$MAILMAP"

if command -v git-filter-repo >/dev/null 2>&1; then
  echo "== 使用 git-filter-repo 改写 =="
  git filter-repo --mailmap "$MAILMAP" --force
  git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"
else
  echo "== 未安装 git-filter-repo，退回 git filter-branch（较慢） =="
  echo "   建议先安装：pip install git-filter-repo"
  FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --env-filter "
    if [ \"\$GIT_AUTHOR_EMAIL\" = \"$OLD_EMAIL\" ]; then
      export GIT_AUTHOR_NAME=\"$NEW_NAME\"
      export GIT_AUTHOR_EMAIL=\"$NEW_EMAIL\"
    fi
    if [ \"\$GIT_COMMITTER_EMAIL\" = \"$OLD_EMAIL\" ]; then
      export GIT_COMMITTER_NAME=\"$NEW_NAME\"
      export GIT_COMMITTER_EMAIL=\"$NEW_EMAIL\"
    fi" --tag-name-filter cat -- --all
  rm -rf .git/refs/original
  git reflog expire --expire=now --all
  git gc --prune=now
fi

rm -f "$MAILMAP"

echo "== 改写后的署名统计 =="
git log --format='%an <%ae> | %cn <%ce>' | sort | uniq -c | sort -rn | head -10

echo
echo "接下来（确认上面的统计里已经没有被改坏的内容）："
echo "  1. git push --force origin main    # 或 --force-with-lease"
echo "  2. 到 Settings → Secrets 把 MY_GIT_TOKEN 换成【主账号 ichenc】的 PAT，"
echo "     并确认 .github/workflows/maven.yml 里 user.email 已是主账号邮箱；"
echo "  3. Contributors 是缓存数据，改写后通常几小时内刷新，最慢 24 小时；"
echo "     若迟迟不更新，可给 GitHub Support 提交工单，附上本次改写说明。"
