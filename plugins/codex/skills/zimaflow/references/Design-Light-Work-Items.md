# Light Work Items 设计

> 类型：Design
> 状态：v0.1 first slice
> 日期：2026-07-23
> 范围：zimaflow 轻量模式，可选启用

## 目标

给轻量模式任务提供一份小而稳定的任务台账，让跨 session 续接、handover 和收口检查不再只依赖自由叙述。

Light Work Items 只解决一件事：当轻量模式不值得进入 OpenSpec，但任务已经有多个步骤时，用 `work-items.yaml` 记录每个步骤的状态、验证和阻塞原因。

## 启用条件

默认不启用。只有命中以下任一信号时，`task-planning` 才建议建立 work-items：

- 超过 3 个子步骤。
- 预计需要跨 session 继续。
- 涉及多个文件、多个阶段或多个工具。
- 有明确阻塞项、待确认项或验证证据要记录。
- 用户明确要求"列个台账 / 下次接着做 / 跟一下进度"。

单文件、小文案、小样式、一次性脚本等低风险短任务不建台账，只在 handover 里简述即可。

## 文件位置

推荐位置：

```text
<docs_dir>/States/YYYY-MM-DD-<task-slug>-work-items.yaml
```

如果项目没有 `States/` 目录，生成前先说明并创建；如果用户不想落文件，可先把同样字段写在 handover 的 `## Work Items` 表格里。

### 可读文件名前缀（可选）

轻量任务也可以借用 `draft_ / ready_ / done/` 文件名前缀，给用户和接手 Agent 一个零工具依赖的进度提示：

```text
<docs_dir>/States/draft_YYYY-MM-DD-<task-slug>-work-items.yaml
<docs_dir>/States/ready_YYYY-MM-DD-<task-slug>-work-items.yaml
<docs_dir>/States/done/YYYY-MM-DD-<task-slug>-work-items.yaml
```

文件名前缀只表达给人看的进度信号：

| 前缀 / 目录 | 含义 |
|------|------|
| `draft_` | 任务台账仍在讨论或等待用户确认 |
| `ready_` | 任务台账已确认，可以按项执行 |
| `done/` | 任务已完成或关闭，台账移入归档目录 |

边界：

- 文件名前缀不替代 `items[].status`。单个工作项状态仍以 YAML 字段为准。
- 文件名前缀不替代 handover 或 state。handover 记录过程和下一步，`.zimaflow-state.yaml` 仍是完整模式的机器可读状态。
- 不自动流转。只有用户确认、任务开始执行或任务关闭时，Agent 才建议改名或移动，并说明涉及文件。
- 如果项目不允许改名或移动文件，保持固定路径，在 handover 中记录当前状态即可。

## Schema

```yaml
schema_version: 1
kind: light_work_items
task_id: "2026-07-23-example"
title: "示例轻量任务"
mode: light
requirement_contract:
  path: ""
  intent_lock: ""
items:
  - id: WI-001
    title: "补充规则文档"
    status: todo | doing | done | blocked | skipped
    owner: "agent"
    evidence_path: ""
    verify_command: ""
    verify_result: not_run
    blocked_reason: ""
    notes: ""
updated_at: "2026-07-23T12:00:00+08:00"
```

字段含义：

| 字段 | 含义 |
|------|------|
| `schema_version` | 固定为 `1` |
| `kind` | 固定为 `light_work_items` |
| `task_id` | 轻量任务稳定 ID，建议日期 + slug |
| `title` | 任务名称 |
| `mode` | 固定为 `light` |
| `requirement_contract.path` | 已确认 brief / PRD 路径；紧急热修复可为空并在 handover 补记 |
| `requirement_contract.intent_lock` | 需求契约意图锁；无则留空并在收口列建议补充 |
| `items[].id` | `WI-001` 形式 |
| `items[].status` | `todo` / `doing` / `done` / `blocked` / `skipped` |
| `items[].evidence_path` | 代码、文档、测试报告、截图、CI 链接或 handover 小节路径 |
| `items[].verify_command` | 验证命令；无可验证命令时写"manual"或留空并说明 |
| `items[].verify_result` | `not_run` / `passed` / `failed` / `blocked` / `not_applicable` |
| `items[].blocked_reason` | `blocked` 时必填 |

## 边界

- 不替代 handover。work-items 记录任务状态，handover 记录过程、决策、上下文和下一步。
- 不替代 OpenSpec tasks。完整模式继续使用 OpenSpec `tasks.md` 和 `.zimaflow-state.yaml`。
- 不做自动状态机。状态更新由 Agent 按实际进度写入，或在 handover 中说明未落盘。
- 不强制每个轻量任务都建文件。建台账的成本必须低于恢复上下文的成本。
- 不把长日志、密钥值、发布 token 写入 `evidence_path` 或 `notes`。

## 生命周期

1. `task-planning` 判断是否启用 Light Work Items。
2. 用户确认任务清单后，Agent 生成 `work-items.yaml` 或 handover 表格。
3. 执行过程中，每完成、阻塞或跳过一项，就更新对应 `status`、验证和证据字段。
4. `handover-manager` 在 `## Work Items` 中承接台账摘要和路径。
5. `session-close-reconciler` 检查 `done` 是否有证据、`blocked` 是否有原因、`doing` 是否有下一步。
