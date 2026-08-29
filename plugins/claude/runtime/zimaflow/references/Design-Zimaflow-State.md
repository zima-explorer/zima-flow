# Zimaflow State — per-change 状态文件设计

> 类型：Design
> 状态：v0.1 设计稿
> 日期：2026-07-11
> 来源：Comet `.comet.yaml` 状态文件借鉴；结合 zimaflow 需求契约、路线决策、handover 和 session-close-reconciler 现状裁剪。

## 一、目标

给每个 OpenSpec change 增加一份机器可读的轻量状态文件：

```text
openspec/changes/<change>/.zimaflow-state.yaml
```

它负责回答"当前 change 到哪一步了"，让 Agent、`zimaflow close`、handover 和 reconciler 不再完全依赖自由格式 Markdown 和 git 扫描来拼状态。

状态文件不是 handover 的替代品：

- `.zimaflow-state.yaml` 记录稳定字段，适合机器读取。
- handover 记录过程、原因、文件清单、验证细节和下一步，适合人和 Agent 续接。

v0.1 只覆盖 OpenSpec change。轻量模式任务仍由 requirement-contract、task-planning、handover 承接；等 state 写入流程稳定后，再评估是否增加 `docs://States/` 或 `.zimaflow/states/` 的轻量任务状态文件。

## 二、文件位置

完整模式：

```text
<code_repo>/openspec/changes/<change>/.zimaflow-state.yaml
```

原因：

- 与 OpenSpec change 同生命周期，archive 后自然随 change 结束。
- bridge、verify、archive 都能在代码仓本地直接读取。
- 不污染知识库项目文档目录，避免把机器状态当人工决策文档。

## 三、v0.1 Schema

```yaml
schema_version: 1
change_id: web-page-module-mvp
phase: contract_confirmed
mode: full

requirement_contract:
  path: docs/<project>/Requirements/2026-07-11-example-brief.md
  status: confirmed
  confirmed_at: "2026-07-11T21:30:00+08:00"
  intent_lock: "本轮只解决示例核心问题，让用户能够完成关键结果。"

decision:
  path: docs/<project>/Decisions/Decision-20260711-Example.md
  status: confirmed

prototype:
  enabled: false
  prototype_path: ""
  review_notes_path: ""
  status: not_applicable

openspec:
  change_path: openspec/changes/web-page-module-mvp
  proposal_path: openspec/changes/web-page-module-mvp/proposal.md
  design_path: openspec/changes/web-page-module-mvp/design.md
  tasks_path: openspec/changes/web-page-module-mvp/tasks.md
  spec_review_confirmed: false
  spec_review_confirmed_at: ""

implementation:
  isolation: branch
  branch: feat/web-page-module-mvp
  worktree_path: ""
  started_at: ""
  completed_at: ""

verification:
  opsx_verify: not_run
  full_tests: not_run
  last_command: ""
  last_result: ""
  evidence_path: ""
  blocked_reason: ""
  verified_at: ""

archive:
  status: not_archived
  archived_at: ""
  docs_synced: false

handover:
  latest_path: ""
  updated_at: ""

artifact_hashes:
  contract: ""
  decision: ""
  proposal: ""
  design: ""
  tasks: ""

execution_input:
  path: openspec/changes/web-page-module-mvp/execution-input.md
  status: not_applicable
  generated_at: ""
  confirmed_at: ""

collaboration:
  profile: none
  objective_id: ""
  round_id: ""
  phase: ""
  loop_events: ""
  boundary_matrix: ""
  latest_report: ""
  latest_receipts: []
  termination: ""
  event_head: ""

updated_at: "2026-07-11T21:30:00+08:00"
updated_by: "zimaflow"
```

## 四、字段语义

| 字段 | 含义 |
|------|------|
| `schema_version` | 状态文件格式版本，v0.1 固定为 `1` |
| `change_id` | OpenSpec change 名称 |
| `phase` | 当前阶段，使用固定枚举 |
| `mode` | `full` / `hotfix`，v0.1 不覆盖 light |
| `requirement_contract` | 已确认 brief / PRD 的路径、状态和意图锁 |
| `decision` | 路线决策文档路径，完整模式必填 |
| `prototype` | 原型评审产物路径和状态；未启用时 `enabled: false` |
| `openspec` | proposal / design / tasks 路径和 spec review 确认状态 |
| `implementation` | branch / worktree 隔离信息 |
| `verification` | `openspec validate <change-name>`、全量测试和最近验证结果 |
| `archive` | archive 和 docs sync 状态 |
| `handover` | 最近一次 handover 路径 |
| `artifact_hashes` | 契约、路线决策和 OpenSpec 三件套的 SHA256 基线，用于漂移检测 |
| `execution_input` | full / hotfix 的只读派生快照指针；来源漂移时由读取端报告 stale，不替代真源工件 |
| `collaboration` | 默认 `profile: none`；显式启用 Reviewer–Executor 后保存 objective/round、协作 phase、events/matrix/report/receipts 指针与已提交的 `event_head`，不复制证据正文 |
| `updated_at` / `updated_by` | 最近更新时间和写入来源 |

## 五、phase 枚举

本节顶层 `phase` 是 OpenSpec change 生命周期。`collaboration.phase` 是 opt-in Reviewer–Executor objective 生命周期（`planned → executing ↔ checkpoint → review_ready → changes_requested/accepted`，或 `blocked` / 显式 `terminated`），两者必须分开读取和推进；reviewer 接受 objective 不等于 archive，也不自动把顶层 phase 推进为 `verified` 或 `closed`。

| phase | 进入条件 | 下一步 |
|-------|----------|--------|
| `contract_confirmed` | requirement-contract 已确认并落盘 | route-decision-recorder |
| `route_decided` | Decisions 文档已确认 | proto-review 或 OpenSpec propose |
| `prototype_reviewed` | 原型评审已完成；未启用原型可跳过 | OpenSpec propose |
| `spec_proposed` | proposal/design/tasks 已生成 | spec review |
| `spec_reviewed` | 用户确认 spec，且 tasks <= 15 | bridge build |
| `build_started` | branch/worktree 隔离确认，开始实现 | TDD 执行 |
| `build_completed` | tasks 已完成，初步测试通过 | verify |
| `verified` | `openspec validate <change-name>` 和全量测试通过 | archive |
| `archived` | OpenSpec archive 完成 | docs sync / reconciler / handover / `zimaflow finalize` |
| `closed` | `zimaflow finalize` 已验证 archive、docs sync、handover 证据 | `zimaflow close --json` 最终只读 gate |
| `blocked` | 连续缺失输入或外部条件阻塞 | 等用户或外部状态改变 |

### Archive → close 状态矩阵

| 物理位置 / phase | archive evidence | docs evidence | handover evidence | 统一动作 | `close --json` 结果 / 原因 |
|---|---|---|---|---|---|
| active change / 非 `closed` | `not_archived` | 任意 | 任意 | 先完成 verify 与 OpenSpec archive | `need_archive` / `openspec_change_not_archived`，并按 state 补 `active_state_not_closed` |
| active change / 任意 | 任意 | 任意 | 任意 | opt-in objective 必须先 reviewer `accepted` 或有用户证据的显式 termination | 独立增加 `review_loop_not_accepted`；不得折叠为 docs、archive 或 verification 原因 |
| `archive/` / `archived` | `status=archived` | `docs_synced=false` | 任意 | 同步项目文档，再运行 finalize | `need_finalize` / `archive_state_not_closed`，另有 `archive_docs_not_synced` |
| `archive/` / `archived` | `status=archived` | `docs_synced=true` | 空或文件不存在 | 生成/修复 handover，再运行 finalize | `need_finalize` / `archive_state_not_closed`；finalize 返回 `handover_missing` 或 `handover_not_found` |
| `archive/` / `archived` | `status=archived` | `docs_synced=true` | 路径可解析且文件存在 | `zimaflow finalize <change> --json` | finalize 原子推进为 `closed`，`next_action=run_close` |
| `archive/` / `closed` | `status=archived` | `docs_synced=true` | 路径可解析且文件存在 | `zimaflow close --json` | 其他 gate 也通过时 `can_close`；这是唯一允许宣称完成的结果 |
| `archive/` / `closed` | 不完整 | 任意 | 任意 | 修复证据后重跑 finalize/close | 对应 `archive_docs_not_synced` 或 finalize 的精确 blocker；不得以 phase 单独宣称完成 |
| 任意 / 任意 | 唯一 `change_id` 匹配失败 | 任意 | 任意 | 清理重复 state 或提供正确 change id | finalize 返回 `archive_state_not_found` / `archive_state_ambiguous`，不写文件 |

`need_docs_sync` 是兼容的粗粒度 `next_action`；自动化和 Agent 必须读取 `blocking_reasons[]`。生命周期仍停在 archived 时使用 `archive_state_not_closed`，不得把它退化成模糊的 docs 提示。

close 的 archived blocker 以“当前 working tree + HEAD first-parent 变更集”为 session 边界：本轮刚 archive/finalize 的 state 必须参与 gate，未被本轮触碰的历史 archived state 仍由 `zimaflow state` 可见，但不阻断以后每个无关 session。旧 state 顶层若使用 `change`，读取端兼容回退；新写入仍统一使用 `change_id`。

## 六、写入责任

| 阶段 | 写入者 | 写入内容 |
|------|--------|----------|
| requirement-contract 确认后 | `requirement-contract` 或 `sdd-router` | 初始化 state，写入 `contract_confirmed` 和契约路径 |
| route decision 确认后 | `route-decision-recorder` | 写入 `decision.path`，phase → `route_decided` |
| proto-review 完成后 | `proto-review` | 写入 prototype / review-notes 路径，phase → `prototype_reviewed` |
| OpenSpec propose 后 | `openspec-superpowers-bridge` 启动前检查 | 写入 openspec 三件套路径，phase → `spec_proposed` |
| bridge Step 0 用户确认后 | `openspec-superpowers-bridge` | 写入 `spec_review_confirmed`、实现隔离信息，phase → `spec_reviewed` / `build_started` |
| 跨 Agent objective 显式启动后 | `zimaflow reviewer-executor start` | 仅在当前 change 写入 `collaboration.profile=reviewer_executor`、objective/round、phase 与 `repo://` validation 指针；重复启动幂等 |
| objective 执行 / 审核中 | `zimaflow reviewer-executor transition\|record-finding\|review-ready\|review-decision` | 只通过合法 transition 更新 `collaboration.phase`；finding 与 gate decision 追加到 `loop_events`，不手写复发次数 |
| tasks 完成后 | `openspec-superpowers-bridge` | phase → `build_completed` |
| verify / full tests 后 | `openspec-superpowers-bridge` 或 Agent | 写入 verification，phase → `verified` |
| 建立交接基线时 | `zimaflow drift-check --write` | 写入 `artifact_hashes`，不推进 phase |
| archive 后 | archive Agent / OpenSpec archive Skill | 写入 archive，phase → `archived`；随后自动进入 session close 流程 |
| docs/handover 准备 | `session-close-reconciler` / `handover-manager` | 生成证据；通过 `zimaflow finalize` 参数统一写入，不直接把 phase 手写为 `closed` |
| 收口后 | `zimaflow finalize` | 唯一负责校验并原子推进 `archived → closed`；失败不写 state，重复执行有效 closed state 为幂等 no-op |

除 `archived → closed` 已收敛到 `zimaflow finalize` 外，v0.1 不要求所有 phase transition 自动化。其他阶段仍由 Skill 检查并建议更新 state，避免在没有明确 owner 时扩大写入面。

### Verification Evidence

`verification` 是机器可读的最近验证证据摘要，不替代完整日志或 handover。最小字段：

| 字段 | 含义 |
|------|------|
| `opsx_verify` | `openspec validate <change-name>` 状态：`not_run` / `passed` / `failed` / `blocked` |
| `full_tests` | 项目级全量测试状态：`not_run` / `passed` / `failed` / `blocked` |
| `last_command` | 最近一次关键验证命令，只记录命令，不粘贴长输出 |
| `last_result` | 最近一次关键验证结果：`passed` / `failed` / `blocked`，或简短摘要 |
| `evidence_path` | 详细报告、测试日志、截图、CI 链接或 handover 小节路径；没有则留空 |
| `blocked_reason` | 验证无法完成时的阻塞原因；验证通过时留空 |
| `verified_at` | 最近一次完整验证通过或阻塞记录更新时间 |

规则：

- 声称 `phase: verified` 时，`opsx_verify` 和 `full_tests` 都应为 `passed`，并写入 `verified_at`。
- 若验证失败，记录 `last_command`、`last_result: failed` 和 `evidence_path`（如有），不推进到 `verified`。
- 若验证被环境、依赖、权限或外部服务阻塞，记录 `last_result: blocked` 和 `blocked_reason`，并在 handover 的 `Verification Evidence` 中承接。
- `evidence_path` 只放路径或 URL；不要把长日志、截图正文、secret/token 原文写进 state。

## 七、读取责任

| 读取者 | 用途 |
|--------|------|
| `sdd-router` | 发现未关闭 change 时，提示继续现有 change 或新开需求 |
| `openspec-superpowers-bridge` | Step 0 读取契约、spec review、隔离状态，避免凭对话记忆判断 |
| `session-close-reconciler` | 对账 phase、verify、archive、docs sync、handover 是否一致 |
| `session-close-reconciler`（opt-in） | 额外对账 objective/round、`collaboration.phase`、boundary matrix、latest report/receipts；未 accepted 时上浮 `review_loop_not_accepted` |
| `handover-manager` | 在 handover 中引用 state 文件路径和当前 phase |
| `zimaflow state` | 汇总当前目录（优先）或 git root 下的 `openspec/changes/*/.zimaflow-state.yaml`，输出 human / JSON |
| `zimaflow recall` | 汇总未关闭 change 的进度、artifact 路径、verification / handover 状态，并按 `verified_at` → `handover.updated_at` → 文件 mtime 做 30 天 bit-rot 提醒；只读、不写、不推进 phase。`--days N` / `--summary-lines N` 可调阈值与摘要行数 |
| `zimaflow recall --project <name>` | 从用户级 `~/.zimaflow/projects.yaml` 定位项目，以解析后的 `code_root` / `docs_root` 读取 state 与 handover；无需 cd |
| `zimaflow recall --all` | 跨项目：遍历用户级项目配置中的 active 项目，各自读取 `repo://openspec/changes/*/.zimaflow-state.yaml`，汇总 active / stale / skipped；默认不读 handover 摘要，`--summary-lines N` 显式开启 |
| `zimaflow release-check` | 读取 active change state 的 `verification`（opsx_verify / full_tests）、`archive.status`、`handover.latest_path`，汇总发布前置就绪度（verify / archive / handover / secrets）+ 四问；只读、不 deploy、不读发布 token |
| `zimaflow state init/update` | 统一创建或更新 state 文件的高频字段，减少多 Agent 手写 YAML 的格式漂移 |
| `zimaflow finalize` | 在唯一 archived state 上验证 archive/docs/handover 证据，原子推进为 `closed`；失败不写、成功可幂等重跑 |
| `zimaflow drift-check` | 对比 `artifact_hashes` 与当前文件 hash，发现契约、decision、proposal/design/tasks 是否漂移 |
| `zimaflow close` | 只读最终 gate；扫描 active 与 archived state，输出粗粒度 `next_action` 和精确 `blocking_reasons[]`；只有 `next_action=can_close` 允许完成表述 |

### Reviewer–Executor Evidence Ownership

- `.zimaflow-state.yaml` 只保存协作索引和当前 phase；canonical contract 仍在 `references/Reviewer-Executor-Loop.md`，项目目标与验收语义仍在 Requirement / Decision / OpenSpec。
- `loop_events` 是 append-only JSONL，由 CLI 追加 finding、round、gate 与 reviewer decision；每个新 event 链接 state `event_head` 并携带完整 `state_after`，event 落盘后原子替换 state，同时让顶层 `updated_at` 等于 event timestamp。下次命令只恢复一个有效 pending event，其余链条或 summary 分裂 fail closed。
- `boundary_matrix` 必须把当前 Change 的 delta-spec requirement/scenario 全集一一映射到 boundary/owner/invariant/required evidence，并声明 `diff_base` 与精确 diff artifact；`latest_receipts` 指向带 argv、cwd、commit、source tree、isolation、batch/sequence、timestamps、result 与 artifact hashes 的 JSON 回执。
- `review_ready` 是任务级证据门，不是 session close：required tasks 未完成、spec pair 缺失/未知/重复、diff 非当前派生、Report 链接不可解析、非证据源码 dirty、event/state 分裂、receipt stale/cwd/worktree/order 不一致或复发边界未系统闭合都应返回独立稳定诊断。
- 默认 `profile: none` 时不得要求这些 artifacts，也不得改变现有 1.22.5 单 Agent 路径。

## 八、暂不做

- 不做全自动 phase transition；仅 `archived → closed` 由 `zimaflow finalize` 统一自动写入。
- 不用状态文件替代用户审核；`spec_review_confirmed: true` 只能在用户明确确认后写入。
- `requirement_contract.intent_lock` 只是对照锚点，不替代契约正文；偏离意图锁时回到 requirement-contract / route-decision / OpenSpec 修订并重新确认。
- 不把 handover 全文塞进 state。
- 不把 boundary matrix、receipt 或 event 正文塞进 state，也不新增第二套 lifecycle Skill。
- 不把轻量模式强行纳入 v0.1。
- 不做加密或安全防篡改；`artifact_hashes` 只用于发现漂移。

## 九、后续落地顺序

1. ✅ 在 `openspec/config.yaml` 增加 state 文件约定。
2. ✅ 更新 `requirement-contract`、`route-decision-recorder`、`proto-review`、`openspec-superpowers-bridge`、`session-close-reconciler`、`handover-manager` 的读写规则。
3. ✅ 增加 `bin/zimaflow state` / `state --json`，统一只读汇总 state。
4. ✅ 增加 `bin/zimaflow state init/update`，统一写入高频字段，减少多 Agent 手写 YAML 的格式漂移。
5. ✅ 扩展 `zimaflow close --json`，输出 `active_state_count` 和 `active_state_changes`。
6. ✅ 增加 `bin/zimaflow drift-check`：给契约、decision、proposal/design/tasks 计算 hash，用于发现漂移，不宣称防篡改。
7. ✅ 增加 `bin/zimaflow finalize` 与 archived-state discovery：统一 `archived → closed`，并让 `close --json` 以 `blocking_reasons[]` 输出可操作原因。
