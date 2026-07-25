# CLI Reference

`bin/zimaflow` 是 zimaflow 的确定性辅助层。它不替代 skills，也不自动执行需求、实现或发布；它只做轻量读取、检查和提醒。

## `close`

```bash
bin/zimaflow close
bin/zimaflow close --json
```

检查当前 git 仓库是否干净，并汇总 active `.zimaflow-state.yaml`。`--json` 输出稳定字段，便于 agent 或脚本读取。

核心字段：

- `repository`
- `git_status`
- `dirty_count`
- `active_state_count`
- `active_state_changes`
- `next_action`

## `state`

```bash
bin/zimaflow state
bin/zimaflow state --json
bin/zimaflow state init <change> [options]
bin/zimaflow state update <change> [options]
```

读取或写入 `openspec/changes/<change>/.zimaflow-state.yaml`。state 只记录机器可读的短状态，不替代 requirement contract、decision、OpenSpec 文档或 handover。

常用写入选项：

- `--phase <phase>`
- `--mode <mode>`
- `--contract <path>`
- `--decision <path>`
- `--branch <branch>`
- `--worktree <path>`
- `--verify <status>`
- `--full-tests <status>`
- `--last-command <command>`
- `--last-result <result>`
- `--evidence-path <path-or-url>`
- `--blocked-reason <reason>`
- `--archive-status <status>`
- `--handover <path>`

## `recall`

```bash
bin/zimaflow recall
bin/zimaflow recall --json
bin/zimaflow recall --days 14
bin/zimaflow recall --summary-lines 3
```

汇总当前仓库里的 active change、验证状态、handover 指针和 bit-rot 提醒，用来在跨 session 时恢复上下文。

公开版 first slice 只支持单仓 recall。`recall --all` 和 `recall --project` 暂不开放，因为它们需要项目注册表约定，容易把维护者工作区布局变成用户的隐式依赖。

`recall` 是只读命令：不修改 state、不刷新 handover、不运行测试、不触发 CI。

## `install-hooks`

```bash
bin/zimaflow install-hooks
```

在当前 git 仓库安装 reminder-only hooks。它只提示可以运行 `zimaflow close`，不阻断 commit 或 push。
