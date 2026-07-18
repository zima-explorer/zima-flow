# zimaflow v0.1.0 — 首次公开发行 🎉

zimaflow 是一套面向个人开发者和小团队的轻量 AI Coding 工作流，把一句粗略需求整理成可追踪、可交接的实现闭环。多数需求走 brief 就够，只有复杂场景才升级完整模式，避免小改动背上重流程。

v0.1 只保留一条经过发行审查的主链路：**需求进入 → 需求契约 → 任务拆解 → OpenSpec/Superpowers 衔接 → 合规检查 → handover → session 收口 → 经验沉淀。**

## 本次纳入

- **主链路 skills**：sdd-router、requirement-contract、task-planning、route-decision-recorder、openspec-superpowers-bridge、spec-compliance-check、session-close-reconciler、handover-manager、learn
- **老项目认知底座**：`legacy-project-onboarding`，给存量代码库建立架构总览、接口清单、数据模型/ER、关键链路和隐性知识问答，并产出 thin context index
- **工程护栏**：需求契约的 Given/When/Then 验收标准与反问上限；合规检查的破坏性变更（B4）与沿用抽象（B5）门槛；收口的 hotfix / rewind / secrets Guardrail；sdd-router 的排障路径、P1/P2/P3 变更分级与 rewind 识别
- **参考表**：`references/` 下已脱敏的通用字典、矩阵与设计说明（工时字典、知识锚点映射、知识使用指南、文档同步矩阵、认知底座与 state 设计、通用经验库种子）
- **agent 规则**：`rules/`（Claude、Codex）面向公开使用的最小规则片段
- **最小 CLI**：`bin/zimaflow`，提供 `close`、JSON 输出和 reminder-only git hook；它是可选便利入口和机器探针，不是完整工作流引擎
- **基础安装脚本**：`scripts/install.sh`，仅复制公开仓内容，不做 OpenSpec 初始化或项目注册；需要一层 `SKILL.md` 自动发现结构时，可用 `--adapter-dir` 生成 `zimaflow-<name>` adapter，Claude Code 项目内场景可用 `--claude-code`
- **端到端 demo**：`examples/demo/`，无网络、无凭证，一条命令走通"需求 → handover"
- **工程配置**：MIT LICENSE、CI、CONTRIBUTING、SECURITY、CODE_OF_CONDUCT

## 后续规划（计划提供）

- **产品原型评审（`proto-review`）**：从想法或 PRD 生成可评审原型，先可视化评审再进 OpenSpec
- **一键初始化器与完整 CLI**：一条命令接入新项目；CLI 增加 per-change 状态、知识淘汰复查、artifact 漂移检查
- **知识使用闭环**：留痕账本加引用/应用证据加淘汰复查，让经验可追踪

## 快速开始

见 [docs/getting-started.md](getting-started.md)，或直接跑 `examples/demo/run-demo.sh` 体验主链路。

---

日常交流欢迎关注微信公众号 **zima-explorer**。完整变更记录见 [CHANGELOG.md](../CHANGELOG.md)。
