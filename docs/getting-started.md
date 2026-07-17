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

安装脚本只复制 `skills/`、`rules/`、`references/`，并可选安装 `bin/zimaflow` 或显式指定的 agent skill root。它不使用网络、不写入 shell profile、不修改任何 agent 配置、不初始化 OpenSpec、不创建项目注册表或项目文档目录。

安装后请把 `ZIMAFLOW_HOME` 指向目标目录，skill 内部对 `references/` 的引用统一使用 `$ZIMAFLOW_HOME/references/`：

```bash
export ZIMAFLOW_HOME="$HOME/.zimaflow"
```

如目标目录已有文件，默认不会覆盖；确认要覆盖时使用：

```bash
scripts/install.sh --target "$HOME/.zimaflow" --force
```

### 让 agent 自动发现 skills

`skills/` 下是扁平的 `*.md` 文件。部分 agent 只发现“每个 skill 一个独立文件夹，文件名必须是 `SKILL.md`”的结构，因此直接把扁平文件复制到项目里，可能不会被自动扫描。

如果你已经让多个 agent 扫描同一个全局 skill root，把 zimaflow 安装到这个 root：

```bash
scripts/install.sh --target "$HOME/.zimaflow" \
  --agent-skill-root "$HOME/agent_skills"
# 生成 $HOME/agent_skills/zimaflow-<name>/SKILL.md
```

如果各 agent 各自维护全局 skill root，分别指定：

```bash
scripts/install.sh --target "$HOME/.zimaflow" \
  --claude-skill-root "$HOME/.claude/skills" \
  --codex-skill-root "$HOME/.agents/skills" \
  --workbuddy-skill-root "$HOME/.workbuddy/skills"
# 分别生成 <root>/zimaflow-<name>/SKILL.md
```

全局 skill root 采用扁平一层的 `zimaflow-<name>/SKILL.md`，不生成 `zimaflow/<name>/SKILL.md`。原因是不同 agent 对 skill root 的递归扫描能力不一致；例如 Claude Code 的 nested discovery 是在工作树不同层级发现各自的 `.claude/skills/`，不能等同于在一个全局 `skills/` 目录内递归发现分组子目录。扁平前缀同时避免文件路径冲突和 frontmatter `name` 冲突。

如果只想让某个项目自动发现，把 `--target` 指向项目根目录并生成项目级 adapter：

```bash
scripts/install.sh --target /path/to/project --claude-code
# 生成 /path/to/project/.claude/skills/zimaflow-<name>/SKILL.md

scripts/install.sh --target /path/to/project --codex
# 生成 /path/to/project/.agents/skills/zimaflow-<name>/SKILL.md
```

`--agent-skill-root` 和 `--*-skill-root` 只写入用户显式传入的目录；脚本不会替你配置 agent 去扫描该目录。WorkBuddy 等未在 v0.1 中声明默认目录的 agent，应使用它实际配置的 skill root。

## 4. 手动使用

如果不运行安装脚本，也可以采用以下方式：

- 让 agent 读取 `skills/` 中的文件，并按主链路执行。
- 若目标是 **Claude Code**：把每个 `skills/<name>.md` 放成 `.claude/skills/zimaflow-<name>/SKILL.md`，并将 frontmatter `name` 同步设为 `zimaflow-<name>`，否则不会被自动发现或会因校验不一致失败。
- 若目标是 **Codex**：把每个 `skills/<name>.md` 放成 `.agents/skills/zimaflow-<name>/SKILL.md`，并将 frontmatter `name` 同步设为 `zimaflow-<name>`。
- 若目标是某个全局 skill root：把每个 `skills/<name>.md` 放成 `<root>/zimaflow-<name>/SKILL.md`，将 frontmatter `name` 同步设为 `zimaflow-<name>`，并确认 agent 已配置扫描 `<root>`。
- 若目标 agent 没有公开或已验证的自动发现目录：保持使用 `skills/` 扁平源文件，并在 agent 指令中显式要求读取入口 skill。
- 将 `rules/` 和 `references/` 与 skills 放在一起，并把 `ZIMAFLOW_HOME` 指向其所在目录，确保 `$ZIMAFLOW_HOME/references/` 引用可解析。

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
- v0.1 不会自动修改任何 agent 配置；全局可发现需要用户先让 agent 扫描对应 skill root。
- `proto-review`、完整初始化器和完整 CLI 暂不属于首发边界（`legacy-project-onboarding` 已纳入 v0.1）。
