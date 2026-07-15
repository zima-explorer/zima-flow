## 改动说明

改了什么、为什么。

## 类型

- [ ] 文档
- [ ] skill / 规则措辞
- [ ] CLI / 安装脚本
- [ ] CI / 工程配置
- [ ] 其他：

## 验证

- [ ] `bin/zimaflow --version` 正常
- [ ] `scripts/install.sh --help` 正常
- [ ] `tests/smoke.sh` 通过
- [ ] `examples/demo/run-demo.sh` 输出 `Demo 检查通过。`

## 发行纪律

- [ ] 未引入本机路径（`/Users/...`、`/home/<name>/...`）
- [ ] 未引入真实客户 / 雇主 / 私有项目 / 生产上下文
- [ ] 如涉及"改 A 应同步 B"，已参考 `references/doc-sync-matrix.md` 更新相关文档
- [ ] 未在 v0.1 里补齐后续规划模块（`proto-review` / 完整 installer/CLI），或已在关联 issue 中确认

## 关联 issue

Closes #
