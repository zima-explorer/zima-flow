---
name: legacy-project-onboarding
description: >
  存量老项目冷启动 / 项目考古 Skill。用于接手已有代码库、让 AI 快速建立项目全局认知，
  产出架构总览、接口清单、数据模型/ER 笔记和隐性知识问答记录。
  触发词：老项目冷启动、项目考古、接手老项目、梳理架构、生成接口清单、生成 ER 图、项目 onboarding、legacy project bootstrap。
---

# Legacy Project Onboarding — 老项目冷启动

## 职责

为已有代码库建立 AI 可读的项目上下文。目标不是一次性读完整个项目，而是像带新人一样，先建立可执行的全局认知，再把代码里看不到的"为什么"问出来。

本 Skill 只负责理解存量系统，不负责把项目接入 zimaflow：

- 项目初始化（OpenSpec、Bridge Rule、项目文档目录、注册）在 v0.1 由手动补齐完成，见 `docs/getting-started.md`。
- `legacy-project-onboarding` 负责在项目已可用后，为存量代码建立认知底座。
- 本 Skill 只推荐用于老项目 / 存量代码 / 项目考古；新项目初始化不强制生成认知底座。

本 Skill 产出的整体称为 **code-intelligence baseline**。baseline 是轻量、工具无关的：可以使用代码图谱工具增强，但不能把任何代码图谱工具作为硬依赖。

## 输入

- 目标项目代码仓路径
- 项目文档目录 `docs_dir`
- 本次关注范围：全项目 / 指定模块 / 指定业务线 / 指定需求相关链路
- 可选：真实 DB schema、SHOW INDEX、线上流量/接口调用范围

如果项目尚未完成 zimaflow 初始化，先建议按 `docs/getting-started.md` 手动补齐；用户明确跳过时继续，但在输出中标记 `⚠️ 未初始化路径`。

## 产物

默认写入项目文档目录：

| 文件 | 内容 |
|------|------|
| `Designs/Architecture-Overview.md` | 系统分层、模块职责、依赖关系、关键入口 |
| `Designs/Module-Map.md` | 模块清单、目录位置、职责、主要依赖 |
| `Designs/Interface-Inventory.md` | 对外接口、入口落点、参数摘要、归属模块、风险点 |
| `Designs/Data-Model-ER.md` | 核心实体、表关系、真实索引来源、待确认字段 |
| `Designs/Test-Entry-Points.md` | 单测、集成测试、E2E、手工验证入口和常用命令 |
| `Designs/Key-Flows.md` | 当前范围内关键链路、调用路径、状态变化和外部依赖 |
| `Designs/Implicit-Knowledge-QA.md` | AI 基于代码证据提出的问题、人类回答、隐藏约束 |
| `.zimaflow/context-index.yaml` | 只记录 baseline 文档路径、短 metadata、常用命令、风险锚点、active change 和最新 handover |

如果项目文档已有同名文件，先读旧文件，改为增量更新，不覆盖用户内容。

`.zimaflow/context-index.yaml` 是路标，不是正文。禁止把架构总览、接口清单、handover、OpenSpec 三件套或大段业务规则复制进去。

## 执行步骤

### Step 1：确定范围

确认本次 onboarding 范围：

- 全项目：适合新接手但代码规模可控。
- 指定模块：适合大型项目，优先围绕当前需求。
- 指定链路：适合缺陷修复、接口改造、跨系统集成。

输出范围说明：

```markdown
## Onboarding Scope

- 项目：
- 代码仓：
- 文档目录：
- 范围：
- 暂不覆盖：
- 输入可信源：
```

### Step 2：架构总览

扫描目录结构、构建文件、框架入口、配置文件和模块依赖，产出：

- 系统分层
- 模块职责
- 上下游依赖
- 核心启动/路由入口
- 本轮范围相关的关键路径

只把从代码或文档中确认的事实写为事实；推断必须标注为"推断"。

### Step 2.5：模块地图

产出 `Designs/Module-Map.md`：

- 模块 / 包 / 子系统名称
- 目录位置
- 职责边界
- 主要依赖与被依赖关系
- 关键入口文件
- 风险或待确认点

如果范围是指定模块或指定链路，只覆盖本次范围内模块，并在文档开头写明"暂不覆盖"。

### Step 3：接口清单

提取对外入口：

- HTTP controller / route
- RPC / Facade / service API
- 消息队列 consumer / producer
- scheduled job / CLI command

对每个入口记录：

| 字段 | 说明 |
|------|------|
| 接口/入口 | 路径、方法、命令或 topic |
| 落点 | 文件、类、方法 |
| 参数/核心字段 | 只列影响理解的字段 |
| 归属模块 | 模块/业务线 |
| 读写资源 | 表、缓存、外部服务 |
| 风险/待确认 | 注释不一致、副作用、权限、状态变更 |

不要轻信注释。接口名、注释和实现不一致时，必须标为待确认。

### Step 4：数据模型 / ER

优先使用真实 DB schema 和索引；没有真实 DB 时，允许从 migration/entity/schema 文件生成"代码推断版"，但必须标注来源。

记录：

- 核心实体与表
- 关键字段含义
- 表关系
- 真实索引或代码推断索引
- 高风险字段（金额、状态机、租户/业务线隔离、权限、外部 ID）

如果用户无法提供真实索引，不要编造线上索引；写入"待用户补充 SHOW INDEX / schema dump"。

### Step 5：测试入口和关键链路

产出 `Designs/Test-Entry-Points.md`：

- 常用测试命令
- 单元测试、集成测试、E2E 或手工验证入口
- 测试数据、fixture、mock、外部依赖说明
- 当前缺口：无测试、测试需要环境、测试与实际链路脱节

产出 `Designs/Key-Flows.md`：

- 本次范围内的关键用户路径 / 系统链路
- 入口到核心服务 / 数据写入 / 外部调用的路径
- 状态机、权限、金额、租户隔离、外部 ID 等高风险节点
- 已确认事实、AI 推断、待确认问题分开记录

### Step 6：隐性知识问答

先让 AI 基于代码证据提出问题，再让人回答。不要空泛问"有什么坑"。

优先问题类型：

- 为什么这里不用缓存 / 为什么不能加缓存？
- 状态机是否有历史兼容或不可逆迁移？
- 金额、库存、权限、租户隔离是否有红线？
- 哪些下游服务不稳定或有特殊契约？
- 哪些接口名/注释和真实行为不一致？
- 哪些表字段不能删、不能改名、不能复用？
- 哪些链路曾经出过线上事故？

每条问答格式：

```markdown
### Q: {基于代码证据的问题}

- 代码证据：`path/to/file`
- AI 推断：{如有，必须标注推断}
- 人类回答：{用户补充}
- 沉淀类型：业务规则 / 架构决策 / 踩坑 / 数据约束
- 后续动作：无 / 写入 lessons / 更新架构图 / 补测试
```

### Step 7：Context Index

创建或更新 `<docs_dir>/.zimaflow/context-index.yaml`。如果目录不存在，先创建 `<docs_dir>/.zimaflow/`。

最小字段：

```yaml
schema_version: 1
project:
  name:
  code_path:
  docs_path:
  status:

baseline:
  scope:
  generated_at:
  source: legacy-project-onboarding
  architecture_overview: Designs/Architecture-Overview.md
  module_map: Designs/Module-Map.md
  interface_inventory: Designs/Interface-Inventory.md
  data_model_er: Designs/Data-Model-ER.md
  test_entry_points: Designs/Test-Entry-Points.md
  key_flows: Designs/Key-Flows.md
  implicit_knowledge_qa: Designs/Implicit-Knowledge-QA.md

workflow:
  active_changes: []
  latest_handover: ""
  latest_state: ""

commands:
  dev: ""
  test: ""
  verify: ""

risk_anchors: []

updated_at:
updated_by: legacy-project-onboarding
```

写入规则：

- 只写路径、短标签、时间戳和简短状态。
- 路径优先相对 `docs_dir`，跨仓库引用才用绝对路径。
- 常用命令只记录命令字符串，不记录长日志。
- 风险锚点只记录标签，例如 `state machine`、`permission boundary`。
- 如果旧 index 已存在，保留未知字段，优先增量更新本 Skill 负责的字段。

### Step 8：知识账本

如果本次 onboarding 读取或应用了 `$ZIMAFLOW_HOME/references/knowledge-anchor-map.md` 中的知识，按 `$ZIMAFLOW_HOME/references/knowledge-usage-guide.md` 追加 ledger 事件。

如果本次产出了可复用经验，不直接写入 lessons；交给 `learn` 做用户确认。

### Step 9：收口

输出：

- 产物文件清单
- context index 路径
- 已确认事实
- 推断和待确认问题
- 建议优先补齐的隐性知识
- 是否建议触发 `learn`

## 原则

- **代码事实和人类回答分开写**：不要把 AI 推断伪装成事实。
- **context index 只做路标**：不要把正文塞进 YAML，Agent 后续按需读取被索引文档。
- **老项目专用**：新项目初始化不强制 onboarding；存量项目缺 baseline 时推荐补齐但不硬阻断。
- **工具可插拔**：代码图谱工具只能增强证据，不能成为 baseline 的必要条件。
- **先关键链路，后全量覆盖**：大型项目优先围绕当前需求。
- **真实 schema 优先**：数据库索引、字段含义、线上差异不能凭代码脑补。
- **隐性知识要有证据触发**：用代码现象唤起人的记忆，比空泛访谈更可靠。
- **不覆盖旧文档**：已有设计文档先读后增量更新。
