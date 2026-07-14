# Changelog

本文件记录 zimaflow 公开发行版的显著变更。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.1.0] — 2026-07-14

首次公开发行。仅包含一条经过发行审查的主链路：从一句粗略需求到可追踪的实现闭环。

### 纳入

- **主链路 skills**：`sdd-router`、`requirement-contract`、`task-planning`、`route-decision-recorder`、`openspec-superpowers-bridge`、`spec-compliance-check`、`session-close-reconciler`、`handover-manager`、`learn`。
- **参考表**：`references/` 下已脱敏的通用字典与矩阵（工时字典、知识锚点映射、知识使用指南、文档同步矩阵）。
- **agent 规则**：`rules/`（Claude、Codex）下面向公开使用的最小规则片段。
- **最小 CLI**：`bin/zimaflow`，提供 `close`、JSON 输出和 reminder-only git hook。
- **基础安装脚本**：`scripts/install.sh`，仅复制公开仓内容，不做 OpenSpec 初始化、项目注册或项目文档目录创建。
- **文档**：`docs/getting-started.md`、`docs/workflow-overview.md`、`docs/open-source-boundary.md`；面向维护者的 `RELEASING.md`。
- **端到端 demo**：`examples/demo/`，无网络、无凭证，`run-demo.sh` 走通"需求 → handover"全过程。
- **工程配置**：`LICENSE`（MIT）、`.gitignore`、`AGENTS.md`、`tests/smoke.sh`。

### 暂缓（后续版本提供）

- `proto-review`：需要公开原型模板和示例资产后再纳入。
- `legacy-project-onboarding`：存量项目冷启动，不属首次 demo 主链路。
- 完整项目初始化器与完整 CLI：v0.1 只保留通用命令与基础安装。

[Unreleased]: https://github.com/zima-explorer/zima-flow/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/zima-explorer/zima-flow/releases/tag/v0.1.0
