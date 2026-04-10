# cli-anything-softwaremove

SoftwareMove 的有状态 CLI 工具。使用此 CLI 扫描已安装软件、将安装目录迁移到新位置、并从历史记录还原。

## 安装

```bash
pip install -e .
```

## 使用方法

```bash
# 启动交互式 REPL
cli-anything-softwaremove

# 查看磁盘列表
cli-anything-softwaremove disk list

# 扫描 D 盘上的已安装软件
cli-anything-softwaremove scan disk D

# 将软件目录迁移到新位置（自动创建链接）
cli-anything-softwaremove move start --source "D:\\Apps\\Foo" --target "E:\\SoftwareMovedFiles\\Foo"

# 根据 ID 从历史记录还原
cli-anything-softwaremove history restore --id 1
```

使用 `--json` 参数获取机器可读的 JSON 输出。
