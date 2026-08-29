# Reviewer–Executor Loop Contract

本契约用于审核者给 Claude Code、Codex 新 Session、WorkBuddy 或其他开发 Agent 下发工作，并根据执行证据继续评审的场景。它是显式 opt-in 的 collaboration profile，不改变缺省的 1.22.5 单 Agent 行为；它不是 Handover 简化模板，也是该协作模式的唯一规则真源，Skill、宿主 wrapper、Learn 和全局记忆只引用本文件。

## 三层信息边界

| 层级 | 载体 | 用途 |
| --- | --- | --- |
| 项目真源 | OpenSpec、Design、Decision、代码、测试、状态文件 | 长期保存可追溯事实与约束 |
| 每轮闭环 | Execution Brief + Execution Report | 审核者与执行者的一轮短期通信 |
| 恢复机制 | Handover | 中断、换人且真源不足、长期暂停或用户明确要求时恢复 |

Brief/Report 必须引用项目真源入口，不复制 OpenSpec、Design、Decision、state 或 Handover 正文。审核结论要成为长期事实时，仍由原 owner 流程回写对应项目真源。

## 循环

```text
审核者读取项目真源与上一轮 Report
  → 输出本轮 Execution Brief
  → 执行者在权限内持续工作
  → 返回 Execution Report 与证据
  → 审核者对照项目真源批准，或输出下一轮目标级 Brief
```

审核未通过时描述“尚未满足的系统目标、边界和证据”，不输出逐函数、逐文件、逐问题的小补丁清单。

每个 opt-in Change 以一个 objective 为审核单位，并使用 `planned → executing ↔ checkpoint → review_ready → accepted` 生命周期；审核退回记录 `changes_requested` 并进入下一 round，真实权限/产品阻断可进入 `blocked`。`checkpoint` 只属于执行者内部，不触发审核或对外 Report；`review_ready` 只能由任务级机器门产生；`accepted` 只由 reviewer/用户决定。

## Execution Brief

按下列顺序输出且仅输出七个二级标题区块；不得添加前言、附录、额外/重复区块、其他标题层级或空区块：

```markdown
## 执行上下文
- 目标宿主
- 代码仓
- 项目知识库
- 当前分支 / OpenSpec Change
- 项目真源入口

## 本轮目标

## 任务范围

## 权限
- 可自主执行
- 禁止执行
- 需用户批准

## 硬约束

## 阻断边界

## 交付证据
```

规则：

- 默认 200–500 个中文字符。只写一个 objective、其 Definition of Done 和结果级范围；任务区默认不超过 6 条，不展开类、函数、行号、单个 finding 或实现步骤。
- 代码仓与项目知识库必填。先用 `zimaflow project show --json` 或等价解析核实；已核实写规范化绝对路径，且必须与校验命令传入的根目录精确一致；未知时先查询，不得按旧记忆猜测。
- 权限明确区分三类。未经本轮用户授权，push、发布、不可逆删除、真实数据迁移、外部凭据、扩大目录、覆盖用户改动不能列为可自主执行。
- 普通测试/构建失败、实现困难和可在确认范围修复的设计问题不是阻断；执行者应继续定位和修复。
- 权限必须允许执行者在确认范围内自主修复设计、代码、测试和文档；交付政策必须声明 checkpoint 不对外汇报，只有 `review_ready` 或真实 `blocked` 才返回 Report。
- 阻断仅限：现有规范无法裁决的用户/产品决策、权限或目录扩大、不可逆操作、覆盖用户改动、外部凭据、规范冲突；一个列表项包含多个条件时，每个分句都必须分别属于此范围，不能用一个合法关键词掩盖额外阻断。
- 同类缺陷连续出现两次，或安全/架构假设被推翻时，本轮目标升级为完整边界审计、根因治理或结构性重构；硬约束禁止继续逐函数、逐问题或兼容性补丁。
- 交付证据要求返回 Execution Report，包含可运行命令或可审计路径，并写明停在 `review`、`archive`、`push` 或 `release` 前。

## Execution Report

执行者按下列顺序返回且仅返回六个二级标题区块；不得添加前言、附录、额外/重复区块、其他标题层级或空区块：

```markdown
## 完成结果

## 根因与设计选择

## 改动范围

## 验证证据

## 剩余风险

## 待用户批准事项
```

`完成结果` 首行必须声明 `review_ready` 或 `blocked`。`review_ready` Report 如实说明根因与选择理由、实际改动边界、剩余风险和仍需批准事项，并以可解析的精确 `repo://` 路径链接当前 diff、OpenSpec task state、boundary matrix 与每个被计入的 structured verification receipt；只写关键词、目录或自由文本“测试通过”都不能替代这些证据。`blocked` 只用于本契约允许的真实 blocker。Report 不美化进度、不粘贴长日志、不把项目真源正文复制成报告。

## 机器事实与完成门

`.zimaflow-state.yaml` 只保存 profile、objective、round、phase 与逻辑指针；round transition、finding 和 reviewer decision 追加到 `events.jsonl`。每个新 event 通过 `previous_event_id` 链接 state 的 `event_head`，携带完整 collaboration `state_after`，写入成功后再原子替换 state，并用同一 event timestamp 更新顶层 `updated_at`。若进程在两次写入间中断，下一命令只可恢复一个链条正确的 pending event；多事件分裂、错误前驱或 summary 不一致必须以 `lifecycle_history_diverged` fail closed。finding 由 reviewer 选择稳定 `defect_class` 与 `boundary_id`，机器从同一 objective 的历史事件派生 occurrence count；任何人工 `recurrence_count` 都不是权威输入。

boundary matrix 将当前 Change 全部 delta-spec requirement/scenario 一一映射到项目声明的 owner boundary、invariant、所需 evidence type、receipt refs 与状态，并声明 `diff_base` 与精确 `diff_artifact`，不固化项目或框架名称。structured receipt 记录 argv、规范化 cwd、git commit、source tree、worktree isolation、batch/sequence、时间、exit code/result 及 artifact hash；它只证明命令事实，证据的语义充分性仍由 reviewer 判断。

`review-ready` 必须 fail closed：required tasks、delta-spec 全集映射、`diff_base..HEAD` 精确 diff、只含 state/validation 的 evidence dirty set、fresh receipts、精确 Report 链接、一致 lifecycle history、复发升级和权限边界全部满足后才推进。稳定诊断至少区分 `task_completion_incomplete`、`boundary_matrix_open`、`boundary_evidence_missing`、`spec_mapping_incomplete`、`spec_mapping_unknown`、`spec_mapping_duplicate`、`diff_evidence_invalid`、`report_evidence_link_missing`、`report_evidence_link_unresolved`、`source_worktree_dirty`、`lifecycle_history_diverged`、`receipt_commit_stale`、`receipt_source_tree_stale`、`receipt_cwd_mismatch`、`receipt_isolation_mismatch`、`receipt_order_invalid` 与 `recurrence_upgrade_unresolved`。

## 状态所有权

工程实现、严格校验、全量回归和 `review_ready` 是工程事件，不等同于用户确认 OpenSpec 审核或 reviewer 接受。用户明确确认前，`.zimaflow-state.yaml` 必须保持 `openspec.spec_review_confirmed: false` 且 `spec_review_confirmed_at` 为空；`implementation.completed_at`、`verification.*` 与 `collaboration.*` 按真实事件独立更新。通过测试不得代替用户写入审核确认，`accepted` 也不替代 archive/finalize/close。

## Handover 边界

活跃的审核者—执行者循环不自动创建或更新 Handover；checkpoint、review-ready 和 changes-requested 都不等于恢复需求。以下情况才需要：

- 任务中断，需要另一 Session 恢复未完成状态；
- 执行者更换，并且 OpenSpec/Design/代码/state/Report 不足以恢复；
- 长期暂停，短期 Brief/Report 不再适合承担恢复信息；
- 用户明确要求交接。

普通 review 往返、只更换宿主但项目真源足够、审核未通过进入下一轮，都不触发 Handover。触发后仍使用 `handover-manager` 的现有完整模板和详细程度。

## 两个主接入点

- `sdd-router`：先识别项目和 quick / standard / full；只有显式启用 profile 且任务要交给新 Session 或其他 Agent 时，初始化 objective 并按本契约生成 Brief。
- `spec-compliance-check`：只在 `review_ready` 后做语义审核；审核未通过时按 objective/requirement/boundary 记录 finding 与 `changes_requested`，再输出下一轮目标级 Brief；复发时扩展边界审计。
- `session-close-reconciler`：核对 opt-in objective 已 accepted 或有显式终止证据；`zimaflow close --json` 用 `review_loop_not_accepted` 保留独立 blocker。

`handover-manager` 不是 Brief 生成入口，只执行上面的恢复边界。

## 行为验证

下面的命令块是公开契约的一部分，并由文档回归测试原样执行。调用方必须先提供已核实的绝对路径；`--source-file` 可重复传入本轮引用的 OpenSpec、Design、Decision、state 或 Handover 文件，以便守卫检测正文复制。

<!-- reviewer-executor-contract-example:start -->
```bash
: "${REVIEWER_EXECUTOR_CLAUDE_BRIEF:?set an absolute Claude Code Brief path}"
: "${REVIEWER_EXECUTOR_CODEX_BRIEF:?set an absolute Codex Brief path}"
: "${REVIEWER_EXECUTOR_WORKBUDDY_BRIEF:?set an absolute WorkBuddy Brief path}"
: "${REVIEWER_EXECUTOR_REPORT:?set an absolute Execution Report path}"
: "${REVIEWER_EXECUTOR_SOURCE_FILE:?set an absolute project source file path}"
: "${REVIEWER_EXECUTOR_CODE_ROOT:?set the verified absolute code root}"
: "${REVIEWER_EXECUTOR_DOCS_ROOT:?set the verified absolute docs root}"

./bin/zimaflow reviewer-executor validate-brief \
  --file "$REVIEWER_EXECUTOR_CODEX_BRIEF" --host codex \
  --code-root "$REVIEWER_EXECUTOR_CODE_ROOT" \
  --docs-root "$REVIEWER_EXECUTOR_DOCS_ROOT" \
  --source-file "$REVIEWER_EXECUTOR_SOURCE_FILE" --json
./bin/zimaflow reviewer-executor validate-report \
  --file "$REVIEWER_EXECUTOR_REPORT" \
  --source-file "$REVIEWER_EXECUTOR_SOURCE_FILE" --json
./bin/zimaflow reviewer-executor parity \
  --claude-code "$REVIEWER_EXECUTOR_CLAUDE_BRIEF" \
  --codex "$REVIEWER_EXECUTOR_CODEX_BRIEF" \
  --workbuddy "$REVIEWER_EXECUTOR_WORKBUDDY_BRIEF" --json
./bin/zimaflow reviewer-executor handover-decision \
  --reason normal-review --project-source-sufficient --json
```
<!-- reviewer-executor-contract-example:end -->

guard 检查实际 Brief/Report 和恢复决策，不是通用自然语言推理器。失败时修正本轮通信，不修改生成包、cache 或安装 runtime。
