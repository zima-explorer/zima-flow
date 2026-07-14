# zimaflow v0.1.0 — 首次公开发行 🎉

zimaflow 是一套面向个人开发者和小团队的轻量 AI Coding 工作流，把一句粗略需求整理成可追踪、可交接的实现闭环。多数需求走 brief 就够，只有复杂场景才升级完整模式，避免小改动背上重流程。

v0.1 只保留一条经过发行审查的主链路：**需求进入 → 需求契约 → 任务拆解 → OpenSpec/Superpowers 衔接 → 合规检查 → handover → session 收口 → 经验沉淀。**

## 本次纳入

- **主链路 skills**：sdd-router、requirement-contract、task-planning、route-decision-recorder、openspec-superpowers-bridge、spec-compliance-check、session-close-reconciler、handover-manager、learn
- **参考表**：`references/` 下已脱敏的通用字典与矩阵（工时字典、知识锚点映射、知识使用指南、文档同步矩阵）
- **agent 规则**：`rules/`（Claude、Codex）面向公开使用的最小规则片段
- **最小 CLI**：`bin/zimaflow`，提供 `close`、JSON 输出和 reminder-only git hook
- **基础安装脚本**：`scripts/install.sh`，仅复制公开仓内容，不做 OpenSpec 初始化或项目注册
- **端到端 demo**：`examples/demo/`，无网络、无凭证，一条命令走通"需求 → handover"
- **工程配置**：MIT LICENSE、CI、CONTRIBUTING、SECURITY、CODE_OF_CONDUCT

## 暂缓（后续版本提供）

- `proto-review`：需要公开原型模板和示例资产后再纳入
- `legacy-project-onboarding`：存量项目冷启动，不属首次 demo 主链路
- 完整项目初始化器与完整 CLI：v0.1 只保留通用命令与基础安装

## 快速开始

见 [docs/getting-started.md](getting-started.md)，或直接跑 `examples/demo/run-demo.sh` 体验主链路。

---

日常交流欢迎关注微信公众号 **zima-explorer**。完整变更记录见 [CHANGELOG.md](../CHANGELOG.md)。
