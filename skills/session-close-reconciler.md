---
name: session-close-reconciler
description: >
  Session 收口文档对账。在开发 session 接近结束时触发，检查本轮改动是否完成了必要的文档同步。
  输出一份 closing checklist，区分已完成/建议补充/明确缺失。
  触发词：总结一下、收口、收尾、完成、完结、结束、已 push、push 完了、提交完成、工作树干净、两边都 clean、本 session 完结、看看还有没有遗漏、准备结束、对账、reconcile、检查文档。
  应在 handover-manager 生成交接文档之前触发——先对账再交接。
---

# Session Close Reconciler — 收口文档对账

## 职责

检查本轮 session 的改动是否已完成必要的文档同步，输出一份 closing checklist。这是"检查与提醒"，不是自动改文档的脚本。

## 与 handover-manager 的关系

执行顺序：**session-close-reconciler（含 learn 候选扫描 + knowledge usage review）→ handover-manager → learn 写入确认**

- reconciler 先跑：对账文档完整性，同时判断本轮是否命中 learn 高置信信号，并复核本轮 loaded/applied/challenged 的 knowledge ID
- handover-manager 后跑：生成交接文档时可以把 reconciler 发现的未补缺口和候选 lesson 记入"遗留与下一步/待沉淀经验"
- learn 最后跑：对 reconciler 或 handover 识别出的候选 lesson 做用户确认和写入

reconciler 不替代 handover-manager，它们检查的维度不同：
- reconciler 检查：**文档是否与改动同步**（向后看——这轮该更新的文档更新了吗）
- reconciler 同时检查：**是否应该触发 learn 候选扫描**（向内看——这轮有没有值得沉淀的经验）
- handover-manager 检查：**下一轮需要什么信息**（向前看——接手的人需要知道什么）

## 触发时机

1. 用户说"总结一下"、"看还有没有遗漏"、"准备结束"、"收口"等
2. 用户触发 handover-manager 时，handover-manager 应先触发 reconciler
3. 用户手动说"reconcile"或"对账"
4. 用户表达 session 要结束或工程状态已完成，例如："收尾"、"完成"、"完结"、"结束"、"已 push"、"push 完了"、"提交完成"、"工作树干净"、"两边都 clean"、"本 session 完结"

## 最终回复 Gate

在回答"完成"、"收尾"、"本 session 完结"或类似结束语之前，AI 必须先运行 session-close-reconciler，不能仅凭 git/test/push 状态直接宣布 session 结束。

以下状态只代表工程状态完成，不代表 zimaflow session 收口完成：

- `git status` clean / 工作树干净 / 两边都 clean
- tests passed / verify passed
- commit 已完成 / push 已完成 / PR 已创建

只有在 reconciler 输出收口检查清单，并处理或记录其中的 ❌ 明确缺失、📝 建议补充、🧠 Learn 候选后，AI 才能在最终回复中表达"本轮收口完整"或"本 session 可以完结"。

## 输入

reconciler 需要从当前 session 上下文中获取：
- 本轮改动了哪些文件（`git diff --name-only` 或 session 中的改动记录）
- 当前项目信息（从 PROJECT_REGISTRY 获取 `code_repo` 和 `docs_dir`）
- 当前工作模式（完整 / 轻量）
- 本轮是否读取或应用过 `knowledge-anchor-map.md` / `lessons-common.md` / 项目 `lessons.md`

## 执行步骤

### Step 1：收集本轮改动事实

```bash
# 代码仓改动
cd <code_repo>
git diff --name-only HEAD~$(git log --oneline --since="today" | wc -l) HEAD 2>/dev/null || git diff --name-only
git status --short

# 如果是 zimaflow 自身或 skill 类项目
ls -lt <改动文件> 2>/dev/null
```

同时回顾本次 session 对话中明确提到的改动（AI 应从对话上下文中提取，不仅靠 git）。

将改动分类：

| 改动类型 | 判断依据 |
|---------|---------|
| 产品功能改动 | 业务逻辑代码变更（非纯重构、非纯测试） |
| 产品定位/范围变化 | 讨论中涉及"不做 X 了"、"改方向"、"扩大/缩小范围" |
| Skill / 工作流 / rule 改动 | `.claude/`、`.codex/`、`skills/`、`SKILL.md` 等文件变更 |
| OpenSpec 路线/切片调整 | `openspec/changes/` 或 `Decisions/` 相关讨论 |
| 踩坑/经验产生 | session 中有调试循环、方向返工、用户纠正 |
| hotfix / incident 修复 | 本轮走了紧急热修复（hotfix 严重度 P0/P1），先止血或跳过完整流程修复线上问题 |
| rewind / 需求纠偏 | 本轮回退了已确认的 contract / Decision / OpenSpec / tasks / implementation（用户说"理解错了/回到上一版/改范围/先撤回"等） |
| secrets 敏感配置风险 | 本轮新增/改动 api_key/token/secret/password/private_key 等敏感配置，或疑似密钥进入版本库 |
| learn 高置信信号 | 用户纠正关键判断、真源/runtime 路径误用、公开内容脱敏或状态修正、规则直接回写到 Skill、同类问题重复出现 |
| knowledge usage | 本轮读取、引用、应用或质疑了带 `ID` 的 lesson/pattern |

### Step 2：加载 doc-sync matrix

读取文档同步矩阵：
```bash
cat "$ZIMAFLOW_HOME/references/doc-sync-matrix.md"
```

根据矩阵，对每种改动类型查出"至少要更新哪些文档"。

### Step 3：逐项核对

对矩阵中要求的每份文档，检查是否已更新：

**检查方法**（按文档类型）：

| 目标文档 | 检查方式 |
|---------|---------|
| `PROGRESS.md` | `git diff` 中是否包含该文件；或本 session 中是否有对该文件的写入 |
| `README.md`（项目或 skill 的） | 同上 |
| `Decisions/` 下的决策文档 | `ls <docs_dir>/Decisions/` 中是否有今天的新文件或修改 |
| `lessons-common.md` / 项目 `lessons.md` | 是否在本 session 中已触发 learn 并写入 |
| `knowledge-usage-ledger.jsonl` | 如果本轮按锚点加载、引用、应用或质疑知识，是否已追加 usage 事件 |
| `openspec/specs/` | 如果有 archive 操作，specs 是否已更新 |
| `config.yaml` | 如果改了约束类规则，是否同步 |
| `.zimaflow-state.yaml` | 如果本轮推进了 OpenSpec change 阶段，phase、verify、archive、handover 是否与实际状态一致 |

### Step 3.2：Guardrail 收口核对（hotfix / rewind / secrets）

如果 Step 1 识别出 hotfix、rewind 或 secrets 命中，按 doc-sync-matrix 对应行逐项核对。这三类只检查、只提醒、只记入交接项，不自动写文档、不自动改密钥、不自动 revoke。

**hotfix / incident 修复**：

- 是否有事故记录：`INCIDENT/` 事故文档，或 handover"遗留与下一步" / `PROGRESS.md` 中记录了事故现象、根因、修复摘要、验证结果。
- P0/P1 是否列出了 24h 内待补项：CHANGE / SUMMARY / tests / LESSONS 提名。
- 缺记录 → ❌ 明确缺失（先止血后必须留痕）；有止血但待补项未列 → 📝 建议补充。

**rewind / 需求纠偏**：

- 是否记录了"被回退的产物、回退原因、当前有效版本"。
- 被回退的 contract / Decision / OpenSpec / tasks 是否就地修订（而非新建平行产物导致新旧版本并存）。
- 缺"当前有效版本"标注 → ❌ 明确缺失（下个 session 会分不清哪版有效）；仅缺回退原因 → 📝 建议补充。

**secrets 敏感配置风险**：

- 核对时**禁止把密钥值写入 checklist 或任何文档**，只引用 `path:line`。
- 是否记录了：命中事实、处理动作、是否需要 revoke/rotate、是否已补 `.env.example` / `.gitignore`。
- 若疑似真实密钥已进入 git 历史 → ❌ 明确缺失，并建议用户执行 revoke/rotate + 补 `.env.example` / `.gitignore`（reconciler 只提醒，不代为 revoke）。
- 已确认是占位符 / env 间接引用（误报）→ 记为 ✅，说明已核实非真实密钥。

输出模板：

```markdown
### 🛡️ Guardrail 收口
- hotfix：INCIDENT/PROGRESS/handover 已记录 / ❌ 缺事故记录 / 📝 24h 待补项未列
- rewind：当前有效产物已标注（{路径}）/ ❌ 未标注当前有效版本
- secrets：{path:line} 已记录处理动作 + revoke/rotate 建议 / ✅ 核实为占位符 / ❌ 疑似真实密钥入库需 rotate（不写密钥值）
```

### Step 3.3：Zimaflow State Review

如果本轮涉及 OpenSpec change，读取：

```bash
cat openspec/changes/<name>/.zimaflow-state.yaml
```

按 `$ZIMAFLOW_HOME/references/Design-Zimaflow-State.md` 核对：

- `phase` 是否与实际进度一致
- 已确认需求契约、Decisions、原型评审记录、proposal/design/tasks 路径是否仍存在
- `implementation` 是否记录 branch/worktree 隔离
- `verification` 是否记录 `/opsx:verify` 和全量测试结果
- archive 后是否写入 `archive.status` 和 `archive.docs_synced`
- handover 生成后是否写入 `handover.latest_path`

state 缺失或明显过期时，列为 📝 建议补充；如果缺失会导致无法判断 verify/archive 状态，列为 ❌ 明确缺失。

### Step 3.4：Knowledge Usage Review

在 Learn 候选扫描前，复核本轮知识使用情况：

1. 检查本轮是否读取过 `$ZIMAFLOW_HOME/references/knowledge-anchor-map.md`、`$ZIMAFLOW_HOME/references/lessons-common.md` 或项目 `lessons.md`。
2. 列出本轮涉及的 knowledge ID，按 `loaded` / `cited` / `applied` / `challenged` 分类。
3. 检查 `$ZIMAFLOW_HOME/references/knowledge-usage-ledger.jsonl` 是否已有对应事件。
4. 如果缺事件，把它列为 📝 建议补充，不直接写入。
5. 如果发现知识不适用或过期，把它列为 Learn 候选或 stale-review 候选。

输出模板：

```markdown
### 🧾 Knowledge Usage
- 已记录：kf-...（applied，stage: planning）
- 建议补记：kf-...（loaded，触发锚点：...）
- 待复核：kf-...（challenged，原因：...）
```

### Step 3.5：Learn 候选扫描 Gate

在输出 checklist 前，必须判断本轮是否命中 learn 高置信信号。

高置信信号包括：

| 信号 | 例子 | 处理 |
|------|------|------|
| 用户纠正了 AI 的关键流程判断 | "不应该改 runtime，应该改 source"、"团队项目必须脱敏" | 输出候选 lesson |
| 真源/runtime 或 source/dist 路径误用 | 直接改了生成副本，后来同步回真源 | 输出候选 lesson |
| 公开内容涉及脱敏、安全边界或状态修正 | 验收环境 改为已上线、删除具体项目名/第三方名 | 输出候选 lesson |
| 规则被直接回写到 Skill | 直接修改 sdd-router、sync-agent-skills、reconciler 等 | 输出候选 lesson，标注"已直接回写规则，缺 lesson 记录" |
| 同类问题在本轮或近期重复出现 | 多次漏掉真源优先、脱敏、learn 触发 | 输出候选 lesson 或 pattern |

输出要求：

- 如果命中，列出最多 3 条候选 lesson，每条包含：主题、触发证据、建议级别、建议写入位置。
- 如果未命中，必须在 checklist 中写明：`learn 候选扫描：未发现高置信候选`。
- 如果本轮已经直接改了 Skill/README 规则，但没有写 lessons，不能标为"已完成"；至少标为"建议补充"。
- 不自动写入 lesson。只输出候选，等用户确认后再交给 learn Skill 写入。

候选输出模板：

```markdown
### 🧠 Learn 候选
- 候选 1：{主题}
  - 触发证据：{本轮哪件事说明它值得沉淀}
  - 建议级别：lesson / pattern / rule
  - 建议写入：项目 lessons.md / lessons-common.md / 回写 Skill
```

### Step 4：输出收口检查清单

以三级状态输出结果：

```markdown
## 收口检查清单

### ✅ 已完成
- （列出本轮已同步的文档项）

### 📝 建议补充
- （改动不大或非关键路径，但最好补一下的文档项）
- （附简要说明：建议更新什么内容）

### ❌ 明确缺失
- （按矩阵应该更新但确实没更新的文档项）
- （附具体说明：缺什么、影响是什么）

### 🧠 Learn 候选
- （命中高置信信号时列出候选；未命中时写"未发现高置信候选"）

### 🧾 Knowledge Usage
- （列出本轮知识 ID 的 loaded/cited/applied/challenged 状态；无则写"本轮未发现知识使用记录"）

### 🛡️ Guardrail 收口
- （本轮涉及 hotfix / rewind / secrets 时列出核对结果；密钥只写 path:line、不写值；均无则写"本轮无 hotfix / rewind / secrets 收口项"）

---
**结论**：{本轮收口完整 / 有 N 项建议补充 / 有 N 项明确缺失}
```

### Step 5：等待用户决策

- 如果有 ❌ 明确缺失项 → 默认建议"现在补"，补完后再生成 handover；只有用户明确选择跳过时，才记入 handover 遗留或继续后续流程
- 如果只有 📝 建议补充 → 告知用户，由用户决定现在补、记入 handover 遗留，或本轮不处理
- 如果有 🧠 Learn 候选 → 只列出候选，不自动写入 lessons；等待用户确认后再交给 learn Skill 写入
- 如果有 🧾 Knowledge Usage 建议补记 → 询问用户是否补记 usage ledger；补记只追加 JSONL，不修改 lesson 正文
- 如果全部 ✅ → 告知"本轮收口完整"，继续生成 handover

用户决策后：
- 选择"现在补" → 协助补充对应文档，补完后重新跑一次 checklist（可选）
- 选择"记入遗留" → 将缺失项传递给 handover-manager，写入"遗留与下一步"
- 选择"不用了" → 尊重用户决定，继续后续流程

## 特殊场景

### 没有产品功能改动的 session

有些 session 只是讨论、设计、文档整理，没有代码改动。此时：
- 跳过代码相关的检查项
- 仅检查讨论中是否产生了需要落文档的决策或经验

### zimaflow 自身的改动

当改动对象是 zimaflow 本身（skill 文件、references、README）：
- 检查 README 的 Skill 列表和版本记录是否同步
- 检查公开路线图或 issue 是否需要更新
- 检查 references/ 下是否有新增文件未被其他 Skill 引用
- 必须执行 Learn 候选扫描 Gate。若本轮是因为流程缺口、用户纠正或真实踩坑而修改 Skill，至少输出 1 条候选 lesson；如果没有候选，说明为什么这只是普通维护。
- 如果本轮新增或修改 `knowledge-anchor-map.md`、`knowledge-usage-guide.md`、`knowledge-usage-ledger.jsonl` 或 lesson `ID`，必须检查 README 和 doc-sync matrix 是否同步。

### 全部通过的情况

如果所有检查项都是 ✅，明确输出：

> ✅ 本轮收口完整，所有文档已同步。可以直接生成 handover。

不要为了显得有用而硬凑建议。

## 原则

- **检查不改写**：reconciler 只负责发现缺口并提醒，不替用户改文档。用户说"帮我补"时才动手。
- **最终回复 Gate**：用户说"完成/收尾/本 session 完结"前，必须先运行 reconciler；git clean、tests passed、pushed 只是工程完成信号，不是 zimaflow session 收口完成信号。
- **learn 扫描不写入**：reconciler 只输出候选 lesson，不直接写 lessons。写入必须由 learn Skill 在用户确认后执行。
- **usage review 不改正文**：reconciler 可以建议补记 ledger，但不能直接修改 lesson 内容或级别。
- **矩阵驱动**：所有检查项来自 doc-sync-matrix.md，不凭 AI 自由发挥。如果矩阵没覆盖的改动类型，标注"矩阵未覆盖，建议人工判断"。
- **不阻断流程**：即使有缺失项，用户说"不用管"就不管。reconciler 是提醒，不是 gate。
- **Guardrail 只提醒不代办**：hotfix / rewind / secrets 三类收口项，reconciler 只检查、提醒、记入交接；不自动写 INCIDENT、不自动改密钥、不代为 revoke/rotate，是否处理由用户决定。
- **密钥值绝不外泄**：secrets 命中只在 checklist 和 handover 中引用 `path:line`，任何情况下都不把密钥原文写入 checklist、handover 或 lessons。
- **与 handover 串联不重叠**：reconciler 检查"文档同步了吗"，handover 检查"下一轮需要什么"。两者有交集（都看改动），但视角不同。
