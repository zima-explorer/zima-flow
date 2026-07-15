# AGENTS.md

面向在本仓库工作的 AI coding agent 的约定。人类贡献者请看 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 这个仓库是什么

zimaflow 是一套轻量 AI Coding 工作流的公开发行版。仓库本身也用这套工作流维护，所以改动应遵循它描述的纪律。

## 开工前先读

- [`README.md`](README.md) — zimaflow 是什么、不是什么。
- [`docs/workflow-overview.md`](docs/workflow-overview.md) — 主链路各阶段职责。
- [`docs/open-source-boundary.md`](docs/open-source-boundary.md) — 哪些模块已纳入 v0.1、哪些属于后续规划。

## 基本约束

- 这是公开发行版，不是维护者的完整工作区。任何改动必须脱敏：不引入本机绝对路径（`/Users/...`、`/home/<name>/...`）、真实项目名、第三方名、密钥或私有上下文。
- 不要在 v0.1 里补齐标记为"后续提供"的模块（`proto-review`、完整初始化器、完整 CLI），除非已在 issue 中确认纳入。
- 提交前在本地跑通验证：`tests/smoke.sh` 和 `examples/demo/run-demo.sh`（CI 会跑同一套）。
- 若改动涉及"改 A 应同步 B"，参考 [`references/doc-sync-matrix.md`](references/doc-sync-matrix.md) 更新相关文档。

发版相关检查见 [`RELEASING.md`](RELEASING.md)。
