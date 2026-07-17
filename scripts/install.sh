#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
zimaflow installer

用法：
  scripts/install.sh --target <dir> [--bin-dir <dir>] [--claude-code] [--codex]
                     [--agent-skill-root <dir>]
                     [--claude-skill-root <dir>]
                     [--codex-skill-root <dir>]
                     [--workbuddy-skill-root <dir>]
                     [--force]
  scripts/install.sh --help

选项：
  --target <dir>   安装 skills/、rules/、references/ 到目标目录。
  --bin-dir <dir>  可选：安装 bin/zimaflow 到指定目录。
  --claude-code    可选：额外在 <target>/.claude/skills/zimaflow-<name>/SKILL.md 生成
                   符合 Claude Code 规范的 skill 目录结构，使其可被自动发现。
  --codex          可选：额外在 <target>/.agents/skills/zimaflow-<name>/SKILL.md 生成
                   符合 Codex 规范的 skill 目录结构，使其可被自动发现。
  --agent-skill-root <dir>
                   可选：安装到一个共享的全局 agent skill root，生成
                   <dir>/zimaflow-<name>/SKILL.md。
  --claude-skill-root <dir>
                   可选：安装到 Claude Code 的全局 skill root。
  --codex-skill-root <dir>
                   可选：安装到 Codex 的全局 skill root。
  --workbuddy-skill-root <dir>
                   可选：安装到 WorkBuddy 的全局 skill root（需用户确认该工具扫描此目录）。
  --force          覆盖目标目录或 skill root 中已存在的同名文件。
  --help           显示帮助。

说明：
  - 不使用网络。
  - 不修改任何 agent 配置或 shell profile。
  - 不初始化 OpenSpec。
  - 不创建项目注册表或项目文档目录。
  - 仅在显式传入对应参数时，生成 agent 可发现的 skill 结构。

关于 skill 自动发现：
  skills/ 下是扁平的 *.md 文件，Claude Code 只发现
  .claude/skills/<skill>/SKILL.md 结构（独立文件夹 + 文件名为 SKILL.md）。
  若要被 Claude Code 自动加载，请使用 --claude-code，或手动按该结构放置。
  Codex 可发现 .agents/skills/<skill>/SKILL.md 结构；若要被 Codex 自动加载，
  请使用 --codex，或手动按该结构放置。
  若用户已有全局 skill root，可用 --agent-skill-root 或对应的
  --claude-skill-root / --codex-skill-root / --workbuddy-skill-root 安装到该目录。
  自动发现结构统一使用 zimaflow-<name>/SKILL.md 扁平命名，避免与用户已有 skill 撞名。
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
codex="no"
agent_skill_root=""
claude_skill_root=""
codex_skill_root=""
workbuddy_skill_root=""
installed_global_roots=""

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
    --codex)
      codex="yes"
      shift
      ;;
    --agent-skill-root)
      [ "$#" -ge 2 ] || die "--agent-skill-root 需要目录参数"
      agent_skill_root="$2"
      shift 2
      ;;
    --claude-skill-root)
      [ "$#" -ge 2 ] || die "--claude-skill-root 需要目录参数"
      claude_skill_root="$2"
      shift 2
      ;;
    --codex-skill-root)
      [ "$#" -ge 2 ] || die "--codex-skill-root 需要目录参数"
      codex_skill_root="$2"
      shift 2
      ;;
    --workbuddy-skill-root)
      [ "$#" -ge 2 ] || die "--workbuddy-skill-root 需要目录参数"
      workbuddy_skill_root="$2"
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
  # 自动发现结构使用 zimaflow-<name> 目录名防冲突；Claude Code 要求
  # frontmatter name 与目录名一致，否则校验报错。
  awk -v newname="$newname" '
    BEGIN { done = 0 }
    !done && /^name:[[:space:]]/ { print "name: " newname; done = 1; next }
    { print }
  ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
}

install_global_skill_root_once() {
  local dst="$1"
  [ -n "$dst" ] || return 0

  case "|$installed_global_roots|" in
    *"|$dst|"*) return 0 ;;
  esac

  install_prefixed_skill_tree "$dst"
  installed_global_roots="${installed_global_roots}|$dst"
}

mkdir -p "$target_dir"
copy_tree "skills"
copy_tree "rules"
copy_tree "references"

if [ "$claude_code" = "yes" ]; then
  install_prefixed_skill_tree "$target_dir/.claude/skills"
fi

if [ "$codex" = "yes" ]; then
  install_prefixed_skill_tree "$target_dir/.agents/skills"
fi

install_global_skill_root_once "$agent_skill_root"
install_global_skill_root_once "$claude_skill_root"
install_global_skill_root_once "$codex_skill_root"
install_global_skill_root_once "$workbuddy_skill_root"

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
  Claude Code skills: $target_dir/.claude/skills/zimaflow-<name>/SKILL.md
EOF
fi

if [ "$codex" = "yes" ]; then
  cat <<EOF
  Codex skills: $target_dir/.agents/skills/zimaflow-<name>/SKILL.md
EOF
fi

if [ -n "$agent_skill_root" ]; then
  cat <<EOF
  Shared agent skill root: $agent_skill_root/zimaflow-<name>/SKILL.md
EOF
fi

if [ -n "$claude_skill_root" ]; then
  cat <<EOF
  Claude Code skill root: $claude_skill_root/zimaflow-<name>/SKILL.md
EOF
fi

if [ -n "$codex_skill_root" ]; then
  cat <<EOF
  Codex skill root: $codex_skill_root/zimaflow-<name>/SKILL.md
EOF
fi

if [ -n "$workbuddy_skill_root" ]; then
  cat <<EOF
  WorkBuddy skill root: $workbuddy_skill_root/zimaflow-<name>/SKILL.md
EOF
fi

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

if [ "$codex" = "yes" ]; then
  cat <<'EOF'
  - Codex 会自动发现 .agents/skills/ 下的 SKILL.md，无需额外配置。
EOF
fi

if [ -n "$agent_skill_root" ] || [ -n "$claude_skill_root" ] || [ -n "$codex_skill_root" ] || [ -n "$workbuddy_skill_root" ]; then
  cat <<'EOF'
  - 已写入显式指定的全局 skill root；是否全局可发现取决于对应 agent 是否扫描该目录。
EOF
fi

cat <<'EOF'

注意：v0.1 基础安装脚本不负责 OpenSpec 初始化、项目注册表或项目文档目录。
EOF
