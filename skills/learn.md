---
name: learn
description: >
  半自动经验沉淀。在开发 session 中识别值得记录的经验教训，辅助整理并等待用户确认后写入。
  支持三级进化：lesson（单次记录）→ pattern（跨项目通用）→ rule/skill（自动化执行）。
  触发词：学到了、踩坑了、记一下、沉淀、learn、这个坑之前也遇到过、总结一下经验。
  也会被 handover-manager 在生成交接文档时自动调用。
---

# Learn — 半自动经验沉淀

## 职责

识别开发过程中值得沉淀的经验教训，辅助整理成结构化的 lesson 条目，经用户确认后写入项目级和/或通用级经验库。跟踪同一类经验的出现频次，在达到阈值时提示进化（lesson → pattern → rule/skill）。

同时维护知识使用证据：
- 新 lesson/pattern 必须带稳定 `ID`（格式：`kf-YYYYMMDD-short-slug`）
- 使用记录写入 `$ZIMAFLOW_HOME/references/knowledge-usage-ledger.jsonl`
- 锚点触发规则见 `$ZIMAFLOW_HOME/references/knowledge-anchor-map.md`
- 账本字段和淘汰规则见 `$ZIMAFLOW_HOME/references/knowledge-usage-guide.md`

账本只能作为证据，不能替代用户确认。`learn` 可以根据 ledger 建议更新"出现次数"、升级、降级或淘汰，但写入 lesson 正文、修改级别、回写 Skill 前必须问用户。

## 两种触发方式

### 方式 1：主动触发

用户在 session 中说"记一下这个坑"、"这个经验沉淀一下"、"learn"等，立即进入整理流程。

### 方式 2：被动触发（由 handover-manager 调用）

handover-manager 生成交接文档时，自动扫描本次 session 是否有待沉淀的经验。扫描信号：

| 信号 | 说明 |
|------|------|
| 用户纠正了 AI 的做法 | "不对，应该这样"、"别用这个，用那个" |
| 遇到报错并花时间排查 | 调试循环超过 2 轮的问题 |
| 做了技术决策并说明理由 | "选 A 不选 B，因为..." |
| 发现了框架/工具的隐蔽行为 | "原来这个 API 默认会..."、"这个配置不生效是因为..." |
| 同一类问题再次出现 | 匹配已有 lessons 中的关键词 |

扫描结果以候选列表形式呈现，**不自动写入**，等用户确认。

### 方式 3：Session 收尾候选扫描（高置信信号下主动建议）

不依赖收工触发词，而是在检测到以下**高置信信号**时，主动提出"这次有几条经验值得沉淀，要整理一下吗？"：

| 信号 | 说明 |
|------|------|
| 用户明确纠正了 AI 的关键判断 | 不是小修改，而是"你做错了方向"级别的纠正 |
| 实现发生返工 / 回滚 / 重做 | 已有代码被推倒重来，说明初始方向有误 |
| 发现旧实现却前期没有先查 | 白白绕了弯路，有明确的"应该更早做 X"的时间点 |
| 同一类问题在一次 session 内踩了两次 | 第一次没有泛化，第二次又中招 |
| 真源/runtime 或 source/dist 路径误用 | 直接改了生成副本、runtime、副本目录，后来才回写真源 |
| 公开内容被用户纠正脱敏或状态准确性 | 团队项目名、第三方名、验收环境/上线状态等被用户指出必须修正 |
| 因流程缺口直接回写 Skill/规则 | 没有先沉淀 lesson，直接把经验写进了 sdd-router、reconciler、sync 规则等 |

**不触发的情况**：普通问答、正常调试、小修改、用户说"先到这"/"收工"等结束语——这些不是高置信信号，不主动扫描。

**触发后**：整理候选 lesson（≤3 条），以简短问句形式呈现，等用户确认是否沉淀。不要强制推送、不要在用户说"不用"后再追问。

## 经验条目格式

每条 lesson 使用统一格式：

```markdown
## {主题标题}

- **ID**：kf-YYYYMMDD-short-slug
- **来源**：{项目名} / {日期} / {session 简述}
- **出现次数**：{N}
- **出现项目**：{项目 1, 项目 2, ...}
- **级别**：lesson | pattern | rule

### 场景

{在什么情况下遇到这个问题}

### 问题

{具体发生了什么}

### 解决方法

{怎么修的}

### 通用原则

{提炼出的可复用原则，一两句话}
```

## 写入位置

| 级别 | 写入位置 | 条件 |
|------|---------|------|
| lesson（项目级） | `<docs_dir>/lessons.md` | 默认，用户确认即写入 |
| pattern（通用级） | `$ZIMAFLOW_HOME/references/lessons-common.md` | 用户确认"这个跨项目通用"后写入 |
| rule/skill | 项目 `CLAUDE.md` 或新建 Skill | 用户确认"封装成规则"后执行 |

> **脱敏要求**：项目级 `lessons.md` 可以保留真实项目名等本地信息；但写入通用级 `lessons-common.md` 时，必须省略或泛化"来源 / 出现项目"等字段，只保留可复用的技术结论，不带入任何具体项目名、第三方名或内部路径。

## 三级进化机制

进化判断优先参考 `knowledge-usage-ledger.jsonl` 中的 `applied` / `cited` 事件，但仍需用户确认。

- `loaded`：只说明读过，不能单独触发升级。
- `cited`：说明被方案、评审或 handover 引用，可作为中等强度证据。
- `applied`：说明知识改变了实现、路由或评审决策，是主要升级证据。
- `challenged`：说明知识可能过期或有误，升级前必须先复核。

### Level 1 → Level 2：lesson → pattern

当一条 lesson 满足以下任一条件时，提示用户考虑提升为 pattern：

- **出现次数 ≥ 2**（同一项目内或跨项目）
- **用户主动标注"这个是通用的"**

提示方式：
> 这条经验"{主题}"已经在 {项目 A} 和 {项目 B} 中出现过了。
> 要同步到通用经验库（lessons-common.md）吗？

用户确认后：
1. 在 `lessons-common.md` 中写入，级别标为 `pattern`
2. 更新原项目 lessons.md 中该条目的出现次数和级别
3. 如本次确认来自 ledger 证据，在回复中列出支撑的 knowledge ID 和事件类型

### Level 2 → Level 3：pattern → rule/skill

当一条 pattern 满足以下任一条件时，提示用户考虑封装：

- **出现次数 ≥ 3**
- **pattern 描述的是一个可以被代码或规则自动执行的行为**

提示方式：
> "{主题}"已经出现 {N} 次了。按"出现 3 次就 Skills 化"的经验——要把它封装成规则或 Skill 吗？
>
> 建议选项：
> 1. 回写到源 Skill 的约束规则中（推荐——经验直接加固触发问题的 Skill，下次不再复现）
> 2. 写入项目 CLAUDE.md 的规则段（适合项目特定约束）
> 3. 创建独立 Skill（适合跨项目通用流程）
> 4. 暂不封装，继续观察
>
> 优先选 1：实践中，高频问题通过"定位源 Skill → 补约束 → 验证 → 交叉验证"可被逐类消除。经验沉淀的终点应该是回写到触发问题的那个 Skill 中，而不是另建独立规则。

## 匹配已有经验的方法

每次触发时，先扫描已有经验库做去重和计数更新：

1. 读取当前项目的 `<docs_dir>/lessons.md`（如果存在）
2. 读取 `$ZIMAFLOW_HOME/references/lessons-common.md`
3. 读取 `$ZIMAFLOW_HOME/references/knowledge-usage-ledger.jsonl`（如果存在）
4. 对候选 lesson 的主题、关键词、稳定 ID，与已有条目做相似度匹配：
   - 完全匹配（相同的错误信息、相同的 API/工具名）→ 更新出现次数
   - 相似主题（同一技术领域的类似问题）→ 提示用户确认是否为同一类
   - 无匹配 → 新建条目
5. 如果匹配到已有 ID，汇总相关 ledger 事件，区分 loaded/cited/applied/challenged，不要把 loaded 直接算成出现次数

## 知识使用账本

当 learn 确认某条知识被复用、引用、应用或质疑时，追加 JSONL 事件到 `$ZIMAFLOW_HOME/references/knowledge-usage-ledger.jsonl`。

最低字段：

```json
{"event_id":"use-YYYYMMDD-NNN","knowledge_id":"kf-YYYYMMDD-short-slug","event_type":"applied","project":"项目名","session":"本轮任务简述","stage":"planning","trigger":"触发锚点或原因","reason":"为什么读/用/质疑这条知识","timestamp":"YYYY-MM-DDTHH:MM:SS+08:00"}
```

写入规则：

- 只追加一行 JSON，不在已有事件上修改。
- 如果只是阅读，使用 `loaded`；真正影响决策才使用 `applied`。
- 如果发现旧知识不适用，使用 `challenged` 并生成 learn 候选或修订建议。
- 不要自动清理 schema-example 事件；它们用于说明字段格式。

## 淘汰候选

当用户要求清理经验库，或 session-close-reconciler 发现知识库膨胀时：

1. 按 `knowledge-usage-guide.md` 的 stale-review 规则扫描。
2. 只输出候选，不删除。
3. 让用户选择：保留、标记 deprecated、移动到归档。
4. 用户确认后再改 lesson 正文或移动文件。

## 执行步骤

### 主动触发时

1. 用户描述了一个经验/踩坑
2. 按条目格式整理（提炼场景、问题、解决方法、通用原则）
3. 检查是否与已有 lessons 匹配
4. 向用户展示整理后的内容，确认：
   - 内容是否准确
   - 写入项目级还是同时写入通用级
5. 确认后写入对应文件
6. 如确认本轮复用了已有知识，追加 ledger 事件
7. 如果达到进化阈值，提示进化

### 被动触发时（handover-manager 调用）

1. 扫描本次 session 的对话，识别符合信号的片段
2. 整理为候选 lesson 列表
3. 在 handover 文档末尾追加 `## 待沉淀经验` 小节：
   ```markdown
   ## 待沉淀经验

   以下经验从本次 session 中识别，待确认后沉淀：

   ### 候选 1：{主题}
   - 场景：{...}
   - 解决：{...}
   - 建议级别：lesson / pattern
   - 匹配已有：{无 / 匹配 lessons-common.md 中的 "{主题}"}

   确认沉淀？（是 / 否 / 修改后沉淀）
   ```
4. 等待用户逐条确认
5. 确认的条目写入对应文件

### Reconciler 候选触发时

当 `session-close-reconciler` 输出了 `Learn 候选`：

1. 读取候选条目，不重新发散生成无关候选。
2. 对每条候选检查已有 lessons 和 `lessons-common.md` 是否相似。
3. 检查候选是否对应已有 knowledge ID 或 ledger 事件。
4. 向用户确认是否写入，以及写入项目级还是通用级。
5. 用户确认后按统一格式写入。
6. 如果候选已经被直接回写成 Skill 规则，仍可补一条 lesson，说明"规则已修，补记录用于后续统计和复盘"。

## 原则

- **不自动写入**：任何经验必须经用户确认才写入文件。AI 的判断可能不准，宁可漏记也不要记错的。
- **格式统一**：所有 lesson 遵循统一格式，确保可检索、可对比、可进化。
- **规则已修也要补记录**：直接改 Skill 能解决下次行为，但没有 lesson 就无法统计出现次数和判断是否应升级 pattern。
- **账本是证据不是裁判**：ledger 记录的是使用事实，是否升级、降级、淘汰仍由用户确认。
- **稳定 ID 优先**：引用知识时优先使用 `ID`，不要依赖标题文本。
- **进化不强制**：达到阈值时提示，但用户可以说"暂不封装"。有些经验需要更多观察。
- **已有 lessons 可导入**：如果项目已有手写的 lessons 文件，可以读取并标记为种子数据，后续新经验在此基础上累积和匹配。
