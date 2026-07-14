# 快速开始

本指南用于体验 v0.1 工作流。v0.1 提供基础安装脚本，但完整项目初始化器后续提供。

## 1. 打开仓库

将仓库根目录作为 `ZIMAFLOW_HOME`：

```bash
cd /path/to/zimaflow
export ZIMAFLOW_HOME="$PWD"
```

demo 使用仓库内置的 project-docs 目录：

```bash
export ZIMAFLOW_PROJECTS_DIR="$PWD/examples/demo/project-docs"
```

## 2. 阅读主链路 skills

首次体验路径如下：

```text
skills/sdd-router.md
skills/requirement-contract.md
skills/task-planning.md
skills/route-decision-recorder.md
skills/openspec-superpowers-bridge.md
skills/spec-compliance-check.md
skills/session-close-reconciler.md
skills/handover-manager.md
skills/learn.md
```

你可以把这些文件作为 agent skills 使用，也可以把它们当作人工评估工作流的检查清单。

## 3. 基础安装

将公开仓内容安装到目标目录：

```bash
scripts/install.sh --target "$HOME/.zimaflow"
```

同时安装最小 CLI：

```bash
scripts/install.sh --target "$HOME/.zimaflow" --bin-dir "$HOME/.local/bin"
```

安装脚本只复制 `skills/`、`rules/`、`references/`，并可选安装 `bin/zimaflow`。它不使用网络、不写入 shell profile、不修改 Codex/Claude Code/Cursor/WorkBuddy 配置、不初始化 OpenSpec、不创建项目注册表或项目文档目录。

如目标目录已有文件，默认不会覆盖；确认要覆盖时使用：

```bash
scripts/install.sh --target "$HOME/.zimaflow" --force
```

## 4. 手动使用

如果不运行安装脚本，也可以采用以下方式：

- 让 agent 读取 `skills/` 中的文件，并按主链路执行。
- 只将 v0.1 的 skill 文件复制到本地 agent skill 目录。
- 将 `rules/` 和 `references/` 与 skills 放在一起，确保链接和共享约束仍可访问。

## 5. 运行 demo

打开：

```text
examples/demo/README.md
```

demo 从一句需求开始：

```text
Add a tiny todo list CLI that can add, list, and complete tasks.
```

它会展示用户在 v0.1 主链路中应看到的产物：

- 需求 brief
- 任务计划
- OpenSpec change 骨架
- 实现交接说明
- 收口检查清单
- 经验候选

## 6. 用在真实项目上

创建项目文档目录，并将 `ZIMAFLOW_PROJECTS_DIR` 指向它：

```bash
mkdir -p "$HOME/projects-docs/my-app/docs"
export ZIMAFLOW_PROJECTS_DIR="$HOME/projects-docs"
```

然后让 agent 从 `skills/sdd-router.md` 开始，并使用项目文档目录作为持久上下文位置。

## 当前限制

- v0.1 只提供基础安装脚本；完整项目初始化器后续提供。
- v0.1 不会自动链接 skills 到特定 agent 的 skill 目录。
- `proto-review` 和 legacy onboarding 暂不属于首发边界。
