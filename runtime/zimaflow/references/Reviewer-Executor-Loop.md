# Reviewer–Executor Loop Contract

本契约用于审核者给 Claude Code、Codex 新 Session、WorkBuddy 或其他开发 Agent 下发工作，并根据执行证据继续评审的场景。它是显式 opt-in 的 collaboration profile，不改变缺省的 1.22.6 单 Agent 行为；它不是 Handover 简化模板，也是该协作模式的唯一规则真源，Skill、宿主 wrapper、Learn 和全局记忆只引用本文件。

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

每个 opt-in Change 以 `change_id + objective_id` 为稳定 review scope。一个 Change 可以声明 2–3 个顺序 objective，以多次正式审核完成同一产品结果；每个 objective 仍只使用一次现有 `planned → executing ↔ checkpoint → review_ready → accepted` 生命周期和一个 reviewer decision。首次只能启动 `order=1`，已有 accepted objective 后只能启动其直接后继；两种跳序均以 `objective_sequence_invalid` 在写 state/event 前拒绝。`round` 只表示该 objective 在 `changes_requested` 后的返修尝试，task group 与 receipt batch 只用于组织，不拥有 phase、round 或 decision。`checkpoint` 只属于执行者内部，不触发审核或对外 Report；`review_ready` 只能由任务级机器门产生；`accepted` 只由 reviewer/用户决定。

顺序 objective 默认按强相关纵向闭环拆分，例如 A 主路径、B 相邻/异常路径、C 三宿主或负向路径；系统性 boundary/recurrence closure 与 release readiness 默认仍属于全 Change 门。3–6 tasks 只是建议，不是限制。每个 required objective 必须显式列出 `required_task_ids`：`tasks.md` 的 required tasks 必须完整、唯一归属，不得遗漏、重复或静默换组；当前 objective 只检查自己的 task 完成状态，后续 objective 的未完成 task 不阻塞它，whole-Change closure 才检查全部 required tasks 已唯一覆盖并完成。

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

`.zimaflow-state.yaml` 只保存 profile、当前 objective/round/phase 与 objective plan、subject manifest 等逻辑指针；不得保存 manifest 正文、subject digest payload、accepted-current 缓存或第二套 phase。round transition、finding 和 reviewer decision 追加到 `events.jsonl`。每个新 event 通过 `previous_event_id` 链接 state 的 `event_head`，携带完整 collaboration `state_after`，写入成功后再原子替换 state，并用同一 event timestamp 更新顶层 `updated_at`。若进程在两次写入间中断，下一命令只可恢复一个链条正确的 pending event；多事件分裂、错误前驱或 summary 不一致必须以 `lifecycle_history_diverged` fail closed。finding 由 reviewer 选择稳定 `defect_class` 与 `boundary_id`，机器从同一 objective 的历史事件派生 occurrence count；任何人工 `recurrence_count` 都不是权威输入。

### Manifest-enabled verification subject

只有显式启用 `reviewer_executor` 且提供 canonical objective plan/subject manifest 时，才启用本节；普通 quick/standard/full、默认单 Agent 和旧 no-manifest Reviewer–Executor Change 完整保留 1.22.6 行为。canonical evidence DAG 固定为 `objective plan → manifest → receipt → boundary matrix → Report`。guard 必须从 manifest 全部结构化引用入口（含 `subjects[].refs` 与 semantic inputs）按内容递归遍历 JSON/YAML 图；直接、多跳或指向任意合法文件名/扩展名下游对象的回边都以 `verification_subject_cycle_detected` fail closed，不能依赖 `receipts/` 目录或文件名前缀识别。

subject digest 是 canonical semantic projection 的 SHA-256。projection 固定 UTF-8、LF、Unicode NFC、`repo://` 路径、对象 key 顺序和 schema 声明的 set 排序；包含 change/objective identity、`required_task_ids`、task ID/语义文本/归属、requirement/scenario、boundary/invariant/owner、required evidence、verification contract 和声明的实现/测试输入 content hash。round、commit/tree、timestamp、lifecycle/status、task checkbox、matrix closure/evidence ref、receipt/Report path、命令输出 hash 与 human summary 均排除。task 文本或归属变化必须改变 digest；checkbox 只属于完成门 metadata。objective receipt 以 `change_id + objective_id + subject_digest` 为语义锚；`whole_change` / `release` receipt 则绑定 ordered objective digests 的 canonical aggregate 和 subject union，使任一前序 objective 语义变化都会使全 Change receipt 失效。commit/tree 只作 provenance；同 objective、同 digest、完整 mapping/artifact/result 且 provenance 仍获授权的 receipt 可跨 round 复用。

verification tier 只表示证据资格，不形成 phase、round、lifecycle、blocker 或 reviewer decision：

- `checkpoint_targeted`：checkpoint 只运行受影响专项验证，可生成诊断 receipt，但不得生成正式 Report，也不得满足 `review_ready`。
- `objective_scope`：只在 objective 申请 `review_ready` 且没有可复用 current receipt 时运行完整 scope verification；同 digest 不重复全量验证，semantic input 变化必须重跑。
- `whole_change`：只在全 Change closure 门运行和消费。
- `release`：只在 release/finalize/close 门运行和消费。

`review_ready_passed` event 先冻结实际通过机器门的 manifest pointer、digest、subject IDs、obligation projection、精确 receipt refs 与 Report/matrix/diff 内容哈希；`accepted` 只能消费这份仍可重算且 receipts/下游 evidence 仍有效的同一快照，门后 semantic change 以 `verification_subject_digest_mismatch`、原路径 evidence overwrite 以 `review_ready_evidence_changed` 留在 `review_ready`。accepted event 冻结相同对象，但 accepted 历史不自动等于当前有效证明。同一 deterministic evaluator 必须在启动后续 objective、当前 objective `review_ready`、whole-Change closure、release/finalize/close 四门从当前真源重算；semantic projection 变化返回 `accepted_objective_subject_stale`。旧 accepted event 不删除、不重开 lifecycle；当前 objective 或新顺序 remediation objective 必须对 predecessor accepted 时冻结的 spec pairs、boundary/invariant/owner、required evidence、refs 与 verification contract 做等同或语义超集覆盖，不能通过改弱 stale predecessor 当前 manifest 获得 coverage，并在自己的 `round-01` 经既有 receipt 与单一 reviewer decision 后成为 replacement current coverage。禁止 epoch、rebaseline、digest-only override 或部分 subject acceptance。

完成事实分属不同 owner：`implemented` 由 executor 记录；`closure_pending` 与 `review_ready` 由 deterministic guard 派生；`accepted` 只由 reviewer/用户决定；`release_ready` 由 release/finalize/close gate 决定。前序事实不得替代后序门。structured blocker 只允许未裁决产品决策、权限/目录扩大、不可逆操作、覆盖用户改动、外部凭据/系统或明确规范冲突，并记录 stable category/code、affected subjects、evidence refs 与 required decision；普通测试失败和可修复 evidence gap 属于 `closure_pending`，不是 blocked。

boundary matrix 将当前 Change 全部 delta-spec requirement/scenario 一一映射到项目声明的 owner boundary、invariant、所需 evidence type、receipt refs 与状态，并声明 `diff_base` 与精确 `diff_artifact`，不固化项目或框架名称。manifest path 的 exact diff 等于 `git diff --binary <diff_base>`，绑定 base 到当前 tracked workspace，覆盖 committed、index 与 tracked working-tree 变化；objective plan、manifest、tasks、subject refs 与 semantic inputs 中任何未跟踪文件都以 `verification_subject_diff_incomplete` 拒绝。metadata-only 不改变 digest 或强制重跑 receipt，但其 tracked workspace 差异仍对 reviewer 可见。旧 no-manifest path 继续使用 1.22.6 的 `<diff_base>..HEAD`。复发边界是否系统闭合由 guard 从该边界全部矩阵行的 covered 状态与有效 evidence 派生，不接受执行者自报的 closure 布尔值。structured receipt 记录 argv、规范化 cwd、git commit、source tree、worktree isolation、batch/sequence、时间、exit code/result 及 artifact hash；它只证明命令事实，证据的语义充分性仍由 reviewer 判断。

`review-ready` 必须 fail closed：manifest path 下检查当前 objective 的 `required_task_ids`、current subject mapping、有效 `objective_scope` receipts、accepted predecessors、matrix、tracked-workspace exact diff、精确 Report 链接、一致 lifecycle history、复发升级和权限边界；no-manifest path 保持 1.22.6 的 tasks 全集、delta-spec 全集映射、`diff_base..HEAD`、evidence-only dirty set 与 commit/tree freshness。whole-Change 门另行检查所有 required task 的完整唯一归属与完成、所有 objective matrix/delta-spec/composition/recurrence 的 current coverage 和 `whole_change` receipt；release/finalize/close 再重算并要求 `release` receipt。除既有 reasons 外，新路径稳定区分 `objective_sequence_invalid`、`objective_task_mapping_incomplete`、`objective_task_mapping_duplicate`、`objective_task_mapping_unknown`、`objective_task_assignment_changed`、`verification_subject_cycle_detected`、`verification_subject_mapping_mismatch`、`verification_subject_digest_mismatch`、`verification_subject_diff_incomplete`、`verification_tier_not_eligible`、`objective_scope_receipt_missing`、`receipt_objective_mismatch`、`receipt_artifact_integrity_invalid`、`receipt_provenance_unauthorized` 与 `accepted_objective_subject_stale`。

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

- `sdd-router`：先识别项目和 quick / standard / full；只有显式启用 profile 且任务要交给新 Session 或其他 Agent 时，初始化 objective 并按本契约生成 Brief；manifest path 还要声明纵向 objective plan、唯一 `required_task_ids` 与 manifest pointer。
- `spec-compliance-check`：只在 current objective 的 `review_ready` 后做语义审核；审核未通过时按 objective/requirement/boundary 记录 finding 与 `changes_requested`，再输出下一轮目标级 Brief；复发时扩展边界审计。checkpoint receipt 或后续 objective 的 task 状态不得替代当前 scope 完成门。
- `session-close-reconciler`：manifest path 重新计算所有 required objectives 的 current coverage、task total/exclusive mapping 与 whole/release tier evidence；历史 accepted 数量或缓存汇总不得替代。`zimaflow close --json` 对未 accepted/current、未完整覆盖的 Change 保留独立 blocker。

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
