---
name: openspec-superpowers-bridge
description: >
  OpenSpec 规范到 Superpowers TDD 执行的衔接。
  在开始实现 OpenSpec 的 tasks 时触发，自动加载规范文档作为 Superpowers planning 的输入。
  触发词：开始实现、apply tasks、实现 spec、开始编码、从 tasks 开始。
---

# OpenSpec-Superpowers Bridge — 规范到执行的衔接

## 铁律

实现任何 OpenSpec task 之前，必须先加载对应的规范文档。没有规范上下文的实现就是盲写代码。

## 前置条件

- OpenSpec 的 explore 和 propose 已完成
- `openspec/changes/<name>/` 下存在 proposal.md、design.md、tasks.md
- 用户已审核并确认 spec

## 执行步骤

### Step 0：Spec Review 确认 Gate

在加载规范上下文之前，必须先确认 spec 已经过用户审核。这是质量的生命线——未经审核的 spec 进入实现阶段，返工成本远大于在此暂停。

检查方式：

1. 检查 `openspec/changes/<name>/` 下是否存在三个必要文件：
   ```bash
   ls openspec/changes/<name>/proposal.md openspec/changes/<name>/design.md openspec/changes/<name>/tasks.md
   ```
   任一缺失 → 阻断，提示用户先完成 propose。

2. 检查 tasks.md 条目数是否超过 15 项：
   ```bash
   grep -c '^\s*- \[' openspec/changes/<name>/tasks.md
   ```
   超过 15 项 → 阻断，提示用户回到 task-planning 拆分为多个变更。

3. 向用户确认审核状态：
   > 即将进入实现阶段。请确认你已审核以下 spec 文档：
   > - proposal.md — 需求范围与排除范围
   > - design.md — 技术方案与架构决策
   > - tasks.md — 任务拆分（共 N 项）
   >
   > 确认无误？还是需要先调整？

4. 用户明确确认后，继续 Step 1。如果用户说"还要改"，暂停等待。

---

### Step 1：加载规范上下文

读取以下文件（全部必读）：

1. `openspec/specs/` 下的主规范（了解已有约束，避免本次改动破坏已有行为）
2. `openspec/changes/<name>/` 下的全部文档：
   - `proposal.md` — 做什么、为什么、排除范围
   - `design.md` — 怎么做（技术方案、架构决策）
   - `tasks.md` — 任务拆分

如果不确定当前变更目录名称：
```bash
ls openspec/changes/
```
如有多个未归档的变更，询问用户确认使用哪个。

### Step 1.5：旧实现检查（条件触发）

**触发条件**：以下信号出现在 proposal.md、design.md 或用户对话中，任一满足即触发：

- 恢复旧功能 / 回到之前的行为 / 修回历史行为
- 老版本有这个能力 / 像原来那样
- 对齐旧实现 / 参考旧版

**触发后必须执行**（在进入 Step 2 planning 之前）：

1. 用 `git log --all -S "关键词"` 搜索历史提交，关键词取 spec 中涉及功能的核心词（如组件名、DOM class、函数名）
2. 找到相关 commit 后，用 `git show <commit> -- <文件>` 查看旧实现
3. 把旧实现的关键信息（DOM 结构、状态设计、核心逻辑）纳入 Step 2 的 planning 输入

**禁止**：在未执行上述检查之前，直接按 spec 自行猜测 DOM 结构、状态结构或交互细节。

**示例**：

> design.md 写"编辑区与预览区双向滚动联动，百分比映射"  
> → 触发检查 → `git log --all -S "scrollTop"` → 找到旧 commit → `git show` 确认旧版用的是 `.w-md-editor-area` 和 `.preview-pane`  
> → planning 直接复用这两个选择器，不重新猜

**未触发时**：跳过此步，直接进入 Step 2。

---

### Step 2：跳过 Superpowers brainstorming

OpenSpec 的 explore + propose 已经完成了需求分析和方案设计，等价于 Superpowers 的 brainstorming 阶段。

**直接进入 Superpowers 的 planning 阶段**，把 design.md 作为 planning 输入。

### Step 3：转换 specs 为 TDD 测试用例

把 specs/ 中的场景映射为测试用例。每个"假设/当/则"场景至少生成：

| 场景类型 | 测试要求 |
|---------|---------|
| 正常路径 | 假设 → setup，当 → action，则 → assertion |
| 错误路径 | 假设异常条件 → setup，当 → action，则 → error assertion |
| 边界值 | 如果场景涉及数值/时间/长度等边界，额外添加边界测试 |

### Step 4：拆解 tasks 为 TDD 粒度

把 tasks.md 中的每个任务进一步拆成 Superpowers plan 的执行粒度：

1. 每个 task → 1 个或多个 TDD 循环
2. 每个 TDD 循环：写失败测试 → 最小实现 → 重构 → 提交
3. 任务之间保持独立性，按依赖顺序执行

### Step 5：逐 task 执行

按 plan 顺序逐个执行，每个 task 完成后：

1. 运行该 task 相关的测试，确保绿色
2. 触发 `spec-compliance-check` 审查规范合规
3. 通过后继续下一个 task

**关键决策点暂停**：遇到以下情况必须暂停等用户拍板：
- 引入新依赖
- 改变接口契约
- 需要偏离 spec 排除范围的改动

**Spec 缺失回流**：实现过程中发现 spec 有遗漏（design.md 未覆盖的场景、tasks.md 缺失的步骤、proposal.md 未定义的边界），**不能靠猜测继续写代码**。必须：
1. 立即停止当前 task 的实现
2. 列出缺失项清单，说明"缺什么、为什么影响实现、建议补什么"
3. 等用户确认后，回到 OpenSpec propose 阶段补齐 spec（`/opsx:propose <name>` 更新对应文件）
4. spec 补齐并经用户确认后，重新从 Step 1 加载更新后的规范上下文，再继续实现
5. 最多回流 3 轮；如果 3 轮后仍有缺失，标记为 blocked 并生成 handover，等用户离线解决后再继续

### Step 6：全部完成后验证

所有 task 完成后，按顺序执行：

1. `spec-compliance-check` 全量审查
2. `/opsx:verify <name>` — OpenSpec 验证
3. 全量测试（`go test ./...` / `npm test` / `pytest` 等，按项目技术栈）
4. 三个验证都通过，才能执行 `/opsx:archive <name>`

## 审查的双重检查

每次代码审查必须包含两个维度：
1. **代码质量**（Superpowers 默认审查）
2. **规范合规**（spec-compliance-check Skill）

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| AI 没读 design.md 就开始实现 | bridge Skill 未触发 | 手动要求"先读 spec 再实现" |
| tasks 粒度太粗，一个 task 涉及太多改动 | 未拆成 TDD 步骤 | Step 4 拆解不够，要求进一步细分 |
| verify 通过了但测试没跑全 | 跳过了 Step 6 的全量测试 | archive 前强制跑项目级测试命令 |
| 实现时发现 spec 有遗漏 | 正常情况 | 触发 Spec 缺失回流：停止实现 → 列缺失清单 → 回到 propose 补齐 → 重新加载 spec → 继续。最多 3 轮，超过则 blocked |
