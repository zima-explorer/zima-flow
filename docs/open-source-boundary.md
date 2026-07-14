# v0.1 范围与后续规划

本文说明 v0.1 公开发行版包含哪些能力，以及哪些能力计划在后续版本逐步开放，方便你判断当前能用什么、可以对什么保持期待。

## 纳入

| 模块 | 公开文件 | 原因 |
|------|----------|------|
| `sdd-router` | `skills/sdd-router.md` | 主入口，解释模式选择和扩展开关。 |
| `requirement-contract` | `skills/requirement-contract.md` | 进入规划和 OpenSpec 前的核心 Gate。 |
| `task-planning` | `skills/task-planning.md` | 将已确认范围转成可执行任务。 |
| `route-decision-recorder` | `skills/route-decision-recorder.md` | 让完整模式的路线决策可追踪。 |
| `openspec-superpowers-bridge` | `skills/openspec-superpowers-bridge.md` | 连接 OpenSpec 文档和实现纪律。 |
| `spec-compliance-check` | `skills/spec-compliance-check.md` | 对照 spec 检查实现。 |
| `session-close-reconciler` | `skills/session-close-reconciler.md` | 显式完成收口检查。 |
| `handover-manager` | `skills/handover-manager.md` | 保存跨 session 上下文。 |
| `learn` | `skills/learn.md` | 经用户确认后沉淀经验。 |
| reference tables | `references/*.md` | 小型可复用字典和矩阵。 |
| agent rules | `rules/` | 面向公开使用的最小规则片段。 |
| `scripts/install.sh` | `scripts/install.sh` | 基础安装公开仓内容，不做项目初始化。 |
| `bin/zimaflow` | `bin/zimaflow` | 最小 CLI，提供 close、JSON 输出和 hook 提醒。 |

## 后续规划

以下能力已完成开发,迭代打磨中，计划在后续版本随公开示例和稳定模板逐步开放：

| 方向 | 亮点 |
|------|------|
| 产品原型评审（`proto-review`） | 想法或 PRD 一键转成可评审原型，先看得见再写 spec。 |
| 老项目认知底座（`legacy-project-onboarding`） | 接手存量项目快速建立认知：架构、接口、数据模型一览。 |
| 一键初始化器 | 一条命令接入新项目，自动配好 OpenSpec、规则和 skills。 |
| 完整 CLI | 在 `close` 之外补上状态跟踪、知识淘汰复查和交接漂移检查。 |
| 知识使用闭环 | 经验从"靠记忆"变成可追踪、可淘汰的账本。 |
| 可选硬门禁 | 按真实复发信号逐步引入阻断式 guard，默认不启用。 |

以上为方向性计划，不代表固定时间表；具体节奏以后续 release 为准。
