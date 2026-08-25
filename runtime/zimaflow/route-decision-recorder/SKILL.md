---
name: route-decision-recorder
description: >
  Use when a project has entered full-mode planning and needs a documented route
  decision before OpenSpec propose, especially for product pivots, architecture
  changes, multi-slice work, or cross-repo execution.
sync: false
sync_reason: 有意不同步：套件内部子 Skill，由 Zimaflow 主入口路由；宿主 adapter 从独立源码仓生成或注入同一能力根
---

# Route Decision Recorder — 路线决策落文档

## 职责

你负责在进入 OpenSpec propose 之前，先把“这一轮怎么走”写成知识库仓中的路线决策文档。

这份文档回答的是：
- 为什么这轮要这么走
- 走完整模式还是轻量模式
- 是否需要拆成多个子项目或多个 slice
- 本轮 first slice 是什么
- 是否需要产品原型评审，以及原型只覆盖哪些页面/状态
- 接下来应该开哪个 OpenSpec change

它**不是**产品 PRD，也**不是**代码仓中的 OpenSpec spec；如需页面和状态评审，只记录 `proto-review` 的范围和入口，不把原型旁注整份写进 Decisions。

## 触发条件

出现以下任一信号时，优先触发本 Skill：

- `sdd-router` 已判定为**完整模式**
- 用户正在做产品重构、架构迁移、目录规范迁移、跨仓协同
- 需求过大，需要先拆成多个子项目或多个 slice
- 进入 `/opsx:propose` 前，尚未有本轮对应的 `Decisions/` 文档

以下情况通常**不需要**触发：

- 轻量模式的小改动、bug 修复、样式调整
- 已有本轮最新 `Decisions/` 文档，且用户明确表示沿用，不需要重新拍板

## 输入

优先读取以下上下文：

1. 运行 `zimaflow project show --json`，读取当前项目解析后的 `code_root` / `docs_root`
2. 项目下的 PRD / TECH / 现有 Designs / Decisions
3. `sdd-router` 给出的项目名、需求描述、模式判断、是否启用产品原型评审
4. 已确认的需求契约路径（brief 或 PRD；紧急热修复除外）
5. 如有需要，再快速扫代码仓，确认真实技术边界
6. 如 `sdd-router` 已输出代码图证据，优先复用；必要时再用 `code-graph-to-diagram` 生成 scoped 图表作为路线 / slice 依据

读取需求契约时必须提取 `意图锁` 原文。如果契约已确认但缺少意图锁，继续按已确认契约处理本轮，但在路线决策中列为 📝 建议补充；不要在本 Skill 中替用户新写或改写意图锁。

## 前置 Gate：需求契约

除紧急热修复外，路线决策必须基于已确认的需求契约。开始写 `Decisions/` 前先检查：

- 已有 `需求契约路径`，且状态为"已确认" → 继续
- 只有口头需求、契约仍为"草稿/待确认"、或路径缺失 → 暂停，不写路线文档，交回 `sdd-router` / `requirement-contract`

本 Gate 是 `sdd-router` Step 6.5 的下游冗余校验，用来防止用户直接触发 `route-decision-recorder` 时绕过需求契约。

## 输出位置

输出到项目文档根：

`docs://Decisions/`

`docs://` 必须通过 `zimaflow project show --json` 解析，不能猜测宿主私有目录。

如果 `Decisions/` 不存在，则创建。

文件命名：

`YYYY-MM-DD · <主题>.md`

主题使用“本轮路线决策”“子项目拆分”“first slice”这类可检索措辞，避免过于抽象。

## 执行步骤

### Step 1：确认这是“路线决策”问题

先判断当前问题是否属于以下类型：

- 本轮开发目标发生重心变化
- 需要先决定执行路径，再写 spec
- 需要把大需求切成独立可交付 slice
- 需要澄清知识库仓与代码仓的边界

如果只是普通任务拆解，不要误用本 Skill，交还给 `task-planning`。

### Step 2：提炼本轮拍板项

从 PRD、历史文档、用户表述中提炼：

- 本轮背景变化
- 需求契约中的意图锁
- 关键拍板结论
- 不变量 / 红线
- 模式判定理由
- 子项目拆分方式
- 本轮 first slice
- 产品原型评审范围（如启用）：输入模式、目标页面、关键状态、待确认问题

重点不是面面俱到，而是把**会影响后续 propose 范围**的决定写清楚。

### Step 2.1：意图锁对照

完整模式的路线决策必须回答：

- 本轮 first slice 如何服务需求契约中的 `意图锁`。
- 哪些候选内容看起来相关，但超出意图锁，应放入 Non-Goals 或后续 slice。
- 如果路线决策需要偏离意图锁，暂停并回到 `requirement-contract` 修订契约，等待用户重新确认。

本步骤是软约束，不做硬门禁，不新增 `execution-contract.md`，不自动回退。

### Step 2.5：可选代码图证据 / 图表依据

本步骤用于支撑路线拍板，不是为了"好看地画一张图"。

优先复用 `sdd-router` 的代码图证据：

- `代码图证据`
- `代码图结论`
- `代码图限制`
- `是否建议生成图`

只有当代码结构会影响以下决策时，才调用 `code-graph-to-diagram` 生成持久图表：

- 为什么需要完整模式，而不是轻量模式
- 为什么要拆成多个 slice
- 为什么 first slice 选某个入口 / 模块 / 链路
- 为什么需要先改架构边界、数据模型、权限、跨系统契约
- 为什么某个上游 / 下游影响必须进入 Non-Goals 或后续 slice

推荐图表：

| 决策问题 | 图表 |
|---|---|
| first slice 范围 | impact map / scoped architecture |
| 跨模块依赖 | architecture |
| 关键链路风险 | sequence / dataflow |
| 改前改后路线 | comparison |

保存约定：

```text
docs://Decisions/diagrams/<slug>/
- brief.yaml
- diagram.mmd      # Markdown 决策文档优先，可选
- diagram.svg
- NOTES.md
```

写入 Decisions 文档时：

- 只写短结论与相对路径，不写长查询日志。Markdown 决策文档优先保留 `diagram.mmd`，需要预览或导出时同时保留 `diagram.svg`。
- 明确区分代码事实、AI 推断、静态图限制。
- `trace_path` 图必须标注不是 runtime trace。
- 代码推断数据模型不能当真实 DB schema。
- MCP 不可用、项目未索引、scope 太大或图不可读时，写"代码图依据：未使用 / 跳过原因"，不要阻塞路线决策。

### Step 3：写 Decisions 文档

默认使用以下结构：

```markdown
# <项目名> · <主题>

> 版本：v1.0
> 日期：YYYY-MM-DD
> 状态：已拍板 / 待确认
> 主依据：<PRD 或设计文档链接>
> 意图锁：<从已确认需求契约提取的一句话；缺失时写"待补">
> 说明：OpenSpec spec 落代码仓，路线决策落本仓。

## 一、本轮背景

## 二、拍板结论

## 三、意图锁对照

## 四、架构方向 / 执行路线

## 五、模式判定

## 六、子项目拆分

## 七、First slice

## 七点五、代码图依据（可选）

## 八、产品原型评审（可选）

## 九、OpenSpec 入口

## 十、下一步
```

可按项目需要增减小节，但以下 5 项必须出现：

- **模式判定**
- **意图锁对照**（first slice 如何服务意图锁；超出的内容放哪里）
- **子项目拆分**（如果无需拆分，要明确写“不拆分，本轮直接单 slice 推进”）
- **First slice**
- **产品原型评审**（如无需原型，明确写“不启用”；如启用，写明 PRD-driven / Idea-driven、原型文件预期位置、页面与状态范围）
- **OpenSpec 入口**（change 名称、范围、建议包含的 capability 或设计重点）

如果启用了代码图证据，`代码图依据（可选）` 至少写：

- 查询状态：未使用 / 已复用 sdd-router 证据 / 已生成图表 / 不可用
- 关键结论：1-3 条
- 图表路径：如 `diagrams/<slug>/diagram.mmd` 或 `diagrams/<slug>/diagram.svg`
- 限制：静态代码图 / scope / 截断 / risk label 说明

### Step 4：明确分层

文档中必须显式区分：

- **知识库仓 Decisions**：路线、边界、拍板、slice 切分
- **知识库仓 Prototypes**：可评审页面、状态、旁注、AI 假设和待确认问题
- **代码仓 OpenSpec**：proposal/design/tasks 的正式 spec

不能把 OpenSpec 的细节整份写回知识库仓，也不能把 `prototype.html` 当作生产前端或正式 spec。

### Step 5：确认后再移交

文档写出后，先让用户确认。

确认后：

- 如启用产品原型评审 → 先移交 `proto-review`，评审完成后再进入 OpenSpec 或 task-planning
- 如未启用产品原型评审且仍需估算和任务拆解 → 移交 `task-planning`
- 如任务边界已非常明确，也可直接提示进入 `/opsx:explore` 与 `/opsx:propose <change>`

### Step 6：更新 Zimaflow State

如果本轮 OpenSpec change 名称已确定，初始化或更新：

```text
openspec/changes/<change>/.zimaflow-state.yaml
```

写入内容遵循 `references/Design-Zimaflow-State.md`：

- `phase: route_decided`
- `decision.path`
- `decision.status: confirmed`
- `requirement_contract.path`（如果尚未写入）
- `requirement_contract.intent_lock`（如果 state 支持；否则在 handover / Decision 中保留原文）

如果 change 名称尚未确定，在移交给 OpenSpec propose 时明确要求 proposal/design 引用本 Decisions 文档和需求契约路径，后续由 bridge 补写 state。

## 默认约束

- **先路线，后 propose**：完整模式下，没有本轮 `Decisions/` 文档，不要直接进入 `/opsx:propose`
- **先对照意图锁，再切 slice**：first slice 必须能解释如何服务需求契约的意图锁；超出意图锁的内容进入 Non-Goals / 后续 slice / 需求变更。
- **先切 slice，再开 spec**：如果需求明显过大，先拆子项目，只给 first slice 开本轮 spec
- **知识库仓与代码仓分层**：路线文档不替代 spec，spec 也不吞掉路线文档
- **不阻塞当前主线**：补流程时不要反向要求修改已稳定推进中的代码实现，除非用户明确要求回补

## 常见误区

| 误区 | 问题 | 正确做法 |
|------|------|---------|
| 直接从 PRD 进入 propose | spec 范围容易过大、混入路线决策 | 先写 `Decisions/`，再给 first slice 开 change |
| 把任务拆解当路线决策 | 只能回答“做什么”，回答不了“这轮为什么这样切” | 路线文档先定边界，task-planning 再拆任务 |
| 用 handover 代替路线文档 | handover 是 session 快照，不是本轮拍板依据 | 路线决策写 `Decisions/`，handover 继续做交接 |
| 路线决策偏离意图锁 | 用户确认过的核心目的被下游悄悄改写 | 回到 requirement-contract 修订并重新确认 |
