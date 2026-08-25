# Zimaflow

<p align="center">
  <a href="https://github.com/zima-explorer/zima-flow/releases"><img src="https://img.shields.io/github/v/release/zima-explorer/zima-flow?style=flat-square" alt="最新版本"></a>
  <a href="https://github.com/zima-explorer/zima-flow/stargazers"><img src="https://img.shields.io/github/stars/zima-explorer/zima-flow?style=flat-square&logo=github" alt="Stars"></a>
  <a href="https://github.com/zima-explorer/zima-flow/network/members"><img src="https://img.shields.io/github/forks/zima-explorer/zima-flow?style=flat-square" alt="Forks"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/zima-explorer/zima-flow?style=flat-square" alt="MIT 许可"></a>
</p>

[English](README.md) | [简体中文](README.zh-CN.md)

Zimaflow 把一句粗略的开发需求整理成可执行、可复核的工作流：路由需求、拆解任务、衔接 OpenSpec、检查实现、跨 session 交接，并沉淀可复用经验。支持 Claude Code、Codex 和 WorkBuddy。

## 快速开始

先安装你所使用宿主的 CLI。本仓库包含 Zimaflow 1.22.4。

Claude Code：

```sh
claude plugin marketplace add zima-explorer/zima-flow
claude plugin install zimaflow@zimaflow
```

Codex：

```sh
codex plugin marketplace add zima-explorer/zima-flow
codex plugin add zimaflow@zimaflow
```

## 受限网络

上面的 owner/repository 命令通过 GitHub HTTPS 获取仓库。若 HTTPS 受限，可通过 SSH clone 后，从父目录注册本地 checkout：

```sh
git clone git@github.com:zima-explorer/zima-flow.git
claude plugin marketplace add ./zima-flow
codex plugin marketplace add ./zima-flow
```

## 验证安装

```sh
claude plugin list
codex plugin list
```

WorkBuddy 使用已初始化的 Zimaflow 项目。项目至少应包含 `.zimaflow/project.yaml` 与 `openspec/config.yaml`：

```sh
ZIMAFLOW_ROOT=/absolute/path/to/zima-flow
PROJECT_ROOT=/absolute/path/to/your-project

"$ZIMAFLOW_ROOT/runtime/zimaflow/bin/zimaflow" --version
"$ZIMAFLOW_ROOT/runtime/zimaflow/bin/zimaflow" doctor workbuddy \
  --project "$PROJECT_ROOT" \
  --runtime-manifest "$ZIMAFLOW_ROOT/adapters/workbuddy/runtime-manifest.yaml"
```

## WorkBuddy

WorkBuddy 通过 `adapters/workbuddy/runtime-manifest.yaml` 使用 `runtime/zimaflow` 中的可移植运行时，不需要单独的 marketplace 入口。

## 更新或移除

```sh
claude plugin update zimaflow@zimaflow
claude plugin uninstall zimaflow@zimaflow
claude plugin marketplace remove zimaflow

codex plugin marketplace upgrade zimaflow
codex plugin remove zimaflow@zimaflow
codex plugin marketplace remove zimaflow
```

## 验证发行内容

在仓库根目录执行：

```sh
./verify-release.sh --distribution .
```

verifier 会检查版本、manifest 结构、artifact hash 与已记录 payload 是否发生漂移。

## 包含内容

- Claude Code plugin：`plugins/claude`
- Codex plugin：`plugins/codex`
- WorkBuddy adapter：`adapters/workbuddy`
- 共享 runtime：`runtime/zimaflow`

## 完整性与信任边界

`release-manifest.yaml` 记录了 artifact 与 payload 的预期 hash。verifier 会重新计算它们，用于发现 checkout 与已记录发行内容之间的漂移。

manifest 没有签名，因此这项检查不能证明发布者身份，也不构成密码学真实性证明。

## 许可证

Zimaflow 使用 MIT License。参见 [LICENSE](LICENSE) 与 [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES)。
