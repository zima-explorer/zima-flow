#!/usr/bin/env bash
# 针对 todo.sh 的聚焦测试，产出真实的 verify 证据。
# 覆盖本轮增量：list --status pending|done|all 的正向、负向、默认回归、异常路径与组合场景。
#
# 设计说明：每个筛选断言都配一条「不含另一类」的负向条件。
# 只断言「目标项存在」时，即使 --status 被完全忽略也会通过——那是假绿灯。
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
todo="$here/todo.sh"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

pass=0
assert() {
  local desc="$1" ok="$2" detail="${3:-}"
  if [ "$ok" = "yes" ]; then
    echo "  PASS: $desc"
    pass=$((pass + 1))
  else
    echo "  FAIL: $desc" >&2
    if [ -n "$detail" ]; then
      echo "  ---- 实际输出 ----" >&2
      printf '%s\n' "$detail" >&2
    fi
    exit 1
  fi
}

has() { printf '%s' "$1" | grep -q "$2"; }

echo "verify: todo.sh（list 状态筛选）"

# 准备数据：#1 已完成，#2 未完成。
main="$work/main-todos.txt"
bash "$todo" --file "$main" add "Write README" >/dev/null
bash "$todo" --file "$main" add "Ship v0.2" >/dev/null
bash "$todo" --file "$main" done 1 >/dev/null

# 1. list --status pending 显示未完成任务（正向 · 契约测试）
out="$(bash "$todo" --file "$main" list --status pending)"
ok="no"; has "$out" '\[ \] #2 Ship v0.2' && ok="yes"
assert "list --status pending 显示未完成任务" "$ok" "$out"

# 2. list --status pending 不包含已完成任务（负向 · 防假绿灯）
ok="yes"; has "$out" '\[x\] #1' && ok="no"
assert "list --status pending 不包含已完成任务" "$ok" "$out"

# 3. list --status done 显示已完成且不包含未完成（正向 + 负向）
out="$(bash "$todo" --file "$main" list --status done)"
ok="no"
if has "$out" '\[x\] #1 Write README' && ! has "$out" '\[ \] #2'; then ok="yes"; fi
assert "list --status done 显示已完成且不包含未完成" "$ok" "$out"

# 4. 不传 --status 的输出与 --status all 一致（兼容性检查 · 默认行为不回归）
# 这条用例是因为验证证据矩阵把「兼容性检查」与「契约测试」并列为该变更类型的期望证据才单独立的。
default_out="$(bash "$todo" --file "$main" list)"
all_out="$(bash "$todo" --file "$main" list --status all)"
ok="no"; [ "$default_out" = "$all_out" ] && ok="yes"
assert "不传 --status 的输出与 --status all 一致（默认行为不回归）" "$ok" "$default_out"

# 5. --status bogus 报清晰错误且退出码非 0（异常路径 · 契约测试）
ok="no"
if err="$(bash "$todo" --file "$main" list --status bogus 2>&1)"; then
  err="（命令意外成功）"
else
  has "$err" '\-\-status 取值无效' && ok="yes"
fi
assert "--status bogus 报清晰错误且退出码非 0" "$ok" "$err"

# 6. --status 与 --file 可组合（兼容性检查 · 不破坏上一个案例交付的能力）
other="$work/other-todos.txt"
bash "$todo" --file "$other" add "Only in other file" >/dev/null
out="$(bash "$todo" --file "$other" list --status pending)"
ok="no"
if has "$out" '\[ \] #1 Only in other file' && ! has "$out" 'Ship v0.2'; then ok="yes"; fi
assert "--status 与 --file 可组合，只读取指定文件" "$ok" "$out"

echo "verify passed: ${pass}/6 checks"
