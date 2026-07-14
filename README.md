# zimaflow

[![CI](https://github.com/zima-explorer/zima-flow/actions/workflows/ci.yml/badge.svg)](https://github.com/zima-explorer/zima-flow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

zimaflow 是一套轻量 AI Coding 工作流，用来把一句粗略需求整理成可追踪的实现闭环。

它面向**个人开发者和小团队**：不追求企业级流程治理，而是用最少的约束把需求、规范、实现和收口串成一条可追踪、可交接的轻工作流。多数需求走 brief 就够，只有真正复杂的场景才升级到完整模式，避免小改动背上重流程的负担。

它不是完整的 agent 框架，不是项目管理系统，也不是个人工作区的镜像。v0.1 是经过公开发行审查的一条主链路，让读者可以完整体验：需求进入、需求契约、任务拆解、OpenSpec/Superpowers 衔接、合规检查、handover、session 收口和经验沉淀。

这条主链路包括：

1. 路由需求
2. 确认轻量需求契约
3. 将 first slice 拆成任务
4. 使用 OpenSpec 作为规范层
5. 用 Superpowers 风格的执行纪律进入实现
6. 在 session 之间交接上下文
7. 通过文档对账和经验沉淀完成收口

这个仓库是公开发行版。它比源工作区更小：这里只保留已审查的主链路。

## v0.1 纳入内容

| 范围 | 文件 | 状态 |
|------|------|------|
| 需求路由 | `skills/sdd-router.md` | 纳入 |
| 需求契约 | `skills/requirement-contract.md` | 纳入 |
| 任务拆解 | `skills/task-planning.md` | 纳入 |
| 路线决策 | `skills/route-decision-recorder.md` | 纳入 |
| OpenSpec 到执行衔接 | `skills/openspec-superpowers-bridge.md` | 纳入 |
| 规范合规检查 | `skills/spec-compliance-check.md` | 纳入 |
| handover | `skills/handover-manager.md` | 纳入 |
| session 收口 | `skills/session-close-reconciler.md` | 纳入 |
| 经验沉淀 | `skills/learn.md` | 纳入 |
| 参考表 | `references/*.md` | 纳入，已脱敏 |
| agent 规则 | `rules/` | 纳入 |
| 基础安装脚本 | `scripts/install.sh` | 纳入 |
| 最小 CLI | `bin/zimaflow` | 纳入 |

## v0.1 暂不开放内容

| 源模块 | v0.1 决策 | 原因 |
|--------|-----------|------|
| 完整项目初始化器 | 重写 | v0.1 基础安装脚本只安装公开仓内容，不初始化 OpenSpec、不维护项目注册表。 |
| `legacy-project-onboarding` | 暂缓 | 有价值，但超出首次体验主链路。 |
| `proto-review` | 暂缓 | 产品 UI 工作很有价值，但还需要独立的公开原型模板。 |
| 完整 CLI | 重写 | v0.1 只保留 `close`、`close --json`、`install-hooks`、`--help`、`--version`。 |
| knowledge ledger data | 移除 | 运行证据可能包含项目上下文，不作为示例数据发布。 |
| 源工作区 README.md / 路线图笔记 | 重写/移除 | 含未发布路线历史和未审查参考资料。 |

完整边界见 [docs/open-source-boundary.md](docs/open-source-boundary.md)。

## 目录关系

```text
zimaflow/
  skills/              # 主链路执行单元
  rules/               # 跨 skill 共享约束
  references/          # 辅助模板、矩阵和背景说明
  docs/                # 面向外部读者的人类文档
  examples/demo/       # v0.1 完整体验入口
  scripts/             # 基础安装脚本
  bin/                 # 最小 zimaflow CLI
```

`skills/` 描述 agent 应该怎么执行；`rules/` 保存跨 skill 的共同约束；`references/` 放可被 skill 引用的辅助材料；`docs/` 面向读者解释项目；`examples/demo/` 是最快体验 v0.1 主链路的入口。

## 快速开始

先读 [docs/getting-started.md](docs/getting-started.md)。

最短路径：

```bash
export ZIMAFLOW_HOME="$PWD"
export ZIMAFLOW_PROJECTS_DIR="$PWD/examples/demo/project-docs"
```

然后打开 [examples/demo/README.md](examples/demo/README.md)，按示例需求走一遍。

v0.1 提供基础安装脚本：

```bash
scripts/install.sh --target "$HOME/.zimaflow" --bin-dir "$HOME/.local/bin"
```

安装脚本只复制公开仓内容，不初始化 OpenSpec、不创建项目注册表、不修改 shell profile 或 agent 配置。

## 设计原则

- 多数小需求用 brief 就够，不强制完整 PRD。
- OpenSpec 负责规范层；完整模式的实现不应跳过规范上下文。
- handover 和收口检查是工作流的一部分，不是事后补丁。
- 公开发行文件必须脱敏，并且不依赖源工作区。

## 参与贡献

欢迎提 issue 和 PR。参与前请先读：

- [CONTRIBUTING.md](CONTRIBUTING.md) — 本地验证、公开措辞与脱敏要求、提交流程。
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — 社区行为准则。
- [SECURITY.md](SECURITY.md) — 安全问题请私下报告，勿走公开 issue。

日常使用问题、建议和交流，也可以在微信搜索并关注公众号 **zima-explorer**，私信反馈；公众号里也有一些 AI Coding 工作流的相关实践文章可供参考。安全漏洞请勿走公众号或公开 issue，见 [SECURITY.md](SECURITY.md)。

版本变更记录见 [CHANGELOG.md](CHANGELOG.md)。

## 许可证

本项目使用 [MIT 许可证](LICENSE)。
