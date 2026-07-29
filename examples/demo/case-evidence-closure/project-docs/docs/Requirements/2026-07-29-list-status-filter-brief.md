# todo list 状态筛选 · 需求 brief

> 类型：需求 brief（轻量模式最小字段）
> 依据模板：`skills/requirement-contract.md`
> 日期：2026-07-29
> 变更名：list-status-filter

## 意图锁

给 `todo.sh list` 增加一个状态开关，让用户能只看未完成或只看已完成——**只加入口，不改数据**。

这句话是本轮的对照基准：收口时逐条回看，凡是超出「加一个读取侧开关」的改动都算跑偏。

## 范围

- `todo.sh list` 支持 `--status pending|done|all`
- `--status` 与 `--file` 一样，可出现在子命令之前或之后
- 不传 `--status` 时等价于 `--status all`（默认行为不变）
- `--status` 取值非法时报清晰错误并以非 0 退出

## 不做什么

- **不改持久化格式**：仍是行式 `id|done|title`，不新增字段、不做迁移
- **不做 JSON 输出**：`--json` / 结构化输出不在本轮
- **不做日期过滤**：`todo.sh` 没有存创建时间，做这个要先加字段，属另一个需求
- **不改 `add` / `done` 的行为与输出格式**
- **不写 OpenSpec 三件套**：本需求纯读、不改 schema、不涉权限与数据写入路径，风险低。规范的作用由下方 Given/When/Then 承担，计划的作用由[轻量任务台账](../Tasks/2026-07-29-list-status-filter-tasks.md)承担

## 怎么算做完

- **场景 1**：Given 列表中同时有未完成和已完成任务，When 执行 `list --status pending`，Then 输出包含未完成任务，且**不包含**任何已完成任务
- **场景 2**：Given 同上，When 执行 `list --status done`，Then 输出包含已完成任务，且**不包含**任何未完成任务
- **场景 3**：Given 同上，When 执行不带 `--status` 的 `list`，Then 输出与 `list --status all` **完全一致**（默认行为不回归）
- **场景 4（异常路径）**：Given 任意列表，When 执行 `list --status bogus`，Then 打印说明可选值的错误信息，并以非 0 退出码结束
- **场景 5（组合）**：Given 用 `--file` 指定了另一个 todo 文件，When 执行 `list --status pending`，Then 只读取该文件的内容，`--file` 能力不被破坏

场景 1、2 的「不包含」部分是**有意写进验收标准**的：只要求「目标项存在」时，即使筛选完全没生效也会通过。

## 假设与默认值

- 默认值取 `all` 而不是 `pending`：默认行为不回归优先于「猜用户想看什么」
- 取值集合固定为三个字面量，不做前缀匹配、不做大小写归一（保持纯 bash、无版本敏感逻辑）

## 风险

- 低。纯读命令，无数据写入；唯一的回归面是 `list` 的默认输出，已由场景 3 锁定
