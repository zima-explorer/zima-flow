# v0.1 开源边界

本文记录 zimaflow 源 skill 集的首次公开发行决策。

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

## 暂缓

| 模块 | 原因 |
|------|------|
| `legacy-project-onboarding` | 对存量系统考古有用，但不是首次 demo 主链路必需。 |
| `proto-review` | 需要公开原型模板和示例资产后再纳入。 |
| 外部实践参考 | 属于研究笔记，不是运行时必需材料。 |

## 重写

| 模块 | 原因 |
|------|------|
| 完整项目初始化器 | v0.1 基础安装脚本不负责 OpenSpec 初始化、项目注册表或项目文档目录。 |
| 完整 CLI | v0.1 仅保留通用命令，更多能力后续单独设计。 |
| 源工作区 README.md 和路线图笔记 | 混有路线历史、源工作区假设和未发布设计笔记。 |

## 移除

| 模块 | 原因 |
|------|------|
| `references/knowledge-usage-ledger.jsonl` | 运行账本证据可能包含真实项目上下文。 |
| 源 `openspec/changes/*` | change history 可能包含未发布示例，应使用公开 demo 材料重建。 |
