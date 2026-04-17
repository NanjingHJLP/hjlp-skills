# softwaremove

SoftwareMove 的有状态 CLI 工具。使用此 CLI 扫描已安装软件、将安装目录迁移到新位置、并从历史记录还原。

## 安装与运行

```bash
# 方式 1：安装到 PATH（推荐）
pip install -e .

# 方式 2：无需安装，直接运行
python -m softwaremove scan disk D
```

## 使用方法

```bash
# 启动交互式 REPL
softwaremove

# 查看磁盘列表
softwaremove disk list

# 扫描 D 盘上的已安装软件
softwaremove scan disk D

# 将软件目录迁移到新位置（自动创建链接）
softwaremove move start --source "D:\\Apps\\Foo" --target "E:\\SoftwareMovedFiles\\Foo"

# 验证搬迁结果
softwaremove move verify --id 1

# 根据 ID 从历史记录还原
softwaremove history restore --id 1
```

使用 `--json` 参数获取机器可读的 JSON 输出。如果命令未注册到 PATH，可用 `python -m softwaremove <子命令>` 代替。
