#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
zimaflow installer

用法：
  scripts/install.sh --target <dir> [--bin-dir <dir>] [--adapter-dir <dir>...]
                     [--claude-code]
                     [--force]
  scripts/install.sh --help

选项：
  --target <dir>   安装 skills/、rules/、references/ 到目标目录。
  --bin-dir <dir>  可选：安装 bin/zimaflow 到指定目录。
  --adapter-dir <dir>
                   可选：在指定目录生成扁平 adapter：
                   <dir>/zimaflow-<name>/SKILL.md。可重复传入。
  --claude-code    可选：额外在 <target>/.claude/skills/zimaflow-<name>/SKILL.md 生成
                   adapter；等价于 --adapter-dir <target>/.claude/skills。
  --force          覆盖目标目录或 adapter 目录中已存在的同名文件。
  --help           显示帮助。

说明：
  - 不使用网络。
  - 不修改任何 agent 配置或 shell profile。
  - 不初始化 OpenSpec。
  - 不创建项目注册表或项目文档目录。
  - 仅在显式传入 --adapter-dir 或 --claude-code 时，生成 agent 可发现的 adapter。

关于 skill 自动发现：
  skills/ 下是扁平的 *.md 文件，Claude Code 只发现
  .claude/skills/<skill>/SKILL.md 结构（独立文件夹 + 文件名为 SKILL.md）。
  若要被 Claude Code 自动加载，请使用 --claude-code，或手动按该结构放置。
  Codex / WorkBuddy 等若能直接读取源目录或显式指定 skill 路径，优先使用源文件；
  若你的运行环境要求 <skill>/SKILL.md 一层结构才能自动发现，再使用 --adapter-dir。
  adapter 统一使用 zimaflow-<name>/SKILL.md 扁平命名，避免与用户已有 skill 撞名。
  skill 内部对 references/ 的引用使用 $ZIMAFLOW_HOME/references/，
  因此请将 ZIMAFLOW_HOME 指向 --target 目录。
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
claude_code="no"
adapter_dirs=()
installed_adapter_dirs=""

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
    --claude-code)
      claude_code="yes"
      shift
      ;;
    --adapter-dir)
      [ "$#" -ge 2 ] || die "--adapter-dir 需要目录参数"
      adapter_dirs+=("$2")
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

install_prefixed_skill_tree() {
  local dst="$1"
  local src="$repo_root/skills"

  [ -d "$src" ] || die "源目录不存在：$src"

  while IFS= read -r file; do
    local name
    name="$(basename "$file" .md)"
    local out="$dst/zimaflow-$name/SKILL.md"
    if [ -e "$out" ] && [ "$force" != "yes" ]; then
      die "目标文件已存在：$out（使用 --force 覆盖）"
    fi
  done < <(find "$src" -maxdepth 1 -type f -name '*.md' | sort)

  while IFS= read -r file; do
    local name
    name="$(basename "$file" .md)"
    local out="$dst/zimaflow-$name/SKILL.md"
    mkdir -p "$(dirname "$out")"
    cp "$file" "$out"
    rewrite_skill_name "$out" "zimaflow-$name"
  done < <(find "$src" -maxdepth 1 -type f -name '*.md' | sort)
}

rewrite_skill_name() {
  local file="$1"
  local newname="$2"
  # 自动发现 adapter 使用 zimaflow-<name> 目录名防冲突；部分宿主要求
  # frontmatter name 与目录名一致，否则校验报错。
  awk -v newname="$newname" '
    BEGIN { done = 0 }
    !done && /^name:[[:space:]]/ { print "name: " newname; done = 1; next }
    { print }
  ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
}

install_adapter_dir_once() {
  local dst="$1"
  [ -n "$dst" ] || return 0

  case "|$installed_adapter_dirs|" in
    *"|$dst|"*) return 0 ;;
  esac

  install_prefixed_skill_tree "$dst"
  installed_adapter_dirs="${installed_adapter_dirs}|$dst"
}

mkdir -p "$target_dir"
copy_tree "skills"
copy_tree "rules"
copy_tree "references"

if [ -f "$repo_root/SKILL.md" ]; then
  if [ -e "$target_dir/SKILL.md" ] && [ "$force" != "yes" ]; then
    die "目标文件已存在：$target_dir/SKILL.md（使用 --force 覆盖）"
  fi
  cp "$repo_root/SKILL.md" "$target_dir/SKILL.md"
fi

if [ "$claude_code" = "yes" ]; then
  install_adapter_dir_once "$target_dir/.claude/skills"
fi

for adapter_dir in "${adapter_dirs[@]+"${adapter_dirs[@]}"}"; do
  install_adapter_dir_once "$adapter_dir"
done

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

if [ "$claude_code" = "yes" ]; then
  cat <<EOF
  Adapter: $target_dir/.claude/skills/zimaflow-<name>/SKILL.md
EOF
fi

for adapter_dir in "${adapter_dirs[@]+"${adapter_dirs[@]}"}"; do
  cat <<EOF
  Adapter: $adapter_dir/zimaflow-<name>/SKILL.md
EOF
done

if [ -n "$bin_dir" ]; then
  cat <<EOF
  zimaflow CLI: $bin_dir/zimaflow
EOF
fi

cat <<EOF

下一步：
  1. 将 ZIMAFLOW_HOME 指向 --target 目录，使 skill 内 \$ZIMAFLOW_HOME/references/ 可解析：
       export ZIMAFLOW_HOME="$target_dir"
  2. 让你的 agent 读取目标目录下的 skills/；rules/ 和 references/ 保持在 skills/ 旁边。
  3. 如安装了 CLI，可运行：zimaflow close
EOF

if [ "$claude_code" = "yes" ]; then
  cat <<'EOF'
  - Claude Code 会自动发现 .claude/skills/ 下的 SKILL.md，无需额外配置。
EOF
fi

if [ "${adapter_dirs[*]+set}" = "set" ]; then
  cat <<'EOF'
  - 已写入显式指定的 adapter 目录；是否全局可发现取决于对应 agent 是否扫描该目录。
EOF
fi

cat <<'EOF'

注意：v0.1 基础安装脚本不负责 OpenSpec 初始化、项目注册表或项目文档目录。
EOF
