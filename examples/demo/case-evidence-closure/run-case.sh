#!/usr/bin/env bash
# 证据收口案例的可执行入口：
#   - 真实运行 todo.sh 的聚焦测试，产出可复跑的 verify 证据；
#   - 打印本案例的产物路径，便于顺着链路读下去。
# 不依赖任何外部服务、网络或凭证；只用到 bash，全部在临时目录中进行。
set -euo pipefail

case_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

hr() { printf '\n=== %s ===\n' "$1"; }

hr "场景"
cat <<'EOF'
需求：给已有的本地 todo CLI 增加 list 状态筛选（--status pending|done|all）。
定档：走轻量模式——需求小、纯读、不改持久化格式，不写 OpenSpec 三件套，
      规范由 brief 的 Given/When/Then 承担，计划由轻量任务台账承担。
看点：证据怎么收口——可复跑的验证、独立落盘的合规报告、逐项对账的收口清单。
EOF

hr "第 1 步：跑真实测试（verify 证据）"
bash "$case_root/app/test-todo.sh"

hr "第 2 步：本案例产物"
cat <<EOF
实现与验证：
  $case_root/app/todo.sh
  $case_root/app/test-todo.sh

链路产物：
  $case_root/project-docs/docs/Requirements/2026-07-29-list-status-filter-brief.md
  $case_root/project-docs/docs/Tasks/2026-07-29-list-status-filter-tasks.md
  $case_root/project-docs/docs/Reviews/2026-07-29-list-status-filter-compliance-report.md
  $case_root/project-docs/docs/Closing/2026-07-29-list-status-filter-closing.md
  $case_root/project-docs/docs/Learn/2026-07-29-list-status-filter-lesson.md
EOF

hr "完成"
cat <<'EOF'
本次演示真实执行了 todo.sh 的聚焦测试，输出 verify passed: 6/6 checks。
这份输出就是合规报告与收口清单里引用的那条证据——命令可复跑，结论可核对。
EOF
