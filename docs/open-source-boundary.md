# 公开范围与后续规划

本文说明公开发行版包含哪些能力，以及哪些能力计划在后续版本逐步开放。这个仓库是经过发行审查的公开子集，不是维护者完整工作区的镜像。

## 纳入

| 模块 | 公开文件 | 原因 |
|------|----------|------|
| `sdd-router` | `skills/sdd-router.md` | 主入口，解释模式选择、排障路径、变更分级、rewind 和扩展开关。 |
| `requirement-contract` | `skills/requirement-contract.md` | 进入规划和 OpenSpec 前的核心 Gate；含 GWT 验收标准和反问上限。 |
| `task-planning` | `skills/task-planning.md` | 将已确认范围转成可执行任务。 |
| `route-decision-recorder` | `skills/route-decision-recorder.md` | 让完整模式的路线决策可追踪。 |
| `openspec-superpowers-bridge` | `skills/openspec-superpowers-bridge.md` | 连接 OpenSpec 文档和实现纪律。 |
| `spec-compliance-check` | `skills/spec-compliance-check.md` | 对照 spec 检查实现；含 B4 破坏性变更 / B5 沿用抽象护栏。 |
| `legacy-project-onboarding` | `skills/legacy-project-onboarding.md` | 给存量代码库建立轻量认知底座和 thin context index。 |
| `session-close-reconciler` | `skills/session-close-reconciler.md` | 显式完成收口检查；含 hotfix/rewind/secrets Guardrail。 |
| `handover-manager` | `skills/handover-manager.md` | 保存跨 session 上下文；含 Guardrail 承接和 state/index。 |
| `learn` | `skills/learn.md` | 经用户确认后沉淀经验。 |
| reference tables | `references/*.md` | 小型可复用字典、矩阵和设计说明（含认知底座与 state 设计）。 |
| agent rules | `rules/` | 面向公开使用的最小规则片段。 |
| `scripts/install.sh` | `scripts/install.sh` | 基础安装公开仓内容，不做项目初始化。 |
| `bin/zimaflow` | `bin/zimaflow` | CLI 读取端，提供 close、单仓 state/recall、JSON 输出和 hook 提醒。 |

## v0.2 alpha 候选方向

v0.2 alpha 的候选主题是跨 session 续接与 CLI 读取端。它会优先公开已经能用通用语言解释、且不依赖私有项目目录的能力。

| 方向 | 公开价值 | 边界 |
|------|----------|------|
| session continuity | 解释 state、handover、recall、context index 如何配合恢复上下文 | 不引入新的 memory 系统，不复制私有 handover |
| CLI 读取端 | 单仓 `state` / `recall` 已纳入；`release-check`、`context-check`、`drift-check` 是下一批候选命令 | 只读优先，不 deploy、不读取密钥、不自动改写项目 |
| guardrails catalog | 给高风险规则稳定命名，方便 review 和 handover 引用 | 默认 soft gate，不默认阻断 |
| 公开示例 | 用 demo 展示跨 session 恢复和发布前检查 | 示例必须无网络、无凭证、无真实项目名 |

更多说明见 [v0.2 alpha 公开规划](v0.2-alpha-plan.md)。

## 后续保留

以下能力已完成开发,迭代打磨中，计划在后续版本随公开示例和稳定模板逐步开放：

| 方向 | 亮点 |
|------|------|
| 产品原型评审（`proto-review`） | 想法或 PRD 一键转成可评审原型，先看得见再写 spec。 |
| 完整项目初始化器 | 一条命令接入新项目，自动配好 OpenSpec、规则和 skills。 |
| 知识使用闭环 | 经验从"靠记忆"变成可追踪、可淘汰的账本；公开前需要抽象和脱敏。 |
| 可选硬门禁 | 按真实复发信号逐步引入阻断式 guard，默认不启用。 |

## 不直接公开

- 维护者工作区中的原始 roadmap、评估记录和使用账本。
- 真实项目、真实公司、个人路径、私有仓库、私有服务或密钥相关内容。
- 仍缺少公开模板、公开示例或稳定边界的实验性模块。
- 任何会让安装脚本隐式修改用户 agent 配置、shell profile 或项目注册表的行为。

以上为方向性计划，不代表固定时间表；具体节奏以后续 release 为准。
