#!/usr/bin/env bash
# 公开规则守护测试（grep 型，无运行时）。
#
# 目的：本仓已发布的规则文本是产品承诺的一部分，后续编辑不应把它们悄悄改没。
# 这里只做文本存在性核对，不执行任何 skill 逻辑。
#
# 断言约束（新增断言前请先读）：
#   1. 只断言三类内容：章节标题、表格枚举值、以及「规则失效即语义改变」的边界短句。
#   2. 禁止断言完整散文句——措辞打磨属于正常改动，不该让测试变红。
#      测试红了却只能靠改测试来修，几次之后它就失去约束力了。
#   3. 新增断言前先问：这句话被改掉，规则是否真的失效？
#      答案是「否」就不要加。
#
# 覆盖范围：仅限已公开同步的 4 条规则（Reviews 报告落盘、验证证据匹配度、
# not_applicable 折叠、验证失败/证据不完整上浮）。尚未公开的规则不在此断言，
# 断言不存在的东西只会制造永久失败。

# 说明：这里刻意不用 -e。所有断言要跑完再一次性报告，而不是遇到第一条失败就退出。
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

check_contains() {
  local file="$1" needle="$2"
  if ! grep -qF -- "$needle" "$repo_root/$file" 2>/dev/null; then
    echo "FAIL: 缺少断言文本 '$needle' （$file）" >&2
    fail=1
  fi
}

# 作用域限定：只扫 skills/ 下的规则正文。
# references/Design-Zimaflow-State.md 与 bin/zimaflow 含 state schema 的合法字段名，
# 扫全仓会把公开契约误判为越界。
check_not_contains() {
  local dir="$1" needle="$2" reason="$3"
  local hits
  hits="$(grep -rlF -- "$needle" "$repo_root/$dir" 2>/dev/null)"
  if [ -n "$hits" ]; then
    echo "FAIL: $dir 下出现未公开规则用语 '$needle'（$reason）：" >&2
    printf '  %s\n' $hits >&2
    fail=1
  fi
}

check_max_lines() {
  local file="$1" limit="$2"
  local lines
  lines="$(wc -l < "$repo_root/$file" | tr -d ' ')"
  if [ "$lines" -gt "$limit" ]; then
    echo "FAIL: $file 已达 ${lines} 行，超过 ${limit} 行上限；细节应下沉而不是让公开规则膨胀" >&2
    fail=1
  fi
}

# 案例的验证计数必须与文档引用一致。
# 保持简单：期望值写死，不解析脚本内部结构。
check_verify_count() {
  local case_dir="$1" expected="$2"
  local last_line
  last_line="$(bash "$repo_root/examples/demo/$case_dir/app/test-todo.sh" 2>/dev/null | tail -n 1)" || true
  case "$last_line" in
    *"verify passed: $expected checks"*) ;;
    *)
      echo "FAIL: $case_dir 实际输出与期望计数 $expected 不符，实际末行：$last_line" >&2
      fail=1 ;;
  esac
  if ! grep -rqF -- "verify passed: $expected checks" \
      "$repo_root/examples/demo/$case_dir/project-docs" 2>/dev/null; then
    echo "FAIL: $case_dir 的产物文档未引用 'verify passed: $expected checks'（计数漂移）" >&2
    fail=1
  fi
}

# --- 规则 1：Reviews 报告落盘 ---
# 规则进了 skill 而矩阵行被删，规则就成了孤儿；两处一起守护。

check_contains "skills/spec-compliance-check.md" "Step 5.5：报告落盘要求"
check_contains "skills/spec-compliance-check.md" "<docs_dir>/Reviews/<date>-<change>-compliance-report.md"
check_contains "skills/spec-compliance-check.md" "不强制落盘"
check_contains "references/doc-sync-matrix.md" "spec-compliance-check 全量审查完成"
check_contains "references/doc-sync-matrix.md" "Reviews/"

# --- 规则 2：验证证据匹配度（Step 4.7）---
# 只锚定表格首列的六个枚举值（矩阵骨架），不锚定第二列的期望证据措辞。

check_contains "skills/spec-compliance-check.md" "Step 4.7：验证证据匹配度"
check_contains "skills/spec-compliance-check.md" "| 新增 / 扩展接口或 CLI 入口 |"
check_contains "skills/spec-compliance-check.md" "| 改数据库 / 持久化格式 |"
check_contains "skills/spec-compliance-check.md" "| 改 MQ / producer-consumer |"
check_contains "skills/spec-compliance-check.md" "| 改状态机 / 流程状态 |"
check_contains "skills/spec-compliance-check.md" "| 改权限 / 鉴权 |"
check_contains "skills/spec-compliance-check.md" "| 重构 |"
# 这句把「提醒清单」和「判定器」区分开，删掉规则性质就变了。
check_contains "skills/spec-compliance-check.md" "矩阵未覆盖，建议人工判断"

# --- 规则 3：not_applicable 折叠 ---
# 中间两条是边界句：省掉后规则会退化成漏检。

check_contains "skills/session-close-reconciler.md" "规则 A：not_applicable 分节合并显示"
check_contains "skills/session-close-reconciler.md" "只是显示合并，不减少检查项"
check_contains "skills/session-close-reconciler.md" "不检查就不显示"
check_contains "skills/session-close-reconciler.md" "不参与折叠"

# --- 规则 4：验证失败 / 证据不完整上浮 ---
# 「仍然必须上浮」守护正确性修复，「这仍是 soft check」防止被读成硬 gate。
# 两条方向相反，必须同时在场。

check_contains "skills/session-close-reconciler.md" "规则 B：验证失败 / 证据不完整必须上浮"
check_contains "skills/session-close-reconciler.md" "必须写入 ❌ 明确缺失"
check_contains "skills/session-close-reconciler.md" "必须写入 📝 建议补充"
check_contains "skills/session-close-reconciler.md" "仍然必须上浮"
check_contains "skills/session-close-reconciler.md" "这仍是 soft check"

# --- 负向断言：未公开规则不得渗入公开 skills ---
# 第一版只纳入无歧义的三条。quick / standard / full 这类常见英文词需要词边界处理，
# 误报成本高于收益，暂不做成 hard fail。

check_not_contains "skills" "zima-check" "验证矩阵停在报告规则里，不做独立产品模块"
check_not_contains "skills" "OpenSpec Tasks Sync" "tasks 状态漂移规则尚未公开同步"
check_not_contains "skills" "sdd-router-mode-boundaries" "入口瘦身与该 reference 尚未公开同步"

# --- 结构性不变量 ---

# 合规审查目录统一为复数 Reviews/；单数 Review/ 会让读者以为存在两种规范。
stale_review_dirs="$(find "$repo_root/examples" -type d -name Review 2>/dev/null)"
if [ -n "$stale_review_dirs" ]; then
  echo "FAIL: examples 下存在单数 Review/ 目录（应统一为 Reviews/）：" >&2
  printf '  %s\n' $stale_review_dirs >&2
  fail=1
fi

# 公开版规则体量上限：防止同步时把开发版的密度整体搬过来。
check_max_lines "skills/spec-compliance-check.md" 180
check_max_lines "skills/session-close-reconciler.md" 320

# 计数漂移：断言数变化时，引用它的产物文档必须同步。
check_verify_count "case-evidence-closure" "6/6"
check_verify_count "case-cross-session" "7/7"

if [ "$fail" -ne 0 ]; then
  echo "skill-rules tests: FAIL" >&2
  exit 1
fi

echo "skill-rules tests passed"
