#!/usr/bin/env bash
# 针对 todo.sh 的聚焦测试，产出真实的 verify 证据。
# 覆盖：add / list / done 正常路径 + 未知 id 错误路径 + 可配置文件路径。
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
todo="$here/todo.sh"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
custom="$work/custom-todos.txt"

pass=0
exist=0
check() {
  local desc="$1" haystack="$2" needle="$3"
  if printf '%s' "$haystack" | grep -q "$needle"; then
    echo "  PASS: $desc"
    pass=$((pass + 1))
  else
    echo "  FAIL: $desc" >&2
    echo "  ---- 实际输出 ----" >&2
    printf '%s\n' "$haystack" >&2
    exit 1
  fi
}

echo "verify: todo.sh（可配置文件路径）"

# 1. 可配置路径：--file 指向自定义位置，add 后文件在该位置生成
bash "$todo" --file "$custom" add "Write README" >/dev/null
[ -f "$custom" ] || { echo "  FAIL: --file 未在指定位置创建文件" >&2; exit 1; }
exist=$((exist + 1))
echo "  PASS: --file 在指定位置创建持久化文件"

# 2. list 显示新增任务为待办
out="$(bash "$todo" --file "$custom" list)"
check "add 后 list 显示待办任务" "$out" "\[ \] #1 Write README"

# 3. done 标记完成
bash "$todo" --file "$custom" add "Ship v0.2" >/dev/null
bash "$todo" --file "$custom" done 1 >/dev/null
out="$(bash "$todo" --file "$custom" list)"
check "done 后任务出现在已完成区" "$out" "\[x\] #1 Write README"
check "未完成任务仍在待办区" "$out" "\[ \] #2 Ship v0.2"

# 4. 未知 id 报清晰错误且退出码非 0
if err="$(bash "$todo" --file "$custom" done 99 2>&1)"; then
  echo "  FAIL: done 99 应当失败但成功了" >&2
  exit 1
fi
check "未知 id 报清晰用户错误" "$err" "找不到任务 #99"

# 5. TODO_FILE 环境变量同样生效
envfile="$work/env-todos.txt"
TODO_FILE="$envfile" bash "$todo" add "via env" >/dev/null
[ -f "$envfile" ] || { echo "  FAIL: TODO_FILE 未生效" >&2; exit 1; }
exist=$((exist + 1))
echo "  PASS: TODO_FILE 环境变量指定文件路径生效"

total=$((pass + exist))
echo "verify passed: ${total}/${total} checks（${pass} 个 grep 断言 + ${exist} 个存在性断言）"
