# Cross-Session Continuity 设计

> 类型：Design
> 状态：v0.1 first slice
> 日期：2026-07-21
> 范围：zimaflow 开发版

## 目标

让下一个 AI session 能可靠接上当前工作，而不是只依赖对话窗口或一份自由格式 handover。

本设计不新增 9 文件 memory 层，不把 handover 替换为 `CURRENT_STATE`，不引入自动状态机。它把现有机制收束成一条轻量跨 session 续接闭环：

```text
session 开始：recall 读取 state + handover + context-index
session 进行中：各阶段写入 state / 决策 / 验证 / 知识使用证据
session 收尾：reconciler 检查一致性，handover 写回最新入口
下次恢复：recall 给出 active change、摘要、bit-rot 和 next_action
```

## 组件职责

| 组件 | 负责回答的问题 | 载体 |
|------|----------------|------|
| Context Index | 这个项目慢变背景在哪里读？ | `docs://.zimaflow/context-index.yaml` |
| Zimaflow State | 当前 OpenSpec change 到哪一步了？ | `repo://openspec/changes/<change>/.zimaflow-state.yaml` |
| Handover | 本轮为什么这样做、改了什么、下一步怎么接？ | `docs://Handovers/*handover*.md` |
| Recall | 下次 session 先看什么、该继续哪个 change？ | `zimaflow recall` |
| Knowledge Ledger | 本轮用了哪些知识、是否影响了决策？ | 用户级 `ZIMAFLOW_DATA_HOME/knowledge-usage-ledger.jsonl`；能力根只读，只带静态 schema |
| Drift Check | 交接后契约 / decision / spec 三件套是否变了？ | `zimaflow drift-check` |

## Session 生命周期

### 1. 开始：恢复入口

当用户说"继续上次 / 接着做 / 出差回来 / 捡一下项目"时，入口应优先走 recall。`zimaflow recall` 是 zimaflow 的 session restore entrypoint：

入口先用 `zimaflow project show --json` 解析当前仓库的 `code_root` / `docs_root`；跨目录点名或总览时由 recall 读取用户级 `~/.zimaflow/projects.yaml`。核心 Skill 不直接解析用户配置，不依赖私人知识库结构。

| 场景 | 命令 |
|------|------|
| 已在项目代码仓 | `zimaflow recall` |
| 知道项目名但不在目录 | `zimaflow recall --project <name>` |
| 多项目回看 | `zimaflow recall --all` |

Agent 读取 recall 输出后，再按 active change 的 state、handover summary、bit-rot next_action 决定继续当前阶段、刷新 handover、重跑测试或请求人工确认。

### 2. 进行中：阶段状态

完整模式下，每个 OpenSpec change 应维护 `.zimaflow-state.yaml`。state 只记录机器可读的稳定字段，不替代用户确认、handover 或 OpenSpec 文档。

轻量模式暂不强行纳入 state。若后续轻量任务也需要 recall，再评估 `docs://States/`，不要提前引入。

### 3. 收尾：一致性检查

session-close-reconciler 在 handover 前检查：

- state phase 是否与实际进度一致。
- state 中的 `handover.latest_path` 是否存在。
- context-index 的 `workflow.latest_handover` 是否与最新 handover 明显脱节。
- context-index 的 `workflow.latest_state` 是否仍指向 active state。
- knowledge usage 是否只停留在 handover 叙事里，而没有 ledger 证据。

发现脱节时只提醒，不自动改写；用户确认"现在补"后再协助写回。

### 4. 交接：下次启动指引

handover-manager 生成 handover 时必须写明下一次 session 的 restore command：

```markdown
- 恢复命令：`zimaflow recall` / `zimaflow recall --project <name>`
```

如果存在 state，handover 还应记录 state path 和当前 phase。生成 handover 后，按职责写回 `handover.latest_path`，并在 context-index 中只更新 `workflow.latest_handover` / `workflow.latest_state` / `updated_at`，不复制正文。

## 写回责任矩阵

| 写回内容 | 负责人 | 时机 |
|----------|--------|------|
| `requirement_contract.path/status/confirmed_at` | `requirement-contract` | 契约确认后；change 尚未创建时传给下游补写 |
| `decision.path/status` | `route-decision-recorder` | 路线决策确认后 |
| `openspec.*` / `spec_review_confirmed` | `openspec-superpowers-bridge` | spec 三件套生成并经用户确认后 |
| `implementation.branch/worktree` | `openspec-superpowers-bridge` | build 开始前完成隔离检查后 |
| `verification.*` | `openspec-superpowers-bridge` 或执行 Agent | verify / full tests 后 |
| `archive.status/docs_synced` | 执行 Agent / `session-close-reconciler` | archive 与 docs sync 后 |
| `handover.latest_path/updated_at` | `handover-manager` | handover 生成后 |
| `context-index.workflow.latest_handover/latest_state` | `handover-manager` | handover 生成后；只写 `docs://` / `repo://` 逻辑路径和短状态 |
| `knowledge usage ledger` | `learn` / 执行 Agent | 用户确认复用 / 引用 / 应用 / 质疑知识后，通过 `zimaflow knowledge-record` 写全局 ledger |

## Knowledge Usage 边界

知识闭环分两层：ledger 记录使用证据，learn 决定是否沉淀或升级。两者不能互相替代。

| 情况 | ledger 事件 | 是否生成 learn 候选 | 是否可改 lesson / Skill |
|------|-------------|---------------------|--------------------------|
| 只是按 anchor 读过知识 | `loaded` | 否，除非读后发现缺口 | 否 |
| 在 plan / review / handover 中明确引用 | `cited` | 可选，若反复出现则提示 | 否 |
| 影响了路由、实现、验证或文档规则 | `applied` | 是，建议评估是否补 lesson 或升级 | 仍需用户确认 |
| 发现旧知识过期、误导或不适用 | `challenged` | 是，建议复核或修订 | 仍需用户确认 |
| 定期淘汰扫描命中 | `stale_review` | 可选，按候选呈现 | 仍需用户确认 |

边界规则：

- ledger 只追加 JSONL 事件，不修改 lesson 正文、出现次数、级别或 Skill 规则。
- `loaded` 只能说明读过，不能单独作为升级依据。
- `applied` 和 `challenged` 是强信号，收口时应进入 Learn 候选。
- 如果本轮已直接回写 Skill/README 规则，仍应生成 lesson 候选，补上"为什么需要这条规则"的可统计记录。
- handover 可以记录 Knowledge Usage 表，但 handover 表格不是 ledger；如果缺 JSONL 事件，应列为待补。

## 不做

- 不新增 `.superpowers-memory/` 式 9 文件结构。
- 不新增 `LEARNING_BACKLOG` 平行文件。
- 不把 handover 全文塞进 state 或 context-index。
- 不做自动 phase transition。
- 不把 `recall` / `release-check` 做成阻断 gate。
- 不默认启用 hard hook。

## 验收标准

- README 能说明 "下次 session 怎么接上"。
- `sdd-router` 遇到继续类触发词时优先进入 recall 路径。
- `handover-manager` 的启动指引包含 restore command。
- `session-close-reconciler` 能检查 state / handover / context-index 的明显脱节。
- `learn` / `session-close-reconciler` / `handover-manager` 对 ledger、lesson 候选和用户确认的边界一致。
- grep 型测试守护上述规则不被误删。
