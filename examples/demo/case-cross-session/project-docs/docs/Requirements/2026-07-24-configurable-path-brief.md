# 可配置 todo 文件路径 · 需求 Brief

> 状态：已确认
> 日期：2026-07-24
> 来源：跨 session 案例
> 模式：brief（轻量需求契约）

- **目标**：给已有的本地 todo CLI 增加「可配置文件路径」，让用户不必固定使用当前目录下的 `.todo.txt`。
- **范围**：新增 `--file <path>` 参数与 `TODO_FILE` 环境变量两种指定方式；默认行为保持不变。
- **不做什么**：不做多文件合并、不做云同步、不做文件迁移工具、不改动 add/list/done 的既有语义。
- **验收标准**（优先 Given / When / Then，便于派生测试）：
  - Given 传入 `--file /tmp/x.txt`，When 执行 `add "Write README"`，Then 任务写入 `/tmp/x.txt` 而非默认文件。
  - Given 设置了 `TODO_FILE`，When 未传 `--file` 执行 `add`，Then 使用 `TODO_FILE` 指向的文件。
  - Given 既未传 `--file` 也未设 `TODO_FILE`，When 执行任意命令，Then 沿用默认 `.todo.txt`（行为不回归）。
  - （异常）Given 列表中没有任务 id `99`，When 执行 `done 99`，Then 报清晰的用户错误并以非 0 退出。
- **假设与默认值**：`--file` 优先级高于 `TODO_FILE`，二者都缺省时用 `.todo.txt`（AI 假设，已在本 brief 中确认）。
- **风险 / 待确认**：路径参数是本次唯一的公共接口变化，属低风险；无破坏性变更（未删命令、未改既有输出格式）。
