---
name: spec-compliance-check
description: >
  规范合规审查。在代码实现完成后、code review 之前触发， 检查实现是否严格符合 OpenSpec 规范。 触发词：合规检查、compliance
  check、检查 spec、审查规范、实现完了。
sync: false
sync_reason: 有意不同步：套件内部子 Skill，由 Zimaflow 主入口路由；宿主 adapter 从独立源码仓生成或注入同一能力根
---

# Spec Compliance Check — 规范合规审查

## 铁律

任何实现必须与 openspec/specs/ 中的规范一致。不一致就是 bug，不是"优化"。

## 触发条件

- 每个 task 完成后（由 bridge Skill 调用）
- 全部 task 完成后的全量审查
- 用户手动触发

## 审查步骤

### Step 0：加载 Guardrails Catalog

先读取 `references/guardrails.yaml`，关注与本 Skill 相关的规则：

- `ZF-GR-003 destructive_change_review`
- `ZF-GR-005 analogy_for_search_evidence_for_decision`
- `ZF-GR-006 schema_permission_write_upgrade`

catalog 是单一真源，用来统一规则 ID、触发条件和报告措辞；本 Skill 仍按下列步骤执行实际审查，不因为 catalog 存在就自动阻断或自动回滚。

### Step 1：加载规范

1. 读取 `openspec/specs/` 下的主规范（检查本次实现是否违反了已有需求）
2. 读取本次变更对应的 `openspec/changes/<name>/` 下的 delta 规范

### Step 2：场景覆盖检查

逐条检查 specs/ 中每个"假设/当/则"场景：

| 检查项 | 通过标准 |
|--------|---------|
| 有对应实现代码 | 场景描述的行为在代码中可追溯 |
| 有对应测试 | 至少有一个测试覆盖该场景的正常路径 |
| 错误路径覆盖 | 异常场景有对应的错误处理和测试 |

未覆盖的场景标记为 `❌ 未实现`，列出清单。

### Step 3：架构决策一致性

检查 design.md 中提到的每个架构决策：

- 选定的技术方案是否被遵守（没有偷偷换成别的实现方式）
- 模块边界是否被尊重（没有跨模块直接调用）
- 数据流是否与设计一致

不一致的标记为 `⚠️ 偏离设计`，说明偏离了什么、实际实现是什么。

### Step 4：排除范围检查

读取 proposal.md 的排除范围（Out of Scope），检查：

- 实现中是否包含了排除范围内的功能
- 是否修改了不该修改的文件或模块

违反的标记为 `🚫 超出范围`。

### Step 4.5：破坏性变更门槛（B4 / ZF-GR-003）

借鉴 flow-kit 老项目护栏 B4。**`B4` 是 flow-kit 的来源名，`ZF-GR-003` 是本套件 catalog（`references/guardrails.yaml`）里的 ID，两者指同一条规则**，报告和文档中出现任一名称都是指本步骤，不是两条独立规则。

以下改动属于"破坏性变更"，实现里出现时必须先 grep 引用面并给出影响说明，不能默默改掉：

| 破坏性信号 | 判断标准 |
|-----------|---------|
| 删除代码 | 单个函数/文件删除 ≥ 5 行 |
| 改公共接口 | 改动被其他模块调用的函数签名、导出符号、路由、事件名 |
| 改 schema | 改数据库表结构、迁移、DTO/序列化字段、配置结构 |
| 改权限/鉴权 | 改权限判断、鉴权中间件、token/session 处理、角色校验 |
| 改数据写入路径 | 改写库/删库/批量更新/幂等键/事务边界 |

检查动作（审查，不自动改）：

- 对每个破坏性信号，要求实现方（或审查时补跑）`grep` / `git grep` 出被影响的引用面，列出调用方清单。
- 给出**影响说明**：改了什么、谁会受影响、是否有兼容处理或迁移、回滚方式。
- 缺少引用面排查或影响说明的，标记为 `⚠️ 破坏性变更未评估`，列入报告，交用户决策。

**这是审查规则，不是自动回滚**：spec-compliance-check 只负责发现并标记，是否回退、加兼容层或补迁移由用户确认后处理。唯一沿用既有铁律自动判失败的仍是"超出排除范围"（Step 4）。

### Step 4.6：沿用抽象检查（B5）

借鉴 flow-kit 老项目护栏 B5。审查新增实现时，检查是否在项目已有同类抽象的情况下另起炉灶：

- 新增的能力（HTTP 客户端、状态管理、日期/金额格式化、鉴权、请求封装、通用组件、工具函数、接口模式等）是否先搜索过项目现有实现。
- 检查方式：对新增实现涉及的能力关键词，`grep` 项目里是否已有同类工具函数、组件、hook、接口模式。
- 找到现成抽象却重复造轮子的，标记为 `⚠️ 未沿用现有抽象`，指出应沿用的现有实现路径。
- 确实没有现成实现、或现有实现不适用（需说明原因）的，判为通过。

**同样是审查规则，不自动改代码**：只标记"这里本可以沿用 X"，是否重构由用户决定。

### Step 4.7：验证证据匹配度（按变更类型）

"测试通过"不等于"验证充分"。不同变更类型该看的证据不同，只跑最容易跑的单测就宣称验证通过，是 AI Coding 里常见的假阳性。

先判断本次实现命中哪些变更类型，再对照下表检查是否有对应证据：

| 变更类型 | 期望的验证证据 |
|----------|----------------|
| 新增 API | 契约测试、兼容性检查 |
| 改数据库 | migration、回滚、历史数据验证 |
| 改 MQ | producer / consumer 兼容性 |
| 改状态机 | 主流程、逆向流程、异常分支 |
| 改权限 | 越权、拒绝路径、审计记录（影响面与回滚归 B4 / ZF-GR-003，本行只看证据） |
| 重构 | 先建立测试安全网，再小步重构，再复跑验证 |

检查动作：

- 一次实现可能同时命中多个类型（例如新增 API 同时改了 schema），逐类型分别核对，不要只按主要类型核对一次。
- 有对应证据（测试、脚本、迁移文件、验证记录、evidence_path）→ 记为 ✅ 并指出证据位置。
- 命中类型但缺对应证据 → 记为 `⚠️ 验证证据不足`，列出缺哪一类，交用户决定是补证据还是接受风险。
- 表中未覆盖的变更类型 → 标注"矩阵未覆盖，建议人工判断"，不要硬套最接近的一行。
- 重构类任务额外遵守一条顺序规则：**无测试安全网，不建议大重构**；如果发现先做了大范围重构、事后才补测试，标记为 `⚠️ 验证证据不足`，说明风险顺序颠倒。

**这是 soft check，不是门禁**：本步骤只标记风险和待补证据，不自动阻断流程、不自动回滚、不自动补测试、不自动改代码，是否补证据由用户决定。

**边界说明**：这只是 `spec-compliance-check` 报告规则的一部分，不是独立的 `zima-check` 产品模块，也不引入新的 CLI 命令或状态字段。

### Step 5：输出审查报告

```markdown
## Spec Compliance Report

**变更**：<name>
**审查时间**：<timestamp>

### 场景覆盖
- ✅ 场景 1：xxx — 已实现，已测试
- ✅ 场景 2：xxx — 已实现，已测试
- ❌ 场景 3：xxx — 未实现

### 架构一致性
- ✅ 决策 1：xxx — 一致
- ⚠️ 决策 2：xxx — 偏离（说明）

### 排除范围
- ✅ 未触碰排除范围
  或
- 🚫 违反：xxx（说明）

### 破坏性变更（B4 / ZF-GR-003）
- ✅ 无破坏性变更
  或
- ⚠️ ZF-GR-003 破坏性变更未评估：xxx — 缺 {引用面排查（调用方清单）/ 影响说明（谁受影响、有无兼容或迁移）/ 回滚方式}
  （信号枚举不在本节重复，命中的高风险信号统一见「高风险契约升级」节）

### 沿用抽象（B5）
- ✅ 已沿用现有抽象 / 无同类现有实现
  或
- ⚠️ 未沿用现有抽象：xxx（应沿用的现有实现路径）

### 证据边界
- ✅ ZF-GR-005 未触发：语义联想只用于搜索，范围/实现决策均有直接证据
  或
- ⚠️ ZF-GR-005 决策缺直接证据：xxx（需要补需求契约、用户原话、设计标注、代码事实或显式假设）
- 搜索词扩展记录：{如有，说明哪些只是候选搜索词，未作为范围决策}

### 高风险契约升级
- ✅ ZF-GR-006 未触发：本次实现未改变 schema / 权限 / 数据写入
  或
- ⚠️ ZF-GR-006 高风险契约边界变化：xxx（schema / 权限 / 数据写入已改变，需确认是否已回到 requirement-contract / route-decision-recorder / OpenSpec review）

### 验证证据匹配度
- 命中变更类型：{新增 API / 改数据库 / 改 MQ / 改状态机 / 改权限 / 重构 / 矩阵未覆盖}
- ✅ 证据齐备：{类型} — {证据位置：测试文件 / 迁移文件 / 验证记录 / evidence_path}
  或
- ⚠️ 验证证据不足：{类型} — 缺 {契约测试 / 兼容性检查 / migration / 回滚 / 历史数据验证 / producer-consumer 兼容性 / 逆向流程 / 异常分支 / 越权 / 拒绝路径 / 审计记录 / 测试安全网}
- 矩阵未覆盖：{如有，说明变更类型和建议的人工判断方式}

### 结论
- [ ] 全部通过 → 可进入 code review
- [ ] 有未覆盖场景 → 需要补实现
- [ ] 有设计偏离 → 需要决策：更新 spec 还是修改实现
- [ ] 超出范围 → 必须回退超范围的改动
- [ ] 有破坏性变更未评估 → 补引用面排查 + 影响说明后由用户决策（不自动回滚）
- [ ] 有未沿用的现有抽象 → 由用户决定是否重构沿用（不自动改）
- [ ] 有高风险契约边界变化 → 回到受影响上游产物确认后再继续
- [ ] 有验证证据不足 → 由用户决定补证据还是接受风险（soft check，不阻断）
```

### Step 5.1：审核未通过时输出下一轮 Execution Brief

当 Step 5 结论不是“全部通过”，且问题仍可在已确认 contract / Decision / OpenSpec 范围内修复时：

1. 读取 `<zimaflow-root>/references/Reviewer-Executor-Loop.md`。
2. 若 state 未启用 `reviewer_executor` profile，保留原有只读审查与 Brief 输出行为，不要求 matrix/receipts，不写 loop state。
3. 若 profile 已启用，先确认 executor 已通过 `review-ready` gate；checkpoint 或普通测试失败不能触发 reviewer decision。gate 必须已经从当前 delta-spec 全集、精确 `diff_base..HEAD`、Report 的逐项 `repo://` 链接、commit/source-tree receipts、evidence-only dirty set 和一致 event/state history 派生事实；不得把关键词、目录链接或单份过期回执当成完成。以当前 objective、round、boundary matrix、structured receipts、Execution Report 和项目真源做语义审核。
4. 对每个有效 finding 运行 `record-finding`，使用稳定 `defect-class`、`boundary`、`requirement` ID；不得填写 recurrence count。feedback 只描述 objective / requirement / boundary / invariant / evidence gap，不给逐函数、逐文件或顺序补丁指令。
5. 审核未通过时，把结构化 feedback 落在当前仓 validation 目录并运行 `review-decision --decision changes-requested --feedback <path>`；CLI 自动开启下一 round。以本次 Spec Compliance Report 和项目真源为证据，输出下一轮 objective-level Execution Brief。
6. `本轮目标` 描述尚未满足的系统目标、边界或证据；同类缺陷连续出现两次、组合场景失败或本轮推翻安全/架构假设时，升级为完整边界审计、根因治理或结构性重构，并在硬约束中禁止继续点补丁。
7. 运行 `zimaflow reviewer-executor validate-brief`，显式传入已核实的 `--code-root` / `--docs-root` 和 `--change`，并用可重复的 `--source-file` 传入本轮实际引用的 Spec Compliance Report 和全部项目真源文件；面向多个宿主时运行 `parity`。不得用占位文件绕过正文复制检查。

全部满足时，profile 路径运行 `review-decision --decision accepted`；这只接受当前 objective，不代替 OpenSpec archive、docs sync、finalize 或 close。

正常审核往返只使用 state/event/matrix/receipt + Execution Brief / Execution Report，不自动创建 Handover。只有任务中断、长期暂停、用户明确要求，或执行者更换且项目真源不足以恢复时，才交给 `handover-manager`。

如果审查发现的是规范缺失、范围/权限扩大、不可逆操作或未裁决产品决策，仍按本 Skill 既有规则停止并交用户，不伪装成可自主修复 Brief。

### Step 5.5：报告落盘要求

全部 task 完成后的**全量审查**（区别于每个 task 完成后的轻量检查），其 Step 5 报告必须落盘为独立文件，不能只在 closing checklist 或 handover 里写一行"合规检查：done"。

- 落盘位置：项目文档目录 `<docs_dir>/Reviews/<date>-<change>-compliance-report.md`。
- `session-close-reconciler` 对应 closing checklist 中"spec 合规检查"一行必须链接该文件路径，而不是只写状态结论。
- 每个 task 完成后的轻量检查（触发条件第 1 项）不强制落盘；只有触发条件第 2 项"全部 task 完成后的全量审查"才要求独立文件。

这条要求来自一次真实审查发现：review/compliance 证据一旦被压缩成 checklist 里的一行状态，就很难被下一次 session 或人工复核独立验证——这次案例审查本身就是靠落盘报告才发现了一个真实的场景覆盖缺口（见 `references/doc-sync-matrix.md` 对应行）。

## 常见问题

| 现象 | 判定 | 处理 |
|------|------|------|
| AI 顺手多改了不相关的代码 | 检查排除范围 | 回退多余改动 |
| 实现方式和 design.md 不一致 | 这是 bug，不是优化 | 要么改代码，要么先更新 spec |
| 场景没有对应测试 | 测试不完整 | 补测试 |
| 发现 spec 本身有遗漏 | 不是实现问题 | 暂停，提示用户补充 spec |
| 删了一大段代码或改了公共接口没排查引用 | B4 破坏性变更未评估 | 标记，要求补 grep 引用面 + 影响说明，用户决策；不自动回滚 |
| 项目已有工具函数/组件却重复实现 | B5 未沿用现有抽象 | 标记应沿用的现有实现路径，用户决定是否重构；不自动改 |
| schema、权限或数据写入已经改了，但 spec 没有对应确认 | ZF-GR-006 高风险契约边界变化 | 标记，回到 requirement-contract / route-decision-recorder / OpenSpec review 确认 |
| 只跑了单测就说"验证通过"，但改了 DB / MQ / 状态机 / 权限 | 验证证据不足（Step 4.7） | 按变更类型矩阵指出缺哪类证据，用户决定补证据还是接受风险；soft check，不阻断 |
| 先做了大范围重构，事后才补测试 | 验证证据不足（重构顺序颠倒） | 标记"无测试安全网不建议大重构"，用户决策；不自动回滚 |
