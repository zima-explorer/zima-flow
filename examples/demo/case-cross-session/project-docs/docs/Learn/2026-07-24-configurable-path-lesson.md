# 经验候选 · 可配置 todo 路径

> 类型：lesson candidate
> change：add-configurable-todo-path

## 通用经验

- 给已有命令增加「输出/存储位置」这类参数时，用「显式参数 > 环境变量 > 默认值」的固定优先级，可以在不破坏既有默认行为的前提下扩展能力。
- 跨 session 的小需求，把 first slice 按 session 切分（S1 交接、S2 恢复），配合 `state` + `handover` + `recall`，可以让第二次进入时不重新考古。
- 验证证据应落成可复跑的脚本，而不是一句「我测过了」；`verify passed` 的输出本身就是 handover 里最可信的一行。

## 适用边界

- 仅适用于非破坏性的接口扩展；若要改既有输出格式或删除命令，应升级到完整模式并走 B4 破坏性变更审查。
