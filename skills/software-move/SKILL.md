---
name: 软件搬家
description: 在磁盘间搬移已安装软件，支持扫描、目录迁移、链接创建和历史还原。当用户需要：（1）扫描磁盘上的已安装软件，（2）检测软件是否支持搬迁，（3）将软件安装目录迁移到其他磁盘，（4）在迁移后创建 NTFS junction/symbolic link，（5）从历史记录还原已迁移软件，（6）管理迁移/撤销/重做历史记录时触发。触发词："搬移软件"、"移动软件"、"software move"、"move installed software to another disk"。
---

# software-move

用于在磁盘间搬移已安装软件并支持历史还原的技能。

## 工作流程

1. **扫描** → `cli-anything-softwaremove scan disk <盘符>`
2. **检测** → `cli-anything-softwaremove move check --source <路径> --name <名称>`
3. **迁移** → `cli-anything-softwaremove move start --source <源路径> --target <目标路径>`
4. **链接** → 迁移时自动创建
5. **还原** → `cli-anything-softwaremove history restore --id <编号>`

## 命令

```bash
# 扫描磁盘上的软件
cli-anything-softwaremove scan disk D

# 检测软件是否支持搬迁（推荐迁移前执行）
cli-anything-softwaremove move check --source "C:\\Users\\1\\AppData\\Local\\Figma" --name "Figma"

# 迁移软件目录
cli-anything-softwaremove move start --source "D:\\Apps\\Foo" --target "E:\\SoftwareMoved\\Foo"

# 从历史记录还原
cli-anything-softwaremove history restore --id 1

# 撤销上一次迁移
cli-anything-softwaremove history undo

# 查看历史记录
cli-anything-softwaremove history list
```

## 关键要点

- **迁移前先检测**：用 `move check` 检测软件是否支持搬迁（UWP 应用不支持 junction）
- 源路径必须存在，且为软件安装目录
- 目标路径应位于目标磁盘上，且有足够空间
- 链接（junction points）在迁移后自动创建
- 每次迁移操作都会记录在历史中，支持撤销/重做
- 基于 Windows 注册表检测软件

## 迁移检测说明

`move check` 会检测以下情况：
- **UWP/MSIX 应用**：不支持 junction 链接方式
- **注册表路径引用**：迁移后可能需要手动更新注册表
- **被锁定的文件**：迁移时将跳过
- **不建议搬迁的应用**：百度网盘等 UWP 应用
