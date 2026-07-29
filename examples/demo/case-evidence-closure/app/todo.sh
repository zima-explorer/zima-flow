#!/usr/bin/env bash
# 一个很小的本地 todo CLI，用于证据收口案例演示。
# 无外部依赖（纯 bash），持久化为简单的行式文本：id|done|title
#
# 用法：
#   todo.sh add "写 README"
#   todo.sh list
#   todo.sh list --status pending
#   todo.sh done 1
#
# 文件位置优先级：
#   1. --file <path>（上一个案例交付的能力）
#   2. $TODO_FILE
#   3. 当前目录下的 .todo.txt（默认）
#
# 状态筛选：
#   --status pending|done|all（本轮案例新增的能力；不传等价于 all）
set -euo pipefail

todo_file=".todo.txt"
if [ -n "${TODO_FILE:-}" ]; then
  todo_file="$TODO_FILE"
fi

# 状态筛选默认值：不传 --status 等价于 --status all（默认行为不回归）。
todo_status="all"

# 解析可选的 --file / --status，放在子命令之前或之后都可。
args=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --file)
      [ -n "${2:-}" ] || { echo "错误：--file 缺少值" >&2; exit 2; }
      todo_file="$2"; shift 2 ;;
    --status)
      [ -n "${2:-}" ] || { echo "错误：--status 缺少值" >&2; exit 2; }
      case "$2" in
        pending|done|all) todo_status="$2" ;;
        *)
          echo "错误：--status 取值无效：$2（可选 pending|done|all）" >&2
          exit 2 ;;
      esac
      shift 2 ;;
    *)
      args+=("$1"); shift ;;
  esac
done
# Bash 3.2（macOS 默认）下，空数组配合 set -u 展开 ${args[@]} 会报 unbound；先判空。
if [ "${#args[@]}" -gt 0 ]; then
  set -- "${args[@]}"
else
  set --
fi

ensure_file() {
  [ -f "$todo_file" ] || : > "$todo_file"
}

next_id() {
  ensure_file
  local max=0 id
  while IFS='|' read -r id _ _; do
    [ -n "$id" ] || continue
    [ "$id" -gt "$max" ] && max="$id"
  done < "$todo_file"
  echo $((max + 1))
}

cmd_add() {
  local title="${1:-}"
  [ -n "$title" ] || { echo "错误：add 需要标题" >&2; exit 2; }
  ensure_file
  local id
  id="$(next_id)"
  printf '%s|0|%s\n' "$id" "$title" >> "$todo_file"
  echo "已添加 #${id}：${title}"
}

cmd_list() {
  ensure_file
  local id done title
  # 沿用已有的 done 位分区判定逻辑，只在外层加一个是否渲染该分区的开关。
  if [ "$todo_status" = "pending" ] || [ "$todo_status" = "all" ]; then
    echo "待办："
    while IFS='|' read -r id done title; do
      [ -n "$id" ] || continue
      [ "$done" = "0" ] && printf '  [ ] #%s %s\n' "$id" "$title"
    done < "$todo_file"
  fi
  if [ "$todo_status" = "done" ] || [ "$todo_status" = "all" ]; then
    echo "已完成："
    while IFS='|' read -r id done title; do
      [ -n "$id" ] || continue
      if [ "$done" = "1" ]; then printf '  [x] #%s %s\n' "$id" "$title"; fi
    done < "$todo_file"
  fi
  return 0
}

cmd_done() {
  local target="${1:-}"
  [ -n "$target" ] || { echo "错误：done 需要任务 id" >&2; exit 2; }
  ensure_file
  local found="no" id done title tmp
  tmp="$(mktemp)"
  while IFS='|' read -r id done title; do
    [ -n "$id" ] || continue
    if [ "$id" = "$target" ]; then
      printf '%s|1|%s\n' "$id" "$title" >> "$tmp"
      found="yes"
    else
      printf '%s|%s|%s\n' "$id" "$done" "$title" >> "$tmp"
    fi
  done < "$todo_file"
  if [ "$found" = "no" ]; then
    rm -f "$tmp"
    echo "错误：找不到任务 #${target}" >&2
    exit 1
  fi
  mv "$tmp" "$todo_file"
  echo "已完成 #${target}"
}

case "${1:-}" in
  add)  shift; cmd_add "${1:-}" ;;
  list) cmd_list ;;
  done) shift; cmd_done "${1:-}" ;;
  *)
    echo "用法：todo.sh [--file <path>] [--status pending|done|all] {add <title>|list|done <id>}" >&2
    exit 2 ;;
esac
