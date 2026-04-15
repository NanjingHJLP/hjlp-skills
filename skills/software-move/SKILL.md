---
name: software-move
description: >
  在磁盘间搬移已安装软件，支持扫描、目录迁移、链接创建和历史还原。
  当用户需要：（1）扫描磁盘上的已安装软件，（2）检测软件是否支持搬迁，
  （3）将软件安装目录迁移到其他磁盘，（4）在迁移后创建 NTFS junction/symbolic link，
  （5）从历史记录还原已迁移软件，（6）管理迁移/撤销/重做历史记录时触发。
  触发词："搬移软件"、"移动软件"、"software move"、"move installed software to another disk"。
---

# software-move

用于在磁盘间搬移已安装软件并支持历史还原的技能。

## 安装

```bash
cd scripts && pip install -e .
```

## 工作流程

1. **扫描** → `softwaremove scan disk <盘符>`
2. **检测** → `softwaremove move check --source <路径> --name <名称>`
3. **迁移** → `softwaremove move start --source <源路径> --target <目标路径>`
4. **还原** → `softwaremove history restore --id <编号>`

## 常用命令

```bash
# 扫描磁盘
softwaremove scan disk D

# 检测软件是否可搬移
softwaremove move check --source "C:\Users\1\AppData\Local\Figma" --name "Figma"

# 搬移软件（Program Files 目录需加 --admin）
softwaremove move start --source "C:\Program Files\Docker\Docker" --target "D:\SoftwareMoved\Docker" --admin

# 查看历史记录
softwaremove history list

# 撤销上一次迁移
softwaremove history undo
```

## 管理员权限

`C:\Program Files`、`C:\Program Files (x86)`、`C:\Windows` 下的软件需要管理员权限才能创建 junction 链接。迁移时添加 `--admin` 参数自动请求 UAC 提权。

## 执行前提醒（Agent 必读）

在执行任何需要 `--admin` 的操作（包括 `move start`、`history restore`、`history undo`、`history redo`）之前，Agent **必须**先向用户发送以下提醒：

> 即将执行软件搬家/还原操作。过程中可能会弹出一个新的终端窗口（UAC 提权），**请不要关闭该窗口**，等操作执行完成后它会自动关闭。

待用户确认收到提醒后，再执行实际命令。

## 参考文档

- [完整使用说明与命令详解](references/USAGE.md)
- [CLI 实现说明](references/SOFTWAREMOVE.md)
- [README - 开发与安装](references/README.md)
- [测试计划](references/TEST.md)
