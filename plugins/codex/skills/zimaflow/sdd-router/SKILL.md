---
name: sdd-router
description: >
  开发流程入口路由。当用户描述一个新需求、新任务、新功能时触发。 自动识别目标项目、判断需求规模，按 quick / standard / full
  三档定档（旧名：轻量模式 = quick+standard，完整模式 = full）。 触发词：新需求、新功能、做一个、实现、开发、改一下、加一个、修一个
  bug、排查一下、定位原因、调试、报错、sdd-start。
sync: false
sync_reason: 有意不同步：套件内部子 Skill，由 Zimaflow 主入口路由；宿主 adapter 从独立源码仓生成或注入同一能力根
---

# SDD Router — 开发流程入口路由

## 职责

开发流程的入口调度器。每个新需求从这里开始，产出一个**档位建议**和**下一步移交对象**。

核心职责三件事：

1. **定位**——识别项目、检查初始化状态、恢复已有上下文。
2. **定档**——判断风险与复杂度，给出 quick / standard / full 建议。
3. **移交**——确认需求契约后，交给下一个 skill。

不在这里做的事：不写代码、不生成 spec、不替用户拍板。

细节边界（反例、升级降级细则、旧命名映射、常见误判、复杂度全维度表）见 `<zimaflow-root>/references/sdd-router-mode-boundaries.md`。`<zimaflow-root>` 是宿主入口提供的只读逻辑能力根，不是开发机绝对路径。

## Quick Decision：三档模式判断表（quick / standard / full）

**先看这张表定档。默认从 quick 往上判，而不是从 full 往下砍**——zimaflow 的默认动作不是把所有事流程化。

| | **quick** | **standard** | **full** |
|---|---|---|---|
| 一句话 | 小到不值得立契约 | 真需求，但范围小 | 跨模块 / 高风险 / 改契约 |
| 典型触发 | 单文件低风险改动、小 bugfix、文案样式配置、一次性脚本、文档整理、纯问答 | 单一功能点、局部新增或扩展、老项目低风险叠加、参数字段纯增量扩展 | 跨模块、新接口/新表、schema / 权限 / 数据写入变更、跨系统集成、架构或路线变化 |
| 需求契约 | **不强制**，口头确认即可 | **最小字段 brief** | 完整 brief 或 PRD，须"已确认" |
| 路线决策 | 不需要 | 不需要 | `route-decision-recorder` 必需 |
| OpenSpec | **不生成** | **默认不生成三件套** | **默认入口**：proposal/design/tasks |
| 任务拆解 | 不需要（>3 步用 Light Work Items） | `task-planning` 轻量拆解 | `task-planning` + first slice |
| 实现纪律 | 就地改，能测就测 | Superpowers TDD | TDD + `openspec-superpowers-bridge` |
| 验证证据 | **说明验证方式 + 可复跑命令/结果** | 目标测试 + 关键路径 | 全量测试 + `spec-compliance-check` 报告落盘 |
| 收口 | **一句话收口**（改了什么/怎么验证/有无遗留） | `session-close-reconciler` | 完整收口 + handover + archive |
| 意图锁 | 口头一句话 | brief 中一行 | 契约中正式记录，下游必须对照 |

### 三条不能松的边界

- **quick 不是"不检查"**：风险判断、ZF-GR-005、ZF-GR-006 三档同样执行。quick **省掉的是**文档产物，不是判断动作。触发 schema / 权限 / 数据写入信号立即升级。
- **standard 不是"full 的缩水版堆文档"**：它的特征是**不写 OpenSpec 三件套**，而不是写轻一点的三件套。需要 proposal/design 才说得清 → 本来就该是 full。
- **full 才是 OpenSpec 的默认入口**：只有 full 默认生成三件套。

### 什么时候不生成 OpenSpec

- quick 档全部场景；standard 档默认不生成。
- 纯问答、代码解释、方案讨论：不进开发工作流。
- 一次性脚本、临时数据整理：要验证，不要 spec。
- 低风险文档维护（命名、目录、索引整理）。
- 问题排障根因未确认前；P0/P1 hotfix 止血阶段。

### 升级 / 降级规则

- **升级随时可发生**，不需要重走路由：quick→standard（超出单文件/多步骤）、standard→full（触发 ZF-GR-006 / 跨模块 / 需留审查记录）、任意档→full（资损/隐私/合规/核心数据）。
- **降级必须显式说明理由**，写进「不升完整模式理由」。**不允许因为**"想快点"而降级，只允许因为"重新评估后确认风险确实低"。
- **拿不准时优先 standard**：quick 容易漏证据，full 容易压垮小需求。

细则与 6 条反例（"就加个字段"其实是改 schema 等）见 `references/sdd-router-mode-boundaries.md`。

## 执行步骤

### Step 1：识别项目

先在目标代码仓运行只读项目解析：

```bash
cd <候选代码仓>
zimaflow project show --json
```

从稳定 JSON 读取 `project_name`、`code_root`、`docs_root`、`docs_root_source` 和 `initialized`，后续统一使用这组最终值。用户明确点名其他项目且当前不在该仓时，使用 `zimaflow recall --project <项目名>` 从用户级 `~/.zimaflow/projects.yaml` 定位；不要直接解析该文件。

若 `initialized=false`，建议运行 `zimaflow project init` 生成仓库可提交的 `.zimaflow/project.yaml` 与默认 `docs/zimaflow`。用户可以暂时跳过；不得静默创建项目配置，也不得假设私人知识库目录。

### Step 1.5：检查 zimaflow 初始化状态

```bash
cd <code_repo>
[ -d "openspec" ] && echo "✅ openspec/" || echo "❌ openspec/"
[ -f "openspec/config.yaml" ] && grep -q "^context:" "openspec/config.yaml" && echo "✅ config.yaml" || echo "❌ config.yaml"
[ -f ".claude/rules/openspec-config-awareness.md" ] || [ -f ".codex/rules/openspec-config-awareness.md" ] && echo "✅ Bridge Rule" || echo "❌ Bridge Rule"
```

- 全通过 → 继续 Step 2。
- 有缺失 → **不要静默执行 `openspec init`**，也不要直接进入定档。向用户说明缺什么，给两个选项：① 现在跑 `installer`（推荐，完成后回到 Step 2）；② 跳过并标记 `⚠️ 未初始化路径`，在 handover 中记录。

缺失的后果要讲清楚：没有 OpenSpec 基础设施则 full 档的 propose/apply/archive 无法执行；没有 Bridge Rule 则 AI 不读项目约束、spec 质量不可控。

### Step 2：加载上下文

**先读 thin context index**（存在则只读 index，按需选 1-3 个文档，不要因为 index 存在就全量加载）：

```bash
[ -f "<docs_root>/.zimaflow/context-index.yaml" ] && cat "<docs_root>/.zimaflow/context-index.yaml"
```

index 缺失且是老项目 / 用户说"接手老项目、项目考古、梳理架构"→ 建议先跑 `legacy-project-onboarding`；小修或紧急修复可跳过，但在 handover 记待补。新项目或简单任务不阻断，标记"无 / 不适用"。

**Cross-Session Continuity 恢复路径**：用户说"继续上次 / 接着做 / 出差回来 / 捡一下项目 / 恢复一下"时，优先走恢复路径，不要先按新需求路由。

```bash
cd <code_repo> && zimaflow recall
# 或无需 cd 时：
zimaflow recall --project <项目名>
```

按 `next_action` 决定：`continue` → 读 state + handover 恢复；`run_tests` → 先重跑验证；`refresh_handover` → 先刷新交接；`need_manual_confirmation` → 说明信息不足待确认；`no_active_change` → 继续 Step 3。

同时检查未完成的 handover（"遗留与下一步"非空）和未关闭的 state（`phase` 不是 `closed`），发现时先问用户"继续这个还是开新的"；选新需求时不要改动旧 state。

### Step 2.5：知识锚点预加载

按 `<zimaflow-root>/references/knowledge-anchor-guide.md` 的锚点规则，用你自己的锚点表与需求、项目文档摘要、最近 handover 做语义匹配。命中高信号锚点时加载对应 knowledge ID 条目，**最多 3 条**，优先最高风险维度；加载后通过 `zimaflow knowledge-record` 追加 `loaded` 事件到全局 usage ledger，不直接编辑能力根内的历史 JSONL。触碰高风险主题但无对应锚点时，输出 Learn 候选。

```bash
zimaflow knowledge-record \
  --knowledge-id <id> --event-type loaded \
  --project <project> --session <summary> --stage routing \
  --trigger <matched-anchor> --reason <why-loaded> --json
```

### Step 3：识别项目协作模式

先定项目语境，别把公司项目的规则默认套到个人小项目。

| 协作模式 | 典型信号 | 默认扩展 |
|---------|---------|---------|
| 个人小项目 | 个人维护、无固定测试角色、无多环境 | 无协作扩展 |
| 团队协作项目 | 多人开发、需要交接、可能有 review | handover、回归说明、协作记录 |
| 公司多环境项目 | dev/uat/prod、测试同学/联调验收、固定分支流、配置中心或发布审批 | 多环境发布、分支流、联调/UAT 记录、测试阻断记录 |

注册表或项目文档已声明则优先采用；否则推断并标注"推断"。拿不准不要静默升级到公司多环境项目，最多标"团队协作项目（待确认）"。

扩展开关明细见 `references/sdd-router-mode-boundaries.md` 第九节。

### Step 4：识别需求形态

需求形态影响**必须加载的上下文**，不直接等于档位。

| 需求形态 | 判断信号 |
|---------|---------|
| 小修小补 | 单点 bug、小样式、小配置、小文案、局部函数调整 |
| 老项目叠加功能 | 在已有系统上新增页面/接口/菜单/权限/配置 |
| 产品型界面/流程 | 新页面、新一级菜单、新流程向导、多状态 UI |
| 跨系统/第三方集成 | 外部 API、账号映射、token/key/secret、回调、外部契约 |
| 架构或产品路线变化 | 技术路线、模块边界、数据模型、产品范围变化 |
| 问题排障 / 故障定位 | 报错、测试失败、线上异常、无法复现、"看下为什么" |
| 紧急热修复 | 线上故障、阻断发布、要求先止血 |
| 需求变更 | 在已有契约/decision/spec/tasks/实现中追加、撤销或改写 |

**排障先于修复**：根因未确认前不进 task-planning / requirement-contract / OpenSpec，先用 `superpowers:systematic-debugging`。

**hotfix 严重度分档（P0/P1/P2 hotfix severity）**：P0 完全不可用 → 先止血再定位；P1 部分功能炸 → 快速修复但补最小记录；P2 边缘问题 → 不当热修复，退回正常路由。P0/P1 事后必须补 handover 与 learn 候选。

> ⚠️ hotfix 严重度与 Step 5.5 的 change impact P1/P2/P3 是**两套独立维度**，不要混用：前者衡量线上影响多严重，后者衡量哪个已确认产物失效。

各形态的特别规则见 `references/sdd-router-mode-boundaries.md` 第六、七节。

### Step 5：判断需求风险与复杂度

**先看风险，再看复杂度。** 快速判断用这四问：

1. 是否影响真实用户或线上系统？
2. 是否涉及数据写入、删除、接口签名变更？
3. 是否会有多人接手这段代码？
4. 是否涉及资损、隐私、合规、核心数据？

粗略定档：低风险 + 低复杂度 → quick / standard；中高复杂度 → full；高风险 → 至少 full。拿不准向上升级。

完整的七维复杂度表见 `references/sdd-router-mode-boundaries.md` 第五节。

### Step 5.1：可选代码图谱风险证据

不默认画图。满足任一条件时才启用（用户点名了具体模块/函数/接口/表/状态字段；Step 5 判为中高风险但影响面不清；需求形态是老项目叠加、跨系统集成、架构变化、核心数据写入或权限相关）。

用 `codebase-memory-mcp` 查询影响面，输出 1-3 条短结论 + 限制说明；MCP 不可用时不阻断，标记"不可用（原因）"。需要可视化时才走 `code-graph-to-diagram`。

### Step 5.2：证据边界（ZF-GR-005）

核心规则：**联想用于搜索，引用用于决策**。

- **允许**：用同义词、命名习惯做**搜索词扩展**定位候选文件；标注"候选落点 / 待验证"；把不确定的写成"AI 推断 / 待确认"。
- **禁止**：因为"看起来类似"就扩大需求/交互/实现范围或验收标准；因为同类功能存在就默认本轮也要改；把搜索命中的相似代码当业务决策依据。

决策证据只接受：需求契约原文、用户原话、设计稿标注/原型评审 notes、代码与测试事实。**显式 AI 假设只能进入"假设与默认值 / 待确认"，不能当作已确认范围。**

### Step 5.3：高风险契约升级（ZF-GR-006）

命中 **schema / 权限 / 数据写入** 任一信号时，默认升级到 full 或回退上游：

| 信号 | 例子 | 路由影响 |
|------|------|---------|
| schema | 表结构、迁移、DTO/序列化字段、配置结构 | 新需求至少 full；已有工作回到 contract / decision / OpenSpec review |
| 权限 / 鉴权 | 权限判断、鉴权中间件、token/session、角色校验 | 默认 full，写清身份字段、安全边界、验收标准 |
| 数据写入 | 写库、删库、批量更新、幂等键、事务边界 | 默认 full；删除/批量更新要求影响面和回滚说明 |

紧急热修复可先止血，但 P0/P1 后必须在 handover 补记命中信号、临时处理、影响面、验证方式。

### Step 5.5：判断需求变更影响级别

新需求且无已确认产物需变更 → 输出"不适用"。否则判断 **change impact P1/P2/P3**（不是任务优先级）：

- **P1**：只影响任务、局部实现、测试补充 → 当前阶段内处理。
- **P2**：影响 contract / Decision / prototype notes / OpenSpec 三件套任一 → 回到受影响产物重新确认。
- **P3**：影响产品范围、架构、数据模型、权限、敏感数据、计费、跨系统或发布策略 → 回到 route-decision-recorder / OpenSpec review，必要时拆新 change。

判断原则：**先看哪个已确认产物会失效，再看代码改动大小**。拿不准按 P2 处理。

### Step 5.6：纠偏 / rewind 识别

用户不是在追加需求，而是在**否定或回退当前理解/产物**时，必须回到上游产物就地改，**不能当成新需求重走一遍**。

触发信号："不是这个意思"、"你理解错了"、"回到上一版"、"先撤回"、"改一下范围"、"刚才那步走偏了"。

回退落点：契约起草中 → 改本轮契约；decision 已确认 → 改本轮 Decision；OpenSpec 后 → 修订三件套（改动大按 P3 拆新 change）；实现中 → 回到最近失效的上游产物。

规则：复用已有 change / 契约 / state 就地修订，`phase` 回退到对应阶段，**不创建平行的新 change_id**。如果用户其实是想在保留当前产物基础上叠加，那不是 rewind。

### Step 6：输出定档建议

回到顶部 **Quick Decision** 表定档，然后按下方模板输出路由结果，等待用户确认。

**不升完整模式理由**：建议 quick / standard / 排障 / hotfix / 原型先行时，必须说明为什么不用 full，避免用户误以为默认动作是把所有事流程化。常见理由清单见 `references/sdd-router-mode-boundaries.md` 第八节。

## 路由结果

```markdown
## 路由结果

- 项目协作模式：个人小项目 / 团队协作项目 / 公司多环境项目（如为推断需标注）
- 需求形态：小修小补 / 老项目叠加功能 / 产品型界面流程 / 跨系统集成 / 架构或产品路线变化 / 问题排障 / 紧急热修复 / 需求变更
- 复杂度：低 / 中 / 高
- 风险：低 / 中 / 高
- 建议工作模式：quick / standard / full（旧名：轻量模式 = quick+standard，完整模式 = full）／ 问题排障 / 紧急热修复
- 定档依据：（一句话，为什么是这一档；触发了哪个信号）
- OpenSpec：不生成（quick） / 默认不生成（standard） / 生成三件套（full）
- 不升完整模式理由：不适用 / 纯问答不进流程 / 一次性脚本不进 OpenSpec / 低风险低复杂度 / hotfix 先止血 / 原型先探索 / 文档维护低风险 / 其他...
- 启用扩展：无 / 协作交接 / 多环境发布 / 联调UAT记录 / 测试阻断记录 / 产品原型评审
- 原型评审：不需要 / 建议启用（PRD-driven） / 建议启用（Idea-driven）
- Context Index：已读取 / 缺失建议 onboarding / 无或不适用
- 知识预加载：无 / 已加载 kf-...（触发锚点：...）
- 代码图证据：未启用 / 已查询 / 不可用（原因）
- 代码图结论：（如有，1-3 条）
- 代码图限制：（如有，静态图 / scope / 截断 / risk label 说明）
- ZF-GR-005 证据边界：未触发 / 已触发（已将联想降级为搜索词或待确认假设）
- 搜索词扩展：{如有，列出候选词和来源}
- ZF-GR-006 高风险契约升级：未触发 / 已触发（schema / 权限 / 数据写入）
- Change Impact：不适用 / P1 / P2 / P3（需求变更影响级别，判断哪个已确认产物失效）
- 纠偏/rewind：无 / 检测到（回退落点：requirement-contract / route-decision / OpenSpec change / implementation 上游产物）
- Hotfix 严重度：不适用 / P0 / P1 / P2（仅紧急热修复场景，衡量线上影响，与 Change Impact 是两套维度）
- 需求契约：已有 / 不强制（quick，口头确认） / 需生成 brief（最小字段） / 需生成 brief（完整） / 需生成 PRD
- 需求契约路径：（已确认后填入，未生成前留空）
- 下一步：systematic-debugging / requirement-contract / task-planning / route-decision-recorder / proto-review / 热修复流程 / installer
```

### Step 6.5：需求契约 Gate

**必经的是需求契约，不是完整 PRD。**

判断是否已有可用契约：用户已提供 PRD/brief/外部链接，或项目文档目录下有未过期且用户确认沿用的契约 → 视为"已有"，记录路径交给 `requirement-contract` 确认时效，无需重写。

按档位决定契约要求：

| 档位 | 契约要求 |
|------|---------|
| quick | **不强制落盘**。口头确认三件事即可：本轮目的（意图锁一句话）、改动范围、怎么算做完。用户要留痕可写最小字段 brief，但这是可选项不是 Gate |
| standard | 最小字段 brief（意图锁 / 范围 / 不做什么 / 怎么算做完），按需补全 |
| full | 完整 brief 或 PRD |

升级到 PRD 的信号：产品型界面/多状态 UI/多角色协作、涉及权限计费敏感信息、团队协作或公司多环境项目、用户明确要求。拿不准先 brief，可后续升级，不强制一步到位。

**Gate**：`requirement-contract` 状态必须"已确认"才能进 Step 7。

Gate 豁免：**quick 档**（口头确认即可）、**问题排障**（根因未确认前）、**紧急热修复**（止血优先）。

**豁免的是**契约落盘，**不是**风险判断——quick 同样要走完 Step 5、5.2、5.3；触发高风险信号立即升级并回到本 Gate。

### Step 7：移交下一阶段

**前置条件**：standard / full 档必须有对应契约状态"已确认"；quick 档完成口头确认即可；排障与 hotfix 按各自豁免路径处理。

- **full + 原型评审** → `route-decision-recorder`，传项目名、代码/文档路径、需求描述、所选模式、契约路径、原型评审模式和触发原因；决策确认后进 `proto-review`
- **full + 不启用原型** → `route-decision-recorder`，传项目名、代码/文档路径、需求描述、所选模式、契约路径
- **quick / standard + 用户要求原型** → 先 `proto-review` 生成探索原型，评审后回 `task-planning`
- **standard** → `task-planning`，传项目名、代码/文档路径、需求描述、所选模式、协作模式、需求形态、启用扩展、契约路径
- **quick** → 通常直接实现，不必先拆任务；超过 3 个子步骤时交 `task-planning` 建 Light Work Items
- **问题排障** → `superpowers:systematic-debugging`，传问题现象、已知错误、复现线索；根因确认后回本 skill 二次定档
- **紧急热修复** → 直接进 Superpowers 修复，完成后触发 `handover-manager` 补记录

full 档若本轮 `Decisions/` 已存在且用户确认沿用，可跳过重写，直接把路径传给 `task-planning`。

## 常见陷阱

- **默认从 quick 往上判**，不是从 full 往下砍。zimaflow 的默认动作不是把所有事流程化。
- **解释不升级完整模式**：建议 quick / standard / 排障 / hotfix / 原型先行时必须说明理由；建议 full 时该字段写"不适用"。
- **排障先于修复**：根因未明就先 `systematic-debugging`，不要把"看起来像 bug"直接路由成 task-planning 或 OpenSpec。
- **纠偏是回退不是新开**：用户否定当前理解时回到失效的上游产物就地修订，复用已有 change/契约/state，不新建 change_id。
- **两套 P 分级不混用**：Change Impact 管回退落点，Hotfix 严重度管止血策略，输出时分别标注。
- **需求形态不等于档位**：老项目叠加功能只是触发参考实现检查；档位仍由风险和复杂度决定。
- **契约先于规划**：不允许纯口头需求直接进 `task-planning` / `route-decision-recorder` / OpenSpec——但 quick 档的口头确认本身就是它这一档的契约形态。

## 注意事项

- 不要在这个阶段写代码或生成 spec
- 不要跳过项目识别直接开始
- 不要在 full 档直接把用户送进 `/opsx:propose`
- 不要在根因未明时承诺修复方案
- 不要在契约仍是"草稿"/"待确认"时移交下一阶段（排障和 hotfix 除外）
- 用户说"继续上次的"但没指定项目时，读注册表中所有活跃项目的最新 handover 列出选项
