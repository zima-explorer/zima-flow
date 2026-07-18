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

可选：安装最小 CLI。它只提供 `zimaflow close`、`zimaflow close --json` 和非阻断 hook 提醒，方便在任意项目目录快速检查收口状态；完整工作流仍由 skills 执行。

```bash
scripts/install.sh --target "$HOME/.zimaflow" --bin-dir "$HOME/.local/bin"
```

安装脚本只复制 `skills/`、`rules/`、`references/`，并可选安装最小 CLI 或向显式指定的 `--adapter-dir` 生成自动发现 adapter。它不使用网络、不写入 shell profile、不修改任何 agent 配置、不初始化 OpenSpec、不创建项目注册表或项目文档目录。

安装后请把 `ZIMAFLOW_HOME` 指向目标目录，skill 内部对 `references/` 的引用统一使用 `$ZIMAFLOW_HOME/references/`：

```bash
export ZIMAFLOW_HOME="$HOME/.zimaflow"
```

如目标目录已有文件，默认不会覆盖；确认要覆盖时使用：

```bash
scripts/install.sh --target "$HOME/.zimaflow" --force
```

### 让 agent 自动发现 skills

`skills/` 下是 zimaflow 的中立源文件。Codex、WorkBuddy 等在你显式指定源目录或运行环境支持递归读取时，优先直接使用仓库里的源文件，不需要为它们生成特殊命名；如果你希望某个 agent 走自动发现，仍要按该 agent 实际扫描的结构生成 adapter。

Claude Code 的全局 skill 发现机制比较特殊：它只扫描 `<skill-root>/<skill>/SKILL.md` 这一层，不会递归理解 `skills/*.md` 这样的源结构。因此，只有在你希望 Claude Code 自动发现 zimaflow skills 时，才需要生成扁平 adapter。

如果你已经让多个 agent 扫描同一个全局 skill root，也可以把 adapter 安装到这个 root：

```bash
scripts/install.sh --target "$HOME/.zimaflow" \
  --adapter-dir "/path/to/global-skill-root"
# 生成 /path/to/global-skill-root/zimaflow-<name>/SKILL.md
```

如果各 agent 各自维护全局 skill root，只给确实需要 adapter 的 agent 指定对应 root。最常见的是 Claude Code：

```bash
scripts/install.sh --target "$HOME/.zimaflow" \
  --adapter-dir "$HOME/.claude/skills"
# 生成 $HOME/.claude/skills/zimaflow-<name>/SKILL.md
```

adapter 采用扁平一层的 `zimaflow-<name>/SKILL.md`，不生成 `zimaflow/<name>/SKILL.md`。这个命名是 runtime 兼容层，不是源码组织方式；它主要服务 Claude Code 自动发现，同时避免文件路径冲突和 frontmatter `name` 冲突。

如果只想让某个项目里的 Claude Code 自动发现，把 `--target` 指向项目根目录并使用 `--claude-code`：

```bash
scripts/install.sh --target /path/to/project --claude-code
# 生成 /path/to/project/.claude/skills/zimaflow-<name>/SKILL.md
```

`--adapter-dir` 只写入用户显式传入的目录；脚本不会替你配置 agent 去扫描该目录。WorkBuddy 等未在 v0.1 中声明默认目录的 agent，应使用它实际配置的 skill root。

## 4. 手动使用

如果不运行安装脚本，也可以采用以下方式：

- 让 agent 直接读取仓库中的 `skills/` 源文件，并按主链路执行；能递归读取或支持显式路径的 agent 推荐这样做。
- 若目标是 **Claude Code**：把每个 `skills/<name>.md` 放成 `.claude/skills/zimaflow-<name>/SKILL.md`，并将 frontmatter `name` 同步设为 `zimaflow-<name>`，否则不会被自动发现或会因校验不一致失败。
- 若目标是 **Codex / WorkBuddy**：优先配置或指向 zimaflow 源目录；仅当你的具体运行环境也要求 `<skill>/SKILL.md` 一层结构时，才生成 `zimaflow-<name>` adapter。
- 若目标是某个全局 skill root：只有确认该 agent 需要一层 `SKILL.md` adapter 时，才把每个 `skills/<name>.md` 放成 `<root>/zimaflow-<name>/SKILL.md`，并将 frontmatter `name` 同步设为 `zimaflow-<name>`。
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
