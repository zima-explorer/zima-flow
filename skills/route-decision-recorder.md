---
name: route-decision-recorder
description: >
  Use when a project has entered full-mode planning and needs a documented route
  decision before OpenSpec propose, especially for product pivots, architecture
  changes, multi-slice work, or cross-repo execution.
---

# Route Decision Recorder — 路线决策落文档

## 职责

你负责在进入 OpenSpec propose 之前，先把“这一轮怎么走”写成项目文档库中的路线决策文档。

这份文档回答的是：
- 为什么这轮要这么走
- 走完整模式还是轻量模式
- 是否需要拆成多个子项目或多个 slice
- 本轮 first slice 是什么
- 是否需要产品原型评审，以及原型只覆盖哪些页面/状态（v0.1 只记录评审范围；自动原型 skill 后续提供）
- 接下来应该开哪个 OpenSpec change

它**不是**产品 PRD，也**不是**代码仓中的 OpenSpec spec；如需页面和状态评审，v0.1 只记录评审范围、入口和待确认问题，不把原型旁注整份写进 Decisions。

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

1. `PROJECT_REGISTRY.md` 中该项目的 `docs_dir`
2. 项目下的 PRD / TECH / 现有 Designs / Decisions
3. `sdd-router` 给出的项目名、需求描述、模式判断、是否启用产品原型评审记录
4. 如有需要，再快速扫代码仓，确认真实技术边界

## 输出位置

输出到项目知识库目录下：

`<docs_dir>/../Decisions/`

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
- 需要澄清项目文档库与代码仓的边界

如果只是普通任务拆解，不要误用本 Skill，交还给 `task-planning`。

### Step 2：提炼本轮拍板项

从 PRD、历史文档、用户表述中提炼：

- 本轮背景变化
- 关键拍板结论
- 不变量 / 红线
- 模式判定理由
- 子项目拆分方式
- 本轮 first slice
- 产品原型评审范围（如启用）：输入模式、目标页面、关键状态、待确认问题

重点不是面面俱到，而是把**会影响后续 propose 范围**的决定写清楚。

### Step 3：写 Decisions 文档

默认使用以下结构：

```markdown
# <项目名> · <主题>

> 版本：v1.0
> 日期：YYYY-MM-DD
> 状态：已拍板 / 待确认
> 主依据：<PRD 或设计文档链接>
> 说明：OpenSpec spec 落代码仓，路线决策落本仓。

## 一、本轮背景

## 二、拍板结论

## 三、架构方向 / 执行路线

## 四、模式判定

## 五、子项目拆分

## 六、First slice

## 七、产品原型评审（可选）

## 八、OpenSpec 入口

## 九、下一步
```

可按项目需要增减小节，但以下 4 项必须出现：

- **模式判定**
- **子项目拆分**（如果无需拆分，要明确写“不拆分，本轮直接单 slice 推进”）
- **First slice**
- **产品原型评审**（如无需原型，明确写“不启用”；如启用，写明 PRD-driven / Idea-driven、原型文件预期位置、页面与状态范围）
- **OpenSpec 入口**（change 名称、范围、建议包含的 capability 或设计重点）

### Step 4：明确分层

文档中必须显式区分：

- **项目文档库 Decisions**：路线、边界、拍板、slice 切分
- **项目文档库 Prototypes**：可评审页面、状态、旁注、AI 假设和待确认问题
- **代码仓 OpenSpec**：proposal/design/tasks 的正式 spec

不能把 OpenSpec 的细节整份写回项目文档库，也不能把 `prototype.html` 当作生产前端或正式 spec。

### Step 5：确认后再移交

文档写出后，先让用户确认。

确认后：

- 如启用产品原型评审 → v0.1 先记录评审范围和待确认问题，评审完成后再进入 OpenSpec 或 task-planning；自动 `proto-review` 后续提供
- 如未启用产品原型评审且仍需估算和任务拆解 → 移交 `task-planning`
- 如任务边界已非常明确，也可直接提示进入 `/opsx:explore` 与 `/opsx:propose <change>`

## 默认约束

- **先路线，后 propose**：完整模式下，没有本轮 `Decisions/` 文档，不要直接进入 `/opsx:propose`
- **先切 slice，再开 spec**：如果需求明显过大，先拆子项目，只给 first slice 开本轮 spec
- **项目文档库与代码仓分层**：路线文档不替代 spec，spec 也不吞掉路线文档
- **不阻塞当前主线**：补流程时不要反向要求修改已稳定推进中的代码实现，除非用户明确要求回补

## 常见误区

| 误区 | 问题 | 正确做法 |
|------|------|---------|
| 直接从 PRD 进入 propose | spec 范围容易过大、混入路线决策 | 先写 `Decisions/`，再给 first slice 开 change |
| 把任务拆解当路线决策 | 只能回答“做什么”，回答不了“这轮为什么这样切” | 路线文档先定边界，task-planning 再拆任务 |
| 用 handover 代替路线文档 | handover 是 session 快照，不是本轮拍板依据 | 路线决策写 `Decisions/`，handover 继续做交接 |
