---
name: session-close-reconciler
description: >
  Session 收口文档对账。在开发 session 接近结束时触发，检查本轮改动是否完成了必要的文档同步。 输出一份 closing
  checklist，区分已完成/建议补充/明确缺失。 触发词：总结一下、收口、收尾、完成、完结、结束、已 push、push
  完了、提交完成、工作树干净、两边都 clean、本 session 完结、看看还有没有遗漏、准备结束、对账、reconcile、检查文档。 应在
  handover-manager 生成交接文档之前触发——先对账再交接。
sync: false
sync_reason: 有意不同步：套件内部子 Skill，由 Zimaflow 主入口路由；宿主 adapter 从独立源码仓生成或注入同一能力根
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

## Final Response Gate

在回答"完成"、"收尾"、"本 session 完结"或类似结束语之前，AI 必须先运行 session-close-reconciler，不能仅凭 git/test/push 状态直接宣布 session 结束。

以下状态只代表工程状态完成，不代表 zimaflow session 收口完成：

- `git status` clean / 工作树干净 / 两边都 clean
- tests passed / verify passed
- commit 已完成 / push 已完成 / PR 已创建

只有在 reconciler 输出 Closing Checklist，并处理或记录其中的 ❌ 明确缺失、📝 建议补充、🧠 Learn 候选后，AI 才能在 final response 中表达"本轮收口完整"或"本 session 可以完结"。

## 输入

reconciler 需要从当前 session 上下文中获取：
- 本轮改动了哪些文件（`git diff --name-only` 或 session 中的改动记录）
- 当前项目信息（先运行 `zimaflow project show --json`，使用最终 `code_root` 和 `docs_root`）
- 当前工作模式（完整 / 轻量）
- 本轮是否读取或应用过锚点表 / `lessons-common.md` / 项目 `lessons.md`

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
| Skill / workflow / rule 改动 | `.claude/`、`.codex/`、`skills/`、`SKILL.md` 等文件变更 |
| OpenSpec 路线/切片调整 | `openspec/changes/` 或 `Decisions/` 相关讨论 |
| OpenSpec tasks 状态漂移 | 存在 Superpowers plan / 实际代码改动 / 测试证据，但 `openspec/changes/<name>/tasks.md` 仍明显未勾选或状态滞后 |
| Intent Lock / 契约持续对照风险 | 已确认契约存在意图锁，但 Decision / tasks / OpenSpec 范围实质性变化，或规划文档没有对照意图锁 |
| 踩坑/经验产生 | session 中有调试循环、方向返工、用户纠正 |
| hotfix / incident 修复 | 本轮走了紧急热修复（hotfix 严重度 P0/P1），先止血或跳过完整流程修复线上问题 |
| rewind / 需求纠偏 | 本轮回退了已确认的 contract / Decision / OpenSpec / tasks / implementation（用户说"理解错了/回到上一版/改范围/先撤回"等） |
| secrets_scan 命中或敏感配置风险 | `zimaflow close` 报 `secrets_scan: suspected`，或本轮新增/改动 api_key/token/secret/password/private_key 等敏感配置 |
| release readiness / 发布前检查 | 用户表达准备发布、上线、发版、交付、打 tag、发布到生产等意图 |
| learn 高置信信号 | 用户纠正关键判断、真源/runtime 路径误用、公开内容脱敏或状态修正、规则直接回写到 Skill、同类问题重复出现 |
| knowledge usage | 本轮读取、引用、应用或质疑了带 `ID` 的 lesson/pattern |
| code graph evidence | 本轮使用了 `codebase-memory-mcp` / `code-graph-to-diagram` 查询、生成图表或引用代码图结论 |
| light work items | 轻量模式启用了 `references/Design-Light-Work-Items.md`，或本轮存在 `work-items.yaml` / handover `## Work Items` 表格 |

### Step 2：加载 doc-sync matrix

读取文档同步矩阵：
```bash
cat "<zimaflow-root>/references/doc-sync-matrix.md"
```

根据矩阵，对每种改动类型查出"至少要更新哪些文档"。

同时读取 Guardrails Catalog：

```bash
cat "<zimaflow-root>/references/guardrails.yaml"
```

Guardrails Catalog 是收口时统一规则 ID 与报告措辞的单一真源。reconciler 只做 soft gate 核对，不自动阻断、不自动回滚、不自动 revoke/rotate、不自动发布。

本 Skill 当前重点对照：

- `ZF-GR-001 requirement_contract_confirmed`
- `ZF-GR-002 intent_lock_alignment`
- `ZF-GR-004 secret_value_never_logged`

### Step 2.5：加载 Verification Evidence 字段契约

读取 `references/Design-Zimaflow-State.md` 中的 `Verification Evidence` 字段定义。reconciler 对验证状态的判断以 state/handover 中的最小字段为准：

- `opsx_verify`
- `full_tests`
- `last_command`
- `last_result`
- `evidence_path`
- `blocked_reason`
- `verified_at`

边界：

- 有 `verified_at` 但 `opsx_verify` 或 `full_tests` 不是 `passed`，不能视为完整验证通过。
- 有失败或阻塞时，必须能看到 `last_command` 和 `last_result`；阻塞还应有 `blocked_reason`。
- `evidence_path` 是报告、日志、截图或 CI 链接的路径/URL；reconciler 不要求长日志进入 handover。
- context-index 不能复制 Verification Evidence 正文或验证日志，只能保留 state / handover 路径和短 metadata。

### Step 3：逐项核对

对矩阵中要求的每份文档，检查是否已更新：

**检查方法**（按文档类型）：

| 目标文档 | 检查方式 |
|---------|---------|
| `PROGRESS.md` | `git diff` 中是否包含该文件；或本 session 中是否有对该文件的写入 |
| `README.md`（项目或 skill 的） | 同上 |
| `Decisions/` 下的决策文档 | `ls <docs_root>/Decisions/` 中是否有今天的新文件或修改 |
| `lessons-common.md` / 项目 `lessons.md` | 是否在本 session 中已触发 learn 并写入 |
| 全局 knowledge usage ledger | 如果本轮按锚点加载、引用、应用或质疑知识，是否已通过 `zimaflow knowledge-record` 追加 usage 事件 |
| `openspec/specs/` | 如果有 archive 操作，specs 是否已更新 |
| `config.yaml` | 如果改了约束类规则，是否同步 |
| `.zimaflow-state.yaml` | 如果本轮推进了 OpenSpec change 阶段，phase、verify、archive、handover 是否与实际状态一致 |
| 项目 `Reviews/` 下的 Spec Compliance Report（全量审查后） | 检查文件是否存在，以及 closing checklist / handover 是否链接该路径，而不是只写"合规检查：done"；每个 task 后的轻量检查不要求此项 |

### Step 3.2：Guardrail 收口核对（hotfix / rewind / secrets / release）

如果 Step 1 识别出 hotfix、rewind、secrets 命中或发布意图，按 doc-sync-matrix 对应行逐项核对。这几类只检查、只提醒、只记入交接项，不自动写文档、不自动改密钥、不自动 revoke、不自动发布、不自动打 tag、不自动改配置。

**hotfix / incident 修复**：

- 是否有事故记录：`INCIDENT/` 事故文档，或 handover"遗留与下一步" / `PROGRESS.md` 中记录了事故现象、根因、修复摘要、验证结果。
- P0/P1 是否列出了 24h 内待补项：CHANGE / SUMMARY / tests / LESSONS 提名。
- 缺记录 → ❌ 明确缺失（先止血后必须留痕）；有止血但待补项未列 → 📝 建议补充。

**rewind / 需求纠偏**：

- 是否记录了"被回退的产物、回退原因、当前有效版本"。
- 被回退的 contract / Decision / OpenSpec / tasks 是否就地修订（而非新建平行产物导致新旧版本并存）。
- 缺"当前有效版本"标注 → ❌ 明确缺失（下个 session 会分不清哪版有效）；仅缺回退原因 → 📝 建议补充。

**secrets_scan 命中或敏感配置风险**：

- 核对时**禁止把密钥值写入 checklist 或任何文档**，只引用 `path:line`。
- 是否记录了：命中事实、处理动作、是否需要 revoke/rotate、是否已补 `.env.example` / `.gitignore`。
- 若疑似真实密钥已进入 git 历史 → ❌ 明确缺失，并建议用户执行 revoke/rotate + 补 `.env.example` / `.gitignore`（reconciler 只提醒，不代为 revoke）。
- 已确认是占位符 / env 间接引用（误报）→ 记为 ✅，说明已核实非真实密钥。

**release readiness / 发布前检查**：

- 本轮有发布意图时，建议先运行或读取 `zimaflow release-check`（human 或 `--json`），把 `next_action` 记入收口结果。
- `next_action` 是 `ready` → 记为 ✅（发布前置就绪，仍需人工确认四问）。
- `next_action` 非 `ready` → 按缺口类别列入 checklist：`need_verify` / `need_archive` / `need_handover` / `need_manual_confirmation` 列为 📝 建议补充；`need_secret_review` 列为 ❌ 明确缺失（发布前必须处理密钥风险）。
- 四问（scope / verification / rollback / communication）只记录"待人工确认 / 已确认"，reconciler 不替用户回答，尤其 rollback 路径和 communication 对象/内容是否已备好。
- **禁止记录任何发布 token / secret 值**；secrets/readiness 缺口只记 `path:line` 或类别。
- reconciler 只提醒，不自动发布、不自动打 tag、不自动改发布配置。

输出模板：

```markdown
### 🛡️ Guardrail 收口
- hotfix：INCIDENT/PROGRESS/handover 已记录 / ❌ 缺事故记录 / 📝 24h 待补项未列
- rewind：当前有效产物已标注（{路径}）/ ❌ 未标注当前有效版本
- secrets：{path:line} 已记录处理动作 + revoke/rotate 建议 / ✅ 核实为占位符 / ❌ 疑似真实密钥入库需 rotate（不写密钥值）
- release：release-check next_action={ready/need_...} / 缺口已记（verify/archive/handover/secret review/manual）/ 四问待确认项={scope/verification/rollback/communication}（不记 token/secret 值）
```

### Step 3.3.1：Zimaflow State Review

如果本轮涉及 OpenSpec change，读取：

```bash
cat openspec/changes/<name>/.zimaflow-state.yaml
```

按 `references/Design-Zimaflow-State.md` 核对：

- `phase` 是否与实际进度一致
- 已确认需求契约、Decisions、prototype、proposal/design/tasks 路径是否仍存在
- `implementation` 是否记录 branch/worktree 隔离
- `verification` 是否记录 `openspec validate <change-name>` 和全量测试结果，以及 Verification Evidence 最小字段（`last_command`、`last_result`、`evidence_path`、`blocked_reason`、`verified_at`）
- archive 后是否写入 `archive.status` 和 `archive.docs_synced`
- handover 生成后是否写入 `handover.latest_path`

state 缺失或明显过期时，列为 📝 建议补充；如果缺失会导致无法判断 verify/archive 状态，列为 ❌ 明确缺失。

输出模板：

```markdown
### 🧪 Verification Evidence
- opsx_verify：passed / failed / blocked / not_run
- full_tests：passed / failed / blocked / not_run
- last_command：present / missing
- last_result：passed / failed / blocked / missing
- evidence_path：present / missing / not_applicable
- blocked_reason：present / missing / not_applicable
- 结论：verified / failed_needs_fix / blocked_needs_handover / evidence_incomplete
```

#### 验证状态必须上浮到顶部三级状态

Verification Evidence 不能只停留在本节。Closing Checklist 的核心意图是"防止只凭 tests passed 就宣布 session 完结"；如果验证真的失败了，却只写在中间某一节，顶部三级状态仍显示"0 项明确缺失"，这个意图就被架空了。

因此按下表强制上浮，**不得省略**：

| 验证状态 | 必须出现在 |
|----------|-----------|
| `full_tests=failed` 或 `opsx_verify=failed` | ❌ 明确缺失 |
| 结论为 `evidence_incomplete` | 📝 建议补充 |
| `full_tests=not_run` 或 `opsx_verify=not_run` | 📝 建议补充 |
| 缺少 `last_command` / `last_result` / 必要的 `evidence_path` | 📝 建议补充 |

**即使失败已归因为环境问题、隔离副作用、与本轮改动无关的既有失败，仍然必须上浮**；只是在条目中标注归因，例如：

```markdown
### ❌ 明确缺失
- 全量测试未通过：`pytest tests/ -q` → 1 failed（归因：worktree 目录名导致 test_paths.py 硬编码断言失败，非本轮回归）
```

不允许因为"不是本次引入的问题"就从顶部三级状态中省略。归因只影响处理方式，不影响是否可见。

边界：这仍是 soft check。上浮只是要求"必须显示"，不自动阻断流程、不自动写回文件、不自动修改测试；是否处理由用户决定。

### Step 3.3.2：OpenSpec tasks 状态同步核对（tasks sync drift）

如果本轮涉及 OpenSpec change，在 close 前核对 `tasks.md` 的勾选状态是否与实际完成情况一致：

```bash
grep -n '^[[:space:]]*- \[' openspec/changes/<name>/tasks.md
```

**术语区分：两类 drift 不是一回事**

| 术语 | 对象 | 检查方式 | 承接位置 |
|------|------|----------|----------|
| **artifact hash drift** | 契约 / decision / OpenSpec 三件套的文件内容 | SHA256 比对，看文件在交接后是否被改动 | CLI `zimaflow drift-check <change>` |
| **tasks sync drift**（本步骤） | `tasks.md` 的勾选状态 | 与 Superpowers plan 进度、代码改动、测试证据对照 | 规则层：`openspec-superpowers-bridge` Step 5.5 + 本步骤 |

前者回答"交接后文件被人改过吗"，后者回答"任务状态和实际做完的事对得上吗"。两者可以同时发生，也可以互不相干；本步骤只负责后者，不调用也不替代 `zimaflow drift-check`。

对照本轮的三类实际完成信号：Superpowers plan 执行进度、实际代码改动（`git diff --name-only`）、测试证据（`last_command` / `last_result` / `evidence_path`）。

判定：

- 实际已完成但 `tasks.md` 未勾选或状态滞后 → 列为 📝 建议补充；如果本轮准备进入 verify/archive 或对外交接，列为 ❌ 明确缺失（下个 session 会误判任务未完成）。
- `tasks.md` 已勾选但找不到对应代码改动或测试证据 → 列为 📝 建议补充，说明缺证据的是哪几项。
- 标记后要求人工确认是否同步，并记录同步依据：文件路径 / 测试结果 / handover 记录 / 用户确认。

`openspec-superpowers-bridge` Step 5.5 在进入验证前已做过一次同类检查；reconciler 这一步是 close 前的最后一道核对，覆盖"bridge 未触发"或"实现后又有新增改动"的情况。

边界：reconciler 只对比和提醒，**不自动勾选 `tasks.md`**、不自动改 spec、不自动推进 phase。

输出模板：

```markdown
### 🔀 OpenSpec Tasks Sync（tasks sync drift）
- tasks.md：{N} 项已勾选 / {M} 项未勾选
- 实际完成信号：plan={present/absent} / 代码改动={present/absent} / 测试证据={present/absent}
- 漂移：无 / 实际已完成但未勾选（{条目}）/ 已勾选但缺证据（{条目}）
- 同步依据：文件路径 / 测试结果 / handover 记录 / 用户确认 / 待人工确认
- 结论：aligned / needs_tasks_sync / needs_evidence / not_applicable
```

### Step 3.3.3：Work Items 核对

如果本轮轻量模式启用了 `references/Design-Light-Work-Items.md`，检查 `work-items.yaml` 或 handover 的 `## Work Items` 表格：

- `done` 项是否有 `evidence_path` 或等价证据，并记录 `verify_result`。
- `blocked` 项是否有 `blocked_reason` 和下一步。
- `doing` 项是否有明确下一步和负责人/执行方。
- `skipped` 项是否说明跳过原因，且没有被误报为完成。
- 台账是否声明不替代 handover；handover 仍应记录决策、上下文和恢复命令。

输出模板：

```markdown
### 📋 Work Items
- 台账：present / missing / not_applicable
- done 证据：ok / missing
- blocked 原因：ok / missing / not_applicable
- doing 下一步：ok / missing / not_applicable
- 结论：ready_to_continue / evidence_incomplete / blocked_needs_handover / not_applicable
```

### Step 3.3.4：Intent Lock / 契约持续对照

如果本轮涉及 requirement-contract、Decisions、task-planning 或 OpenSpec change，检查规划是否仍对齐需求契约中的 `意图锁`：

1. 读取已确认需求契约：
   - 如果缺 `意图锁` → 📝 建议补充；既有已确认契约不因缺字段自动失效。
   - 如果存在 `意图锁`，记录原文。
2. 检查下游规划文档：
   - `Decisions/` 是否有"意图锁对照"或等价说明。
   - tasks / task-planning 输出是否说明任务如何服务意图锁。
   - proposal.md / design.md 是否引用或复述意图锁。
3. 如果下游规划实质性扩大/缩小范围，但没有回到 requirement-contract 重新确认：
   - 列为 📝 建议补充；若会导致下个 session 分不清当前有效范围，列为 ❌ 明确缺失。
   - 必要时归入 `rewind / 需求纠偏`，要求标注当前有效版本。

输出模板：

```markdown
### 🧷 Intent Lock
- 契约：present / missing / not_applicable
- Decision 对照：ok / missing / stale / not_applicable
- tasks 对照：ok / missing / out_of_scope
- OpenSpec 对照：ok / missing / drifted
- 结论：aligned / needs_contract_reconfirm / needs_scope_cleanup
```

边界：reconciler 只提醒，不自动修订契约、不自动回退、不新增 `execution-contract.md`。

### Step 3.3.5：Cross-Session Continuity 一致性检查

按 `references/Design-Cross-Session-Continuity.md` 核对 state / handover / context-index 是否明显脱节：

1. 如果存在 `.zimaflow-state.yaml`：
   - `handover.latest_path` 为空，但本轮已经生成或更新 handover → 📝 建议补充。
   - `handover.latest_path` 指向的文件不存在 → ❌ 明确缺失。
   - `phase` 已进入 `verified` / `archived` / `closed`，但 `verification`、`archive` 或 `handover` 关键字段为空 → 📝 建议补充；无法判断是否可恢复时列 ❌。
2. 如果存在 `docs://.zimaflow/context-index.yaml`（物理位置由 `zimaflow project show --json` 的 `docs_root` 解析）：
   - `workflow.latest_handover` 与最新 handover 明显不一致 → 📝 建议补充。
   - `workflow.latest_state` 指向不存在的 state 文件 → ❌ 明确缺失。
   - index 中复制了 handover 正文、验证日志或大段业务规则 → ❌ 明确缺失，应只保留路径和短 metadata。
3. 如果本轮使用了 `zimaflow recall`：
   - handover 或 closing checklist 应记录 recall 的 `next_action`，方便下次判断是继续、重跑测试、刷新 handover、刷新 execution input，还是人工确认。
4. 如果 state 有 `execution_input.path`：运行 `zimaflow drift-check <change>`；结果为 stale / missing 时列为 📝 建议补充，并由用户决定刷新快照或回到上游工件。reconciler 不自动刷新派生物、不自动改真源、不阻断 git。

如果本轮涉及老项目 onboarding、baseline 文档、context-index 更新，或用户明确担心项目地图过期，建议运行只读 `zimaflow context-check`：

- `next_action=ok` → context-index 指针当前可读。
- `next_action=refresh_baseline` → 有 baseline / workflow 指针缺失，列为 📝 建议补充；如果缺失会影响下次恢复或路由，列为 ❌ 明确缺失。
- `next_action=create_context_index` → 当前目录向上未找到 `.zimaflow/context-index.yaml`；老项目列为 📝 建议补充，新项目/小修可写"不适用"。
- reconciler 不自动创建 context-index、不自动改 baseline，只把缺口交给 handover 或下一轮 onboarding。

输出模板：

```markdown
### 🔁 Cross-Session Continuity
- state：phase={...} / handover.latest_path={present/missing/empty}
- context-index：latest_handover={ok/stale/missing} / latest_state={ok/missing/not_applicable}
- recall：next_action={continue/run_tests/refresh_handover/refresh_execution_input/need_manual_confirmation/no_active_change/not_run}
- context-check：next_action={ok/refresh_baseline/create_context_index/not_run}
```

### Step 3.4：Knowledge Usage Review

在 Learn 候选扫描前，复核本轮知识使用情况：

1. 检查本轮是否读取过你的锚点表、`ZIMAFLOW_DATA_HOME/lessons-common.md` 或项目 `lessons.md`（锚点规则见 `references/knowledge-anchor-guide.md`）；私有源 `references/lessons-common.md` 只读兼容且优先级更低。
2. 列出本轮涉及的 knowledge ID，按 `loaded` / `cited` / `applied` / `challenged` 分类。
3. 检查用户级全局 usage ledger 是否已有对应事件；能力根内不保存真实事件。
4. 如果缺事件，把它列为 📝 建议补充，不直接写入；用户确认补记后使用 `zimaflow knowledge-record`，禁止 Agent 直接编辑 JSONL。
5. 如果发现知识不适用或过期，把它列为 Learn 候选或 stale-review 候选。

判定边界：

| 使用状态 | 收口判断 |
|----------|----------|
| `loaded` | 只表示读过；缺 ledger 事件时列为 📝 建议补记，不生成升级建议 |
| `cited` | 被方案、评审或 handover 引用；缺 ledger 事件时列为 📝，多次引用可列 learn 候选 |
| `applied` | 影响了路由、实现、验证或文档规则；缺 ledger 事件时列为 📝，同时列 learn 候选 |
| `challenged` | 发现知识过期、误导或不适用；缺 ledger 事件时列为 📝，同时列 learn / stale-review 候选 |

注意：handover 的 `## Knowledge Usage` 表格只是交接摘要，不等于 ledger 已记录。reconciler 检查的是 JSONL 事件是否存在；补记 ledger、修改 lesson 正文、升级 pattern/rule 都必须交给 `learn` 并等待用户确认。

输出模板：

```markdown
### 🧾 Knowledge Usage
- 已记录：kf-...（applied，stage: planning）
- 建议补记：kf-...（loaded，触发锚点：...）
- 待复核：kf-...（challenged，原因：...）
- 边界：handover 摘要不等于 ledger；lesson 正文/级别/规则回写需用户确认
```

### Step 3.5：Learn 候选扫描 Gate

在输出 checklist 前，必须判断本轮是否命中 learn 高置信信号。

高置信信号包括：

| 信号 | 例子 | 处理 |
|------|------|------|
| 用户纠正了 AI 的关键流程判断 | "不应该改 runtime，应该改 source"、"公司项目必须脱敏" | 输出候选 lesson |
| 真源/runtime 或 source/dist 路径误用 | 直接改了生成副本，后来同步回真源 | 输出候选 lesson |
| 公开内容涉及脱敏、安全边界或状态修正 | UAT 改为已上线、删除具体项目名/第三方名 | 输出候选 lesson |
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

### Step 3.6：Code Graph Evidence Review

如果 Step 1 识别出本轮使用了 `codebase-memory-mcp` / `code-graph-to-diagram`：

1. 检查是否有持久产物（如 `Designs/diagrams/<slug>/`、`Decisions/diagrams/<slug>/`、`image-skills/examples/code-graph-to-diagram/<slug>/`）。
2. 如果生成了图表，检查是否同时有 `brief.yaml`、`NOTES.md`，以及至少一个图表产物：`diagram.mmd` 或 `diagram.svg`。
3. 检查对应文档或 handover 是否记录：
   - 查询工具与 scope
   - 图表路径
   - 1-3 条结论
   - 限制 / 待确认推断（静态图不是 runtime trace、risk label 不是业务严重性、代码推断 schema 未验证等）
4. 如果只做了路由阶段短证据、没有生成图表，检查是否在路由结果或 handover 中记录了代码图证据摘要。

判定：

- 有查询摘要、结论、限制，并且 `brief.yaml` / `NOTES.md` / `diagram.mmd 或 diagram.svg` 齐全（如有图）→ ✅
- 有查询或图表，但缺 `NOTES.md` / 限制说明 / handover 记录 → 📝 建议补充
- 图表已生成但没有 `brief.yaml`、缺少 `NOTES.md`、没有任何 `diagram.mmd` / `diagram.svg`，或无法追溯查询参数 → ❌ 明确缺失

输出模板：

```markdown
### 🧭 Code Graph Evidence
- 已记录：{path}（query/scope + conclusion + limitation）
- 建议补充：{path} 缺 NOTES.md / 限制说明 / handover 摘要
- 明确缺失：{path} 缺 brief.yaml / NOTES.md / diagram.mmd 或 diagram.svg，无法完整追溯代码图来源
```

### Step 4：输出 Closing Checklist

以三级状态输出结果。证据类分段按"先看这轮做完没、再看证据留下没、最后看下一轮接得上没"的顺序排列。

输出前先应用两条格式规则：

**规则 A：not_applicable 分节合并显示**

当某个证据节的结论是 `not_applicable` / "本轮无适用项"时，**不要单独输出一个只有一句话的空节**。把当轮所有此类分节合并成一行，放在对应分段末尾：

```markdown
*本轮无适用项：Work Items、Guardrail 收口、Code Graph Evidence、Knowledge Usage*
```

**边界：这只是显示合并，不减少检查项。** 所有分项仍然要按各自的 Step 逐项检查，只是在结果为 not_applicable 时折叠显示。禁止退化成"不检查就不显示"——没检查过的项不能计入这一行，只有确认过确实不适用的才能折叠。

如果某个分节有实际内容（哪怕只是一条 ✅），仍然单独成节，不参与合并。

**规则 B：验证状态必须上浮**

按 Step 3.3.1 的上浮表，把 `failed` / `evidence_incomplete` / `not_run` / 关键字段缺失的情况写进顶部 ❌ 明确缺失或 📝 建议补充，并标注归因。环境副作用同样要上浮。

```markdown
## Closing Checklist

### ✅ 已完成
- （列出本轮已同步的文档项）

### 📝 建议补充
- （改动不大或非关键路径，但最好补一下的文档项）
- （附简要说明：建议更新什么内容）

### ❌ 明确缺失
- （按矩阵应该更新但确实没更新的文档项）
- （附具体说明：缺什么、影响是什么）

---
#### 一、验证与合规证据

### 🧪 Verification Evidence
- （列出 opsx_verify / full_tests / last_command / last_result / evidence_path 状态与结论）

### ⚖️ Spec Compliance / Reviews
- （全量审查是否已落盘为 `Reviews/` 下独立报告，并给出链接路径；只写一行"合规检查：done"不算通过）

### 🔀 OpenSpec Tasks Sync（tasks sync drift）
- （列出 tasks.md 勾选状态与实际完成信号的一致性；与 CLI `drift-check` 的 artifact hash drift 不是同一件事）

### 📋 Work Items
- （轻量模式台账的 done/blocked/doing 证据完整性）

*（本段中结论为 not_applicable 的分节，按规则 A 折叠到本段末尾一行）*

---
#### 二、范围与风险

### 🧷 Intent Lock
- （列出契约意图锁与 Decision / tasks / OpenSpec 的对齐情况）

### 🛡️ Guardrail 收口
- （本轮涉及 hotfix / rewind / secrets / release 时列出核对结果；密钥和发布 token 只写 path:line 或类别、不写值）

*（Handover / Code Graph Evidence / Knowledge Usage 如为 not_applicable，按规则 A 折叠；🧠 Learn 候选不参与折叠）*

---
#### 三、交接与经验回流

### 🔁 Handover / Cross-Session Continuity
- （列出 state / handover / context-index / recall next_action 的一致性）

### 🧭 Code Graph Evidence
- （列出本轮代码图证据记录情况）

### 🧾 Knowledge Usage
- （列出本轮知识 ID 的 loaded/cited/applied/challenged 状态）

### 🧠 Learn 候选
- （命中高置信信号时列出候选；未命中时写"未发现高置信候选"）

*（同上，not_applicable 分节折叠）*

---
**结论**：{本轮收口完整 / 有 N 项建议补充 / 有 N 项明确缺失}
```

折叠后的实际形态示例（三段中若干节不适用时）：

```markdown
#### 一、验证与合规证据

### 🧪 Verification Evidence
- full_tests：failed（1 failed，归因：worktree 目录名导致的既有测试失败）
- 结论：evidence_incomplete

### ⚖️ Spec Compliance / Reviews
- 已落盘：docs/Reviews/2026-07-29-xxx-compliance-report.md

*本轮无适用项：Work Items、OpenSpec Tasks Sync*
```

`🧠 Learn 候选` 即使未命中也要显式写"未发现高置信候选"，**不参与折叠**——它是 Learn 候选扫描 Gate 的强制输出，必须能看到扫描确实执行过。

分段只是阅读顺序，不是新增门禁；折叠只是版面优化，不减少检查项。所有分项仍然是 soft check 且仍需逐项检查，reconciler 不因为分段或折叠而自动阻断、不自动写回任何文件。

### Step 5：等待用户决策

- 如果有 ❌ 明确缺失项 → 默认建议"现在补"，补完后再生成 handover；只有用户明确选择跳过时，才记入 handover 遗留或继续后续流程
- 如果只有 📝 建议补充 → 告知用户，由用户决定现在补、记入 handover 遗留，或本轮不处理
- 如果有 🧠 Learn 候选 → 只列出候选，不自动写入 lessons；等待用户确认后再交给 learn Skill 写入
- 如果有 🧾 Knowledge Usage 建议补记 → 询问用户是否补记 usage ledger；补记只追加 JSONL，不修改 lesson 正文
- 如果有 🧭 Code Graph Evidence 建议补充 → 询问用户是否现在补 `NOTES.md` / handover 摘要 / 限制说明；明确缺失默认建议先补
- 如果有 🔀 OpenSpec Tasks Sync 需要同步 → 询问用户是否现在同步 `tasks.md`，并记录同步依据；reconciler 不代为勾选
- 如果有 🔁 Handover / Cross-Session Continuity 建议补充 → 询问用户是否现在补 state / context-index / handover 指针；明确缺失默认建议先补
- 如果有 🧷 Intent Lock 建议补充 → 询问用户是否现在补意图锁对照、回到 contract 重新确认，或把超出范围项记入后续迭代；明确缺失默认建议先补
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
- 检查能力自身的路线与待办记录是否需要更新
- 检查 references/ 下是否有新增文件未被其他 Skill 引用
- 必须执行 Learn 候选扫描 Gate。若本轮是因为流程缺口、用户纠正或真实踩坑而修改 Skill，至少输出 1 条候选 lesson；如果没有候选，说明为什么这只是普通维护。
- 如果本轮新增或修改 `knowledge-anchor-guide.md`、`knowledge-usage-contract.md` 或 lesson `ID`，必须检查 README 和 doc-sync matrix 是否同步。正常 usage 事件只写全局数据目录，不触发能力文档同步。

### 全部通过的情况

如果所有检查项都是 ✅，明确输出：

> ✅ 本轮收口完整，所有文档已同步。可以直接生成 handover。

不要为了显得有用而硬凑建议。

## 原则

- **检查不改写**：reconciler 只负责发现缺口并提醒，不替用户改文档。用户说"帮我补"时才动手。
- **Final Response Gate**：用户说"完成/收尾/本 session 完结"前，必须先运行 reconciler；git clean、tests passed、pushed 只是工程完成信号，不是 zimaflow session 收口完成信号。
- **learn 扫描不写入**：reconciler 只输出候选 lesson，不直接写 lessons。写入必须由 learn Skill 在用户确认后执行。
- **usage review 不改正文**：reconciler 可以建议补记 ledger，但不能直接修改 lesson 内容、出现次数、级别、deprecated 状态或 Skill 规则。
- **handover 摘要不是 ledger**：handover 中的 Knowledge Usage 只服务交接；是否已有使用证据，以 `zimaflow knowledge-record` 管理的全局 JSONL 事件及兼容期历史事件为准。
- **矩阵驱动**：所有检查项来自 doc-sync-matrix.md，不凭 AI 自由发挥。如果矩阵没覆盖的改动类型，标注"矩阵未覆盖，建议人工判断"。
- **不阻断流程**：即使有缺失项，用户说"不用管"就不管。reconciler 是提醒，不是 gate。
- **Guardrail 只提醒不代办**：hotfix / rewind / secrets / release 四类收口项，reconciler 只检查、提醒、记入交接；不自动写 INCIDENT、不自动改密钥、不代为 revoke/rotate、不自动发布、不自动打 tag、不自动改发布配置，是否处理由用户决定。
- **release readiness 是提醒不是发布**：有发布意图时建议跑 `zimaflow release-check` 并记录 `next_action` 与四问待确认项；reconciler 不 deploy、不打 tag、不读/写任何发布 token。
- **密钥值绝不外泄**：secrets 命中只在 checklist 和 handover 中引用 `path:line`，任何情况下都不把密钥原文写入 checklist、handover 或 lessons。
- **与 handover 串联不重叠**：reconciler 检查"文档同步了吗"，handover 检查"下一轮需要什么"。两者有交集（都看改动），但视角不同。
- **跨 session 续接一致性**：reconciler 必须检查 state / handover / context-index 的明显脱节；只提醒，不自动推进 phase，也不把 handover 正文塞进 state 或 context-index。
- **意图锁只对照不改写**：reconciler 可以发现 Decision / tasks / OpenSpec 偏离 requirement-contract 的意图锁，但不能直接改契约或规划；需要用户确认后回到对应上游产物。
- **tasks 漂移只标记不写回**：reconciler 可以发现 `tasks.md` 勾选状态与实际完成信号不一致，但不自动勾选、不自动改 spec、不自动推进 phase；是否同步以及同步依据由用户确认。
- **验证失败必须可见**：`full_tests` / `opsx_verify` 为 `failed` 时必须进入 ❌ 明确缺失，`evidence_incomplete` / `not_run` / 关键字段缺失时必须进入 📝 建议补充。即使归因为环境或隔离副作用也要上浮，只在条目中标注归因；归因只影响处理方式，不影响是否可见。
- **折叠不等于不检查**：not_applicable 分节合并显示只是版面优化，所有分项仍需逐项检查；只有确认过确实不适用的才能计入折叠行，没检查过的项不得折叠。
