---
name: openspec-superpowers-bridge
description: >
  OpenSpec 规范到 Superpowers TDD 执行的衔接。 在开始实现 OpenSpec 的 tasks 时触发，自动加载规范文档作为
  Superpowers planning 的输入。 触发词：开始实现、apply tasks、实现 spec、开始编码、从 tasks 开始。
sync: false
sync_reason: 有意不同步：套件内部子 Skill，由 Zimaflow 主入口路由；宿主 adapter 从独立源码仓生成或注入同一能力根
---

# OpenSpec-Superpowers Bridge — 规范到执行的衔接

## 铁律

实现任何 OpenSpec task 之前，必须先加载对应的规范文档。没有规范上下文的实现就是盲写代码。

## 前置条件

- OpenSpec 的 explore 和 propose 已完成
- `openspec/changes/<name>/` 下存在 proposal.md、design.md、tasks.md
- 除紧急热修复外，本轮需求契约已确认，且 proposal.md 或 design.md 引用了需求契约路径
- proposal.md / design.md / tasks.md 与需求契约中的 `意图锁` 对齐；如缺意图锁，至少列为待补，不得自行改写
- 用户已审核并确认 spec
- 进入实现前已确认使用 branch 或 worktree 隔离，不在主分支直接开发

## 执行步骤

### Step 0：Spec Review 确认 Gate

在加载规范上下文之前，必须先确认 spec 已经过用户审核。这是质量的生命线——未经审核的 spec 进入实现阶段，返工成本远大于在此暂停。

检查方式：

1. 读取 Zimaflow state（如存在）：
   ```bash
   cat openspec/changes/<name>/.zimaflow-state.yaml
   ```
   - 如果存在，优先用其中的 `requirement_contract`、`decision`、`openspec`、`implementation` 字段做检查依据
   - 如果不存在，不阻断，但本次 Step 0 通过后必须按 `references/Design-Zimaflow-State.md` 初始化

2. 检查本轮需求契约是否已确认并被 spec 引用（紧急热修复除外）：
   - proposal.md 或 design.md 中应引用需求契约路径（`Requirements/` brief 或 `PRDs/` PRD）
   - 如果缺失 → 阻断，提示先回到 `requirement-contract` / OpenSpec propose 补齐引用

3. 检查 spec 与意图锁是否对齐：
   - 从需求契约或 state 的 `requirement_contract.intent_lock` 读取意图锁
   - proposal.md 或 design.md 应引用或复述意图锁
   - tasks.md 的任务范围不应明显超出意图锁和 Decisions 的 first slice
   - 如果意图锁缺失 → 不自动阻断既有已确认契约，但列为 📝 待补；建议回到 `requirement-contract` 补意图锁后再继续
   - 如果 spec 明显偏离意图锁 → 暂停，提示回到 `requirement-contract` / `route-decision-recorder` / OpenSpec propose 修订并重新确认
   - 本检查不新增 `execution-contract.md`，不做自动回退，不使用硬门禁；用户确认仍是最终依据

4. 检查 `openspec/changes/<name>/` 下是否存在三个必要文件：
   ```bash
   ls openspec/changes/<name>/proposal.md openspec/changes/<name>/design.md openspec/changes/<name>/tasks.md
   ```
   任一缺失 → 阻断，提示用户先完成 propose。

5. 检查 tasks.md 条目数是否超过 15 项：
   ```bash
   grep -c '^[[:space:]]*- \[' openspec/changes/<name>/tasks.md
   ```
   超过 15 项 → 阻断，提示用户回到 task-planning 拆分为多个变更。

6. 检查实现隔离：
   ```bash
   git branch --show-current
   git worktree list
   ```
   - 当前分支是 `main` / `master` / `prod` / `release` 等主干或发布分支，且未使用独立 worktree → 阻断，提示先创建 feature/fix/refactor 分支或 worktree
   - 当前已在本轮专用 branch/worktree → 继续
   - 用户明确说明这是紧急热修复 → 可继续，但必须在输出中标记"紧急热修复：实现隔离例外"，收尾时记录原因

7. 向用户确认审核状态：
   > 即将进入实现阶段。请确认你已审核以下 spec 文档：
   > - proposal.md — 需求范围与排除范围
   > - design.md — 技术方案与架构决策
   > - tasks.md — 任务拆分（共 N 项）
   > - 需求契约引用 — 已确认 brief/PRD 路径
   > - 意图锁对照 — spec 范围仍服务本轮核心目的
   > - 实现隔离 — 当前 branch/worktree 可用于本轮实现
   >
   > 确认无误？还是需要先调整？

8. 用户明确确认后，更新 `.zimaflow-state.yaml`：
   - `phase: spec_reviewed`
   - `openspec.spec_review_confirmed: true`
   - `openspec.spec_review_confirmed_at`
   - `requirement_contract.intent_lock`（如果 state 写入工具支持；否则确保 spec / handover 可追溯）
   - `implementation.isolation`
   - `implementation.branch` 或 `implementation.worktree_path`
   然后继续 Step 1。如果用户说"还要改"，暂停等待。

9. full / P0-P1 hotfix 可在确认后运行 `zimaflow execution-input <name> --write` 生成实现阅读快照。它是派生物，不取代 requirement contract、Decision 或 OpenSpec；`drift-check` 报告 stale 时，暂停并由用户决定刷新或回到上游工件，不自动回退或阻断 git。

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

### Step 5.5：tasks.md 状态漂移检查（soft check）

双环执行有一个真实风险：OpenSpec 生成 `tasks.md` 后，Superpowers 用自己的 plan 执行实现；实现完成后 `tasks.md` 未必被同步勾选。这会让 verify/archive 阶段误判任务未完成，或者更糟——实际完成状态与规格状态分离。

进入 Step 6 验证前，先做一次漂移检查：

```bash
# OpenSpec 侧的勾选状态
grep -n '^[[:space:]]*- \[' openspec/changes/<name>/tasks.md
```

**这里查的是 tasks sync drift，不是 artifact hash drift**：本步骤对照的是 `tasks.md` 的**勾选状态**与实际完成信号；CLI `zimaflow drift-check <change>` 查的是契约 / decision / OpenSpec 三件套的**文件内容** SHA256 是否被改动。两者互不替代，本步骤**不调用 `zimaflow drift-check`**，`drift-check` 也不检查勾选状态。

对照三类实际完成信号：

| 信号 | 观察方式 |
|------|----------|
| Superpowers plan 执行进度 | 本轮 plan 中已完成的执行项 |
| 实际代码改动 | `git diff --name-only` / 本轮改动文件清单 |
| 测试证据 | 已通过的测试命令与结果（`last_command` / `last_result`） |

判定：

- 三类信号显示任务已完成，但 `tasks.md` 对应条目仍未勾选或状态滞后 → 标记 `⚠️ tasks.md 状态漂移`，列出"哪几项实际已完成但 spec 未同步"。
- 反向漂移（`tasks.md` 已勾选，但找不到对应代码改动或测试证据）→ 同样标记，说明缺证据的是哪几项。
- 标记后必须**要求人工确认**是否在 verify/archive 前同步 `tasks.md`，并说明同步依据（文件路径 / 测试结果 / handover 记录 / 用户确认 / 待人工确认）。本轮暂时拿不出依据时，写"待人工确认"，不要留空、也不要用推测填充。

输出模板（与 `session-close-reconciler` Step 3.3.2 同一套结论词，便于 close 前直接承接）：

```markdown
### 🔀 OpenSpec Tasks Sync（tasks sync drift）
- tasks.md：{N} 项已勾选 / {M} 项未勾选
- 实际完成信号：plan={present/absent} / 代码改动={present/absent} / 测试证据={present/absent}
- 漂移：无 / 实际已完成但未勾选（{条目}）/ 已勾选但缺证据（{条目}）
- 同步依据：文件路径 / 测试结果 / handover 记录 / 用户确认 / 待人工确认
- 结论：aligned / needs_tasks_sync / needs_evidence / not_applicable
```

结论取值规则：实际已完成但未勾选 → `needs_tasks_sync`；已勾选但缺代码改动或测试证据 → `needs_evidence`；两类同时存在时都写出来，不合并成一个。

**这是 soft check，不自动写回**：本步骤只对比、标记、要求人工确认，不自动勾选 `tasks.md`、不自动改 spec、不自动推进 phase、不阻断流程。第一版不追求精确同步每一项任务状态，只要求漂移不被静默忽略。

### Step 6：全部完成后验证

所有 task 完成后，按顺序执行：

1. `spec-compliance-check` 全量审查
2. `openspec validate <change-name>` — OpenSpec 验证
3. 全量测试（`go test ./...` / `npm test` / `pytest` 等，按项目技术栈）
4. 三个验证都通过，才能执行 `/opsx:archive <name>`

同时按 `references/Design-Zimaflow-State.md` 更新 `.zimaflow-state.yaml`：

- 开始实现时：`phase: build_started`
- tasks 全部完成时：`phase: build_completed`
- `openspec validate <change-name>` 和全量测试通过时：`phase: verified`，写入 `verification`
- archive 完成后：`phase: archived`，写入 `archive`

archive 不是终态。完成 docs sync、reconciler 与 handover 后，必须使用统一写入端推进状态，再执行最终只读 gate：

```bash
zimaflow finalize <change-name> --docs-synced --handover <repo:// 或 docs:// 路径> --json
zimaflow close --json
```

`finalize` 只有在归档、文档同步和 handover 证据都有效时才把 `archived → closed`；失败时返回明确的 `blocking_reasons` 且不写 state。只有最后一次 `close --json` 返回 `next_action=can_close` 才能宣称实现与 session 已完成。

写入 `verification` 时必须采用 `references/Design-Zimaflow-State.md` 的 **verification evidence** 最小字段：

- `opsx_verify`
- `full_tests`
- `last_command`
- `last_result`
- `evidence_path`
- `blocked_reason`
- `verified_at`

规则：

- 两类验证都通过，才写 `phase: verified`，并将 `last_result` 写为 `passed`。
- 验证失败时，记录失败命令、`last_result: failed`、可追溯的 `evidence_path`（如测试报告/日志路径），不推进 phase。
- 验证被环境或外部依赖阻塞时，记录 `last_result: blocked` 和 `blocked_reason`，并在 handover 里承接。
- `evidence_path` 只写路径或 URL，不粘贴长日志或密钥值。

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
| 代码和测试都完成了，但 tasks.md 还是没勾 | Superpowers 用自己的 plan 执行，OpenSpec tasks 未同步 | Step 5.5 标记 tasks.md 状态漂移，verify/archive 前要求人工确认是否同步；不自动勾选 |
