# Context Intelligence Baseline — 老项目认知底座设计

> 类型：Design
> 状态：v0.1
> 来源：结合 zimaflow 项目初始化流程、legacy-project-onboarding、handover 和 state 文件现状裁剪。

## 一、目标

给存量老项目建立一层轻量的 AI 可读上下文底座：

- 让 Agent 先知道该读哪些项目文档，而不是每次从全仓库重新扫起。
- 把代码事实、AI 推断、人类确认分开，避免把反推语义当事实。
- 为 sdd-router、task-planning、handover 恢复提供稳定入口。
- 保持工具无关：可以用代码图谱工具增强，但不把图谱工具变成硬依赖。

本设计只针对老项目 / 存量项目。新项目初始化在 v0.1 由手动补齐完成（见 `docs/getting-started.md`），不强制生成认知底座。

## 二、适用范围

| 场景 | 行为 |
|------|------|
| 新项目初始化 | 只走手动初始化，不要求 baseline |
| 存量项目首次接入 zimaflow | 手动初始化后建议运行 `legacy-project-onboarding` |
| 已接入但缺少上下文文档的老项目 | `sdd-router` 推荐补一次 onboarding |
| 小修小补且已有 context index | 读取 index 后只加载相关文档，不全量扫描 |
| 紧急热修复 | 不因缺少 baseline 阻断，修复后建议补齐 |

## 三、Code-Intelligence Baseline 产物

默认写入项目文档目录 `docs_dir`，以 Markdown 为正文载体：

| 文件 | 最小内容 |
|------|----------|
| `Designs/Architecture-Overview.md` | 系统分层、模块职责、关键入口、上下游依赖 |
| `Designs/Module-Map.md` | 模块清单、目录位置、职责、主要依赖 |
| `Designs/Interface-Inventory.md` | HTTP/RPC/CLI/Job/消息入口、落点、读写资源、风险点 |
| `Designs/Data-Model-ER.md` | 核心实体、表关系、索引来源、待确认字段 |
| `Designs/Test-Entry-Points.md` | 单测/集成测试/E2E/手工验证入口、常用命令 |
| `Designs/Key-Flows.md` | 当前范围内关键链路、调用路径、状态变化、外部依赖 |
| `Designs/Implicit-Knowledge-QA.md` | 基于代码证据的问题、人类回答、隐藏约束 |

大型项目可以只生成指定模块或指定链路的 baseline，但必须在每个文档开头标明 scope 和暂不覆盖范围。

## 四、Thin Context Index

位置：

```text
<docs_dir>/.zimaflow/context-index.yaml
```

它是路标，不是正文。只放路径、短标签、时间戳和简短状态。

示例：

```yaml
schema_version: 1
project:
  name: example-project
  code_path: /path/to/example-project
  docs_path: /path/to/example-project-docs
  status: active

baseline:
  scope: full-project
  generated_at: "2026-01-01T09:00:00+08:00"
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

risk_anchors:
  - state machine
  - permission boundary

updated_at: "2026-01-01T09:00:00+08:00"
updated_by: legacy-project-onboarding
```

禁止写入：

- 架构总览正文
- 接口清单表格全文
- handover 正文
- OpenSpec proposal/design/tasks/spec 内容
- 大段业务规则或需求叙述

## 五、读取规则

`sdd-router` 在 Step 2 加载上下文时：

1. 优先检查 `<docs_dir>/.zimaflow/context-index.yaml` 是否存在。
2. 存在时只读取 index，基于本轮需求选择 1-3 个相关文档继续读取。
3. 不存在但项目是老项目 / 存量代码 / 用户说接手、梳理、项目考古时，推荐先运行 `legacy-project-onboarding`。
4. 不存在时不阻断普通轻量需求；在路由结果中标记"Context Index：缺失，建议补齐"。

## 六、P1/P2/P3 Change Impact

这里的 P1/P2/P3 是"需求变更影响级别"，不是任务优先级。

| 级别 | 判断 | 处理 |
|------|------|------|
| P1 | 只影响任务、局部实现、测试补充，不改变需求契约、路线决策或 OpenSpec 三件套 | 当前阶段内处理，更新 tasks / handover |
| P2 | 影响 requirement-contract、Decision、原型评审记录、proposal/design/tasks/spec 之一 | 更新并重新确认受影响上游产物，再继续下游 |
| P3 | 影响产品范围、架构方向、数据模型、权限、敏感数据、计费、多角色/多端协作、跨系统集成或发布策略 | 回到 route-decision-recorder / OpenSpec review，必要时重新拆 change |

`sdd-router` 和后续 Skill 遇到需求变更时，先判断 change impact，再决定是否回退阶段。不要只根据"改动行数"判断。

## 七、事实 / 推断 / 待确认

所有 baseline 文档都必须区分：

- 已确认事实：来自代码、配置、真实 schema、用户明确确认。
- AI 推断：由命名、调用关系、注释或字段含义推得，必须标注来源和不确定性。
- 待确认问题：需要用户或真实环境补充的业务规则、数据约束、部署差异。

从代码反推出来的需求语义不能直接进入 requirement-contract 或 OpenSpec；必须先经过用户确认。

## 八、后续可能增强

- 增加 `zimaflow context-index init/update` CLI，统一写 YAML，减少格式漂移。
- 将项目级 risk anchors 与全局 `knowledge-anchor-map.md` 建立松耦合映射。
- 在 `zimaflow close --json` 中输出 context index 的 latest_handover 状态。
