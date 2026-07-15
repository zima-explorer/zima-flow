# Todo CLI · 需求 Brief

> 状态：已确认
> 日期：2026-07-11
> 来源：demo 需求

- **目标**：构建一个很小的命令行 todo list，让用户能在本地添加、查看和完成任务。
- **范围**：支持 `add`、`list` 和 `done` 命令，使用本地 JSON 文件保存任务。
- **不做什么**：不做同步、认证、数据库、Web UI、提醒或重复任务。
- **验收标准**：
  - Given todo 文件为空，When 执行 `add "Write README"`，Then 列表显示 `Write README` 为待办
  - Given 列表中有任务 id `1`，When 执行 `done 1`，Then 列表显示任务 `1` 已完成
  - （异常）Given 列表中没有任务 id `99`，When 执行 `done 99`，Then 命令报告清晰的用户错误
- **假设与默认值**：文件位置默认使用当前目录下的 `.todo.json`（AI 假设，待用户 review）。
- **风险 / 待确认**：文件位置后续应可配置。
