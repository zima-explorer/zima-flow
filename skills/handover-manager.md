---
name: handover-manager
description: >
  跨工具交接文档管理。负责生成和读取 handover 文档，支持不同 AI coding 工具之间的无缝接力。
  触发场景：session 即将结束时、用户说"继续"或"切换"时、用户要求切换工具时、
  上下文消耗超过 60% 时主动提醒。
  触发词：继续、继续上次、切换到、交接、handover、收工、收尾、完成、完结、结束、已 push、push 完了、提交完成、工作树干净、两边都 clean、本 session 完结、换到 CLI、换到另一个工具。
---

# 跨工具交接文档管理

## 职责

你负责在开发 session 的关键节点生成标准化的交接文档，确保任何 AI 工具在新 session 中都能完整恢复上下文。

## 交接文档模板

所有 handover 文档遵循统一格式，文件命名：`{日期}-handover-{需求简述}.md`

存放位置：项目注册表中该项目对应的 `docs_dir`。

```markdown
# {需求简述} · 变更说明

> 类型：handover
> 日期：{YYYY-MM-DD}
> 需求 ID：{如有}
> 当前阶段：{任务拆解 / 方案设计 / 编码实现 / 测试验证 / 已完成}
> 工作模式：{完整模式 / 轻量模式}
> 本次工具：{工具名称}
> 代码仓库：{code_repo 路径}

## 决策

（本轮做出的关键技术决策，每条说清楚"选了什么、为什么、排除了什么"）

## 本轮改动

（按功能分组描述，每组说清楚前后端各做了什么）

### 1. {功能点 1}
{描述}

### 2. {功能点 2}
{描述}

## 文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| path/to/file | 新增/修改/删除 | 简要说明 |

## 验证

（跑了什么测试、命令是什么、结果如何）

## 遗留与下一步

（未完成的工作、下一轮应该做的事、优先级建议）

- [ ] 遗留项 1
- [ ] 遗留项 2

## Knowledge Usage

（本轮读取、引用、应用或质疑过的知识 ID；如无则写"无"）

| Knowledge ID | 状态 | 阶段 | 说明 |
|--------------|------|------|------|
| kf-... | loaded / cited / applied / challenged | routing / planning / implementation / closure | 简要说明 |

## 启动指引

（下一个 session 需要知道的操作信息）

- 当前分支：{branch}
- 启动命令：{如何起服务}
- 环境要求：{特殊依赖或配置}
```

## 生成时机

### 时机 1：session 正常收尾

用户说"收工"、"今天先到这"、"收尾"、"完成"、"完结"、"结束"、"已 push"、"push 完了"、"提交完成"、"工作树干净"、"两边都 clean"、"本 session 完结"等，或当前任务完成时：

1. **先触发 session-close-reconciler**：检查本轮改动的文档同步完整性。如有明确缺失项，建议用户先补再生成 handover；如用户选择"记入遗留"，将缺失项纳入 handover 的"遗留与下一步"
2. 回顾本次 session 的所有改动
3. 按模板生成完整 handover
4. **汇总 Knowledge Usage**：读取 reconciler 输出和本轮对 `knowledge-anchor-map.md` / `lessons-common.md` / 项目 `lessons.md` 的使用记录，把 loaded/cited/applied/challenged 的 knowledge ID 写入 handover 的 `## Knowledge Usage`
5. **触发 learn Skill 扫描**：回顾本次 session，识别是否有值得沉淀的经验（用户纠正、排错过程、技术决策、重复踩坑等）。如有候选 lessons，在 handover 文档末尾追加 `## 待沉淀经验` 小节，列出候选条目等用户确认
6. 写入项目文档目录
7. 告知用户：
   > 交接文档已生成：`{文件路径}`
   > 下次在任何工具中说"继续 {项目名} 的 {需求名}"即可恢复。
   > （如有待沉淀经验）另外发现 {N} 条值得沉淀的经验，见文档末尾，请确认是否沉淀。

#### 最终回复 Gate

handover-manager 不能因为 `git status` clean、测试通过、提交完成或 push 完成，就直接宣布 session 完结。这些只说明工程状态完成，不说明 zimaflow session 收口完成。

在回答"完成"、"收尾"、"本 session 完结"之前，必须确认 session-close-reconciler 已输出收口检查清单：

- ❌ 明确缺失：默认建议"现在补"，用户明确跳过时才写入 handover 遗留
- 📝 建议补充：交给用户选择现在补、记入遗留，或本轮不处理
- 🧠 Learn 候选：只列出候选，不自动写入 lessons；等待用户确认后再交给 learn Skill
- 🧾 Knowledge Usage：如果本轮有知识使用，handover 必须记录 knowledge ID 和状态；如果 usage ledger 缺事件，写入遗留或待沉淀经验

### 时机 2：工具切换

用户说"切到 CLI 继续"、"换到另一个工具讨论"等：

1. 生成当前进度的 handover（即使未完成）
2. 在"启动指引"中特别说明下一个工具应该做什么：
   > 建议在 CLI 中执行：读取此 handover 后，继续编码实现阶段，从任务 3 开始。

### 时机 3：上下文接近上限

如果检测到上下文消耗较高（对话轮次多、已处理大量文件），主动提醒：

> 当前 session 上下文已较满，建议先生成 handover 保存进度。要我现在生成吗？

### 时机 4：阶段切换

从任务拆解 → 方案设计、编码实现 → 测试验证等阶段切换时，生成阶段性 handover。这类 handover 的"遗留与下一步"直接写明下一阶段的入口操作。

## 读取与恢复

当用户说"继续"时：

1. 确认目标项目（从 sdd-router 获取，或读注册表匹配）
2. 在项目文档目录下找最新的 handover 文档：
   ```bash
   ls -t <docs_dir>/*handover* | head -5
   ```
3. 读取最新 handover 全文
4. 向用户汇报恢复的上下文：
   > 已读取上次交接文档（{日期}）：
   > - 需求：{需求简述}
   > - 阶段：{当前阶段}
   > - 遗留：{遗留项摘要}
   >
   > 从 {具体遗留项} 继续？
5. 用户确认后，根据当前阶段进入对应流程

## 原则

- **宁多不少**：handover 的信息密度宁可冗余，不要遗漏。下一个 session 的 AI 完全没有当前 session 的记忆。
- **文件清单必须准确**：列出的每个文件都必须是实际改动过的，不要凭记忆猜测。如果不确定，用 `git diff` 或 `git status` 确认。
- **不要美化进度**：如果某个任务只完成了一半，在遗留项中如实说明完成了哪部分、卡在哪里。
- **启动指引要可操作**：写的命令必须能直接复制执行，不要写模糊的"启动服务"。
- **经验沉淀不遗漏**：每次生成 handover 时都要触发 learn 扫描。宁可多提候选让用户否掉，不要漏掉有价值的踩坑经验。
- **知识使用不丢失**：凡是本轮读取、引用、应用或质疑过的 knowledge ID，都要进入 `## Knowledge Usage`，方便下个 session 继续判断是否该升级、修订或淘汰。
- **工程完成不等于 session 收口完成**：git clean、tests passed、pushed 只是工程信号；final response 宣布 session 完结前，必须先完成 session-close-reconciler 对账。
