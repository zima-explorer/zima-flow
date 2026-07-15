# Zimaflow State — per-change 状态文件设计

> 类型：Design
> 状态：v0.1 设计稿
> 来源：结合 zimaflow 需求契约、路线决策、handover 和 session-close-reconciler 现状裁剪。
>
> 说明：本文描述 `.zimaflow-state.yaml` 的完整设计。v0.1 公开发行版随附最小 CLI（`zimaflow close`），
> 文中标注「后续 CLI」的命令（`state`、`recall`、`drift-check`、`state init/update`）属完整 CLI 规划，
> 未随 v0.1 发布；此前这些字段由各 Skill 在关键阶段检查并建议手动更新。

## 一、目标

给每个 OpenSpec change 增加一份机器可读的轻量状态文件：

```text
openspec/changes/<change>/.zimaflow-state.yaml
```

它负责回答"当前 change 到哪一步了"，让 Agent、`zimaflow close`、handover 和 reconciler 不再完全依赖自由格式 Markdown 和 git 扫描来拼状态。

状态文件不是 handover 的替代品：

- `.zimaflow-state.yaml` 记录稳定字段，适合机器读取。
- handover 记录过程、原因、文件清单、验证细节和下一步，适合人和 Agent 续接。

v0.1 只覆盖 OpenSpec change。轻量模式任务仍由 requirement-contract、task-planning、handover 承接。

## 二、文件位置

完整模式：

```text
<code_repo>/openspec/changes/<change>/.zimaflow-state.yaml
```

原因：

- 与 OpenSpec change 同生命周期，archive 后自然随 change 结束。
- bridge、verify、archive 都能在代码仓本地直接读取。
- 不污染项目文档目录，避免把机器状态当人工决策文档。

## 三、v0.1 Schema

```yaml
schema_version: 1
change_id: example-change
phase: contract_confirmed
mode: full

requirement_contract:
  path: <docs_dir>/Requirements/2026-01-01-example-brief.md
  status: confirmed
  confirmed_at: "2026-01-01T09:00:00+08:00"

decision:
  path: <docs_dir>/Decisions/Decision-20260101-Example.md
  status: confirmed

prototype:
  enabled: false
  prototype_path: ""
  review_notes_path: ""
  status: not_applicable

openspec:
  change_path: openspec/changes/example-change
  proposal_path: openspec/changes/example-change/proposal.md
  design_path: openspec/changes/example-change/design.md
  tasks_path: openspec/changes/example-change/tasks.md
  spec_review_confirmed: false
  spec_review_confirmed_at: ""

implementation:
  isolation: branch
  branch: feat/example-change
  worktree_path: ""
  started_at: ""
  completed_at: ""

verification:
  opsx_verify: not_run
  full_tests: not_run
  last_command: ""
  last_result: ""
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

updated_at: "2026-01-01T09:00:00+08:00"
updated_by: "zimaflow"
```

## 四、字段语义

| 字段 | 含义 |
|------|------|
| `schema_version` | 状态文件格式版本，v0.1 固定为 `1` |
| `change_id` | OpenSpec change 名称 |
| `phase` | 当前阶段，使用固定枚举 |
| `mode` | `full` / `hotfix`，v0.1 不覆盖 light |
| `requirement_contract` | 已确认 brief / PRD 的路径和状态 |
| `decision` | 路线决策文档路径，完整模式必填 |
| `prototype` | 原型评审产物路径和状态；未启用时 `enabled: false` |
| `openspec` | proposal / design / tasks 路径和 spec review 确认状态 |
| `implementation` | branch / worktree 隔离信息 |
| `verification` | `/opsx:verify`、全量测试和最近验证结果 |
| `archive` | archive 和 docs sync 状态 |
| `handover` | 最近一次 handover 路径 |
| `artifact_hashes` | 契约、路线决策和 OpenSpec 三件套的 SHA256 基线，用于漂移检测 |
| `updated_at` / `updated_by` | 最近更新时间和写入来源 |

## 五、phase 枚举

| phase | 进入条件 | 下一步 |
|-------|----------|--------|
| `contract_confirmed` | requirement-contract 已确认并落盘 | route-decision-recorder |
| `route_decided` | Decisions 文档已确认 | 原型评审记录或 OpenSpec propose |
| `prototype_reviewed` | 原型评审已完成；未启用原型可跳过 | OpenSpec propose |
| `spec_proposed` | proposal/design/tasks 已生成 | spec review |
| `spec_reviewed` | 用户确认 spec，且 tasks <= 15 | bridge build |
| `build_started` | branch/worktree 隔离确认，开始实现 | TDD 执行 |
| `build_completed` | tasks 已完成，初步测试通过 | verify |
| `verified` | `/opsx:verify` 和全量测试通过 | archive |
| `archived` | OpenSpec archive 完成 | docs sync / reconciler |
| `closed` | docs sync、reconciler、handover 完成 | change 结束 |
| `blocked` | 连续缺失输入或外部条件阻塞 | 等用户或外部状态改变 |

## 六、写入责任

| 阶段 | 写入者 | 写入内容 |
|------|--------|----------|
| requirement-contract 确认后 | `requirement-contract` 或 `sdd-router` | 初始化 state，写入 `contract_confirmed` 和契约路径 |
| route decision 确认后 | `route-decision-recorder` | 写入 `decision.path`，phase → `route_decided` |
| 原型评审记录完成后 | 原型评审记录流程 | 写入 prototype / review-notes 路径，phase → `prototype_reviewed` |
| OpenSpec propose 后 | `openspec-superpowers-bridge` 启动前检查 | 写入 openspec 三件套路径，phase → `spec_proposed` |
| bridge Step 0 用户确认后 | `openspec-superpowers-bridge` | 写入 `spec_review_confirmed`、实现隔离信息，phase → `spec_reviewed` / `build_started` |
| tasks 完成后 | `openspec-superpowers-bridge` | phase → `build_completed` |
| verify / full tests 后 | `openspec-superpowers-bridge` 或 Agent | 写入 verification，phase → `verified` |
| archive 后 | Agent / session-close-reconciler | 写入 archive，phase → `archived` |
| 收口后 | `session-close-reconciler` / `handover-manager` | 写入 docs sync、handover 路径，phase → `closed` |

v0.1 不要求所有写入都自动化。先要求 Skill 在关键阶段检查并建议更新 state；后续完整 CLI 提供后再把写入收敛到脚本，避免多个 Agent 手写 YAML 造成格式漂移。

## 七、读取责任

| 读取者 | 用途 |
|--------|------|
| `sdd-router` | 发现未关闭 change 时，提示继续现有 change 或新开需求 |
| `openspec-superpowers-bridge` | Step 0 读取契约、spec review、隔离状态，避免凭对话记忆判断 |
| `session-close-reconciler` | 对账 phase、verify、archive、docs sync、handover 是否一致 |
| `handover-manager` | 在 handover 中引用 state 文件路径和当前 phase |
| `zimaflow close` | JSON 输出和 human checklist 中可增加 active change state 摘要 |

后续 CLI（v0.1 未随附）：`zimaflow state` / `state --json` 汇总 state 摘要；`zimaflow recall` 汇总未关闭 change 的进度并做 bit-rot 提醒；`zimaflow state init/update` 统一写高频字段；`zimaflow drift-check` 对比 `artifact_hashes` 发现契约、decision、三件套漂移。

## 八、暂不做

- 不做全自动 phase transition。
- 不用状态文件替代用户审核；`spec_review_confirmed: true` 只能在用户明确确认后写入。
- 不把 handover 全文塞进 state。
- 不把轻量模式强行纳入 v0.1。
- 不做加密或安全防篡改；`artifact_hashes` 只用于发现漂移。

## 九、落地顺序

1. 在 `openspec/config.yaml` 增加 state 文件约定。
2. 更新 `requirement-contract`、`route-decision-recorder`、`openspec-superpowers-bridge`、`session-close-reconciler`、`handover-manager` 的读写规则。
3. 各 Skill 在关键阶段检查并建议手动更新 state 字段。
4. （后续完整 CLI）增加 `zimaflow state` / `state --json` 只读汇总。
5. （后续完整 CLI）增加 `zimaflow state init/update` 统一写入高频字段。
6. （后续完整 CLI）扩展 `zimaflow close --json` 输出 active change state 摘要。
7. （后续完整 CLI）增加 `zimaflow drift-check`，用 `artifact_hashes` 发现漂移，不宣称防篡改。
