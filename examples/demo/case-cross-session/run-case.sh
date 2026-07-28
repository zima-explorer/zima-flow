#!/usr/bin/env bash
# 跨 session 案例的可执行演示：
#   - 真实运行 todo.sh 的聚焦测试，产出 verify 证据；
#   - 真实调用 bin/zimaflow state / recall，演示跨 session 上下文恢复。
# 不依赖任何私有环境；只用到 bash 与 git，全部在临时目录中进行。
set -euo pipefail

case_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$case_root/../../.." && pwd)"
zimaflow="$repo_root/bin/zimaflow"

if ! command -v git >/dev/null 2>&1; then
  echo "跳过：未找到 git，无法演示 state/recall。" >&2
  exit 0
fi

hr() { printf '\n=== %s ===\n' "$1"; }

hr "场景"
cat <<'EOF'
需求：给已有的本地 todo CLI 增加「可配置文件路径」。
过程：一次小需求跨两个 session 完成。
  Session 1：确认 brief、拆任务、实现一半，写 handover 后中断。
  Session 2：用 recall 恢复上下文，补测试、跑 verify、收口。
EOF

hr "Session 2 · 第 1 步：跑真实测试（verify 证据）"
bash "$case_root/app/test-todo.sh"

# 用一个临时 git 仓库演示单仓 state / recall（不污染本仓）。
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cd "$work"
git init -q
change="add-configurable-todo-path"
mkdir -p "docs"

# 把 S1 的 handover 与 openspec 骨架放进临时仓库，供 recall 汇总与解析。
cp "$case_root/project-docs/docs/Handover/2026-07-24-handover-session1.md" "docs/handover-session1.md"
mkdir -p "openspec/changes/$change"
cp "$case_root/project-docs/openspec/changes/$change/"*.md "openspec/changes/$change/"

hr "Session 2 · 第 2 步：初始化 state（S1 结束时的快照）"
"$zimaflow" state init "$change" \
  --phase build_started \
  --mode full \
  --handover "docs/handover-session1.md" >/dev/null
echo "已写入 openspec/changes/$change/.zimaflow-state.yaml"

hr "Session 2 · 第 3 步：recall 恢复上下文"
"$zimaflow" recall

hr "Session 2 · 第 4 步：记录 verify 通过并收口"
"$zimaflow" state update "$change" \
  --phase verified \
  --verify passed \
  --full-tests passed \
  --last-command "bash app/test-todo.sh" \
  --last-result "verify passed: 7/7 checks" >/dev/null
"$zimaflow" state
echo
"$zimaflow" close || true

hr "完成"
cat <<EOF
本次演示真实执行了：
  1. todo.sh 聚焦测试（verify 证据）
  2. zimaflow state init / update（写入并更新单仓状态）
  3. zimaflow recall（跨 session 恢复上下文）
  4. zimaflow close（轻量收口检查）

对应的案例文档（brief / tasks / openspec / handover / review-compliance / closing / learn）见：
  $case_root/project-docs/
EOF
