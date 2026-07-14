#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
zimaflow installer

用法：
  scripts/install.sh --target <dir> [--bin-dir <dir>] [--force]
  scripts/install.sh --help

选项：
  --target <dir>   安装 skills/、rules/、references/ 到目标目录。
  --bin-dir <dir>  可选：安装 bin/zimaflow 到指定目录。
  --force          覆盖目标目录中已存在的同名文件。
  --help           显示帮助。

说明：
  - 不使用网络。
  - 不写入 shell profile。
  - 不修改 Codex、Claude Code、Cursor 或 WorkBuddy 配置。
  - 不初始化 OpenSpec。
  - 不创建项目注册表或项目文档目录。
EOF
}

die() {
  printf '错误：%s\n' "$1" >&2
  exit 1
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_dir=""
bin_dir=""
force="no"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      [ "$#" -ge 2 ] || die "--target 需要目录参数"
      target_dir="$2"
      shift 2
      ;;
    --bin-dir)
      [ "$#" -ge 2 ] || die "--bin-dir 需要目录参数"
      bin_dir="$2"
      shift 2
      ;;
    --force)
      force="yes"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "未知参数：$1"
      ;;
  esac
done

[ -n "$target_dir" ] || die "必须提供 --target <dir>"

copy_tree() {
  local name="$1"
  local src="$repo_root/$name"
  local dst="$target_dir/$name"

  [ -d "$src" ] || die "源目录不存在：$src"
  mkdir -p "$dst"

  while IFS= read -r file; do
    local rel="${file#$src/}"
    local out="$dst/$rel"
    if [ -e "$out" ] && [ "$force" != "yes" ]; then
      die "目标文件已存在：$out（使用 --force 覆盖）"
    fi
  done < <(find "$src" -type f | sort)

  while IFS= read -r file; do
    local rel="${file#$src/}"
    local out="$dst/$rel"
    mkdir -p "$(dirname "$out")"
    cp "$file" "$out"
  done < <(find "$src" -type f | sort)
}

mkdir -p "$target_dir"
copy_tree "skills"
copy_tree "rules"
copy_tree "references"

if [ -n "$bin_dir" ]; then
  [ -f "$repo_root/bin/zimaflow" ] || die "bin/zimaflow 不存在"
  mkdir -p "$bin_dir"
  if [ -e "$bin_dir/zimaflow" ] && [ "$force" != "yes" ]; then
    die "目标文件已存在：$bin_dir/zimaflow（使用 --force 覆盖）"
  fi
  cp "$repo_root/bin/zimaflow" "$bin_dir/zimaflow"
  chmod +x "$bin_dir/zimaflow"
fi

cat <<EOF
zimaflow 基础内容已安装。

安装位置：
  skills/rules/references: $target_dir
EOF

if [ -n "$bin_dir" ]; then
  cat <<EOF
  zimaflow CLI: $bin_dir/zimaflow
EOF
fi

cat <<'EOF'

下一步：
  1. 让你的 agent 读取目标目录下的 skills/。
  2. 将 rules/ 和 references/ 保持在 skills/ 旁边。
  3. 如安装了 CLI，可运行：zimaflow close

注意：v0.1 基础安装脚本不负责 OpenSpec 初始化、项目注册表或项目文档目录。
EOF
