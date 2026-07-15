# 贡献指南

感谢你对 zimaflow 的关注。zimaflow 是一套轻量 AI Coding 工作流，v0.1 只保留一条经过公开发行审查的主链路。为了让仓库保持这种"干净主链路"的定位，贡献前请先读完本指南。

## 先了解范围

这个仓库是公开发行版，不是维护者的完整工作区。在提交改动前，请先看：

- [`README.md`](README.md) — zimaflow 是什么、不是什么。
- [`docs/workflow-overview.md`](docs/workflow-overview.md) — 主链路各阶段职责。
- [`docs/open-source-boundary.md`](docs/open-source-boundary.md) — 哪些模块纳入、哪些属于后续规划。

`proto-review`、完整 installer 和完整 CLI 已明确标记为**后续提供**。请不要在 v0.1 里补齐它们，除非事先在 issue 中讨论并确认纳入。（`legacy-project-onboarding` 已纳入 v0.1。）

## 本地验证

任何改动在提 PR 前，都应在本地跑通以下检查（CI 也会跑同一套）：

```bash
# CLI 可用
bin/zimaflow --version

# 安装脚本帮助
scripts/install.sh --help

# 冒烟测试（安装 + close JSON）
tests/smoke.sh

# demo 主链路
examples/demo/run-demo.sh
```

`run-demo.sh` 必须输出 `Demo 检查通过。`，`smoke.sh` 必须输出 `smoke tests passed`。

## 公开措辞与脱敏

这是发行版最重要的一条纪律。提交的内容里**不得**包含：

- 本机绝对路径（如 `/Users/...`、`/home/<name>/...`）。
- 真实客户、雇主、私有项目、内部仓库、事故或生产上下文。
- 凭证、token、密钥或个人邮箱以外的敏感联系方式。
- 只服务维护者的临时记录、迁移过程或筛选依据。

提交前请自查一遍。CI 会做一次本机路径扫描，命中即失败。references 下的字典和矩阵应保持通用、可复用，不绑定任何具体项目。

## 提交流程

1. Fork 并基于 `main` 建分支，分支名简述意图（如 `docs/fix-link`、`skill/router-wording`）。
2. 保持每个 PR 聚焦一件事，改动尽量小而清晰。
3. 本地跑通上面的验证命令。
4. 在 PR 描述里说明：改了什么、为什么、如何验证。
5. 如果改动涉及"改了 A 就该同步 B"，参考 [`references/doc-sync-matrix.md`](references/doc-sync-matrix.md) 一并更新相关文档。

## commit 措辞

用简洁的祈使句，一行说清意图。示例：

```
docs: fix broken link in getting-started
skill: clarify router lightweight-mode wording
ci: run demo walkthrough on pull requests
```

## 报告问题

Bug 和功能建议都走 GitHub Issues，请使用对应模板。涉及安全的问题不要走公开 issue，见 [`SECURITY.md`](SECURITY.md)。
