#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

files=(
  "$root/project-docs/PROJECT_REGISTRY.md"
  "$root/project-docs/demo-cli/docs/Requirements/2026-07-11-todo-cli-brief.md"
  "$root/project-docs/demo-cli/docs/Tasks/2026-07-11-todo-cli-tasks.md"
  "$root/project-docs/demo-cli/openspec/changes/add-todo-cli/proposal.md"
  "$root/project-docs/demo-cli/openspec/changes/add-todo-cli/design.md"
  "$root/project-docs/demo-cli/openspec/changes/add-todo-cli/tasks.md"
  "$root/project-docs/demo-cli/openspec/specs/todo-cli.md"
  "$root/project-docs/demo-cli/docs/Closing/2026-07-11-todo-cli-closing.md"
  "$root/project-docs/demo-cli/docs/Handover/2026-07-11-handover-todo-cli.md"
)

echo "zimaflow demo：从一句需求到 handover"
echo
echo "需求："
echo "  Add a tiny todo list CLI that can add, list, and complete tasks."
echo

for file in "${files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "缺少文件：$file" >&2
    exit 1
  fi
done

echo "产物："
echo "  1. 需求 brief"
echo "  2. 任务计划"
echo "  3. OpenSpec proposal/design/tasks"
echo "  4. 基线 spec 场景"
echo "  5. 收口检查清单"
echo "  6. handover"
echo
echo "Demo 检查通过。"
