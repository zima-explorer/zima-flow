# Changelog

本文件记录 zimaflow 公开发行版的显著变更。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.1.0] — 2026-07-15

首次公开发行。包含一条经过发行审查的主链路（从一句粗略需求到可追踪的实现闭环），以及一层贯穿主链路的工程护栏。

### 纳入

- **主链路 skills**：`sdd-router`、`requirement-contract`、`task-planning`、`route-decision-recorder`、`openspec-superpowers-bridge`、`spec-compliance-check`、`session-close-reconciler`、`handover-manager`、`learn`。
- **老项目认知底座**：`legacy-project-onboarding`，为存量代码库建立架构总览、模块地图、接口清单、数据模型/ER、测试入口、关键链路和隐性知识问答，并产出 thin context index。
- **工程护栏**：
  - `requirement-contract` 验收标准优先 Given/When/Then 三段式，反问上限（最多 2 轮）与假设默认值。
  - `spec-compliance-check` 破坏性变更门槛（B4：删码≥5行 / 改公共接口 / 改 schema / 改权限 / 改写库路径先排查引用面）与沿用现有抽象检查（B5）；均为审查标记，不自动回滚或改代码。
  - `sdd-router` 问题排障 / 故障定位路径、P1/P2/P3 需求变更影响分级、纠偏 / rewind 识别、thin context-index 读取和未关闭 state 检测。
  - `session-close-reconciler` hotfix / rewind / secrets 三类 Guardrail 收口核对与 `.zimaflow-state.yaml` 状态对账。
  - `handover-manager` Guardrail 承接段落、Zimaflow State 与 Context Index 读写。
- **参考表**：`references/` 下已脱敏的通用字典、矩阵与设计说明（工时字典、知识锚点映射、知识使用指南、文档同步矩阵、`Design-Context-Intelligence-Baseline.md`、`Design-Zimaflow-State.md`、`lessons-common.md` 通用经验库种子）。
- **agent 规则**：`rules/`（Claude、Codex）下面向公开使用的最小规则片段。
- **最小 CLI**：`bin/zimaflow`，提供 `close`、JSON 输出和 reminder-only git hook。
- **基础安装脚本**：`scripts/install.sh`，仅复制公开仓内容，不做 OpenSpec 初始化、项目注册或项目文档目录创建。
- **文档**：`docs/getting-started.md`、`docs/workflow-overview.md`、`docs/open-source-boundary.md`；面向维护者的 `RELEASING.md`。
- **端到端 demo**：`examples/demo/`，无网络、无凭证，`run-demo.sh` 走通"需求 → handover"全过程。
- **工程配置**：`LICENSE`（MIT）、`.gitignore`、`AGENTS.md`、`tests/smoke.sh`。

### 后续规划（计划提供）

- `proto-review`：产品原型评审，需公开原型模板和示例资产后开放。
- 一键初始化器与完整 CLI（per-change 状态、知识淘汰复查、artifact 漂移检查）。
- 知识使用闭环：留痕账本加淘汰复查。

[Unreleased]: https://github.com/zima-explorer/zima-flow/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/zima-explorer/zima-flow/releases/tag/v0.1.0
