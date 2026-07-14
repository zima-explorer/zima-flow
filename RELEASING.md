# 发版检查清单（RELEASING）

> 本文面向维护者和参与发版的贡献者，不是普通使用文档。发布任何 v0.1 候选版本前，按此清单检查。

## 范围

- [ ] 确认 release 目标是 `v0.1`。
- [ ] 确认 release 包含一条完整主链路：需求进入、需求契约、任务拆解、OpenSpec/Superpowers bridge、合规检查、handover、session 收口和经验沉淀。
- [ ] 确认后续规划模块仍标记为后续规划或后续提供，尤其是完整项目初始化器、`proto-review`、legacy onboarding 和完整 CLI 打包。

## 公开内容审查

- [ ] README.md 第一屏解释 zimaflow 是什么。
- [ ] README.md 第一屏解释 zimaflow 不是什么。
- [ ] README.md 说明 v0.1 能让读者完整体验什么。
- [ ] README.md 链接到 demo 入口。
- [ ] 目录分工清楚：`skills/`、`rules/`、`references/`、`docs/`、`examples/demo/`。
- [ ] `docs/getting-started.md` 说明 v0.1 只有基础安装脚本，完整项目初始化器后续提供。
- [ ] `docs/open-source-boundary.md` 与仓库中实际存在的文件一致。
- [ ] 仓库中不包含迁移过程、筛选依据或只服务维护者的临时记录。

## skill 审查

- [ ] `skills/` 下每个文件都已做公开措辞审查。
- [ ] 没有任何 skill 依赖完整项目初始化器。
- [ ] 对后续规划模块的引用都明确标记为后续规划、后续提供或手动处理。
- [ ] 没有 skill 绑定某个人的本地工具链、项目注册表或工作目录。
- [ ] 没有 skill 包含真实客户、雇主、项目、仓库、事故或生产上下文。

## 脱敏扫描

做一次仓库级扫描，覆盖本机路径、工作区名、凭证词和已知源项目名。具体 pattern 可以放在 release issue 或终端历史中，不必硬编码进本清单。

```bash
rg -n "<release-sensitive-pattern>" README.md docs skills rules references examples scripts bin tests LICENSE .gitignore
```

对每个命中：

- [ ] 判断它是安全公开语境，还是必须改写。
- [ ] 改写不安全命中。
- [ ] 重新扫描，直到只剩有意保留的安全命中；最好零命中。

## demo

- [ ] 运行 `examples/demo/run-demo.sh`。
- [ ] 确认 demo 输出 `Demo 检查通过。`。
- [ ] 确认 `examples/demo/README.md` 指向所有预期产物。
- [ ] 确认 demo 不需要网络、凭证或外部服务。
- [ ] 运行 `tests/smoke.sh`。
- [ ] 确认 `scripts/install.sh --help` 可用。
- [ ] 确认 `bin/zimaflow --version` 可用。

## 文档链接检查

- [ ] 检查来自 `README.md` 的链接。
- [ ] 检查来自 `docs/getting-started.md` 的链接。
- [ ] 检查来自 `examples/demo/README.md` 的链接。
- [ ] 确认所有本地链接文件都存在。

## 许可证

- [ ] `LICENSE` 存在。
- [ ] v0.1 使用 MIT，除非未来 release 明确更换。
- [ ] README.md 没有暗示其他许可证。

## GitHub 发布前检查

- [ ] `git status --short` 只包含预期 release 文件。
- [ ] 没有 generated cache、本地环境文件或编辑器产物被暂存。
- [ ] remote URL 正确。
- [ ] 默认分支名符合预期。
- [ ] docs、demo 和扫描检查通过前，不创建 release tag。
- [ ] GitHub 仓库描述与 README.md 第一段一致。
