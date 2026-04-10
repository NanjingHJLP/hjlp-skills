---
name: 桌面整理
description: 桌面图标整理工具 自动扫描用户桌面和公用桌面 按文件类型分类整理到不同文件夹中 生成详细的移动计划 执行前征求用户批准 支持恢复到整理前状态 适用于需要整理混乱桌面 按类型组织文件的场景
---

# 桌面图标整理器

自动扫描用户桌面和公用桌面，智能分类整理文件到对应文件夹。

## 功能特点

- **双桌面扫描**: 同时处理用户桌面和公用桌面
- **智能分类**: 按文件类型自动分类（文档、图片、视频、音频、压缩包、程序、代码、快捷方式等）
- **中文文件夹**: 使用中文分类文件夹名称
- **详细计划**: 生成源路径到目标路径的完整移动计划
- **安全审查**: 识别需要用户确认的文件（冲突、系统文件等）
- **备份恢复**: 整理前自动备份，可随时恢复到整理前状态

## 触发方式

用户提到整理桌面、清理桌面、桌面太乱、图标整理、分类桌面文件等关键词时触发。

### 快速示例

- **"帮我整理一下桌面"** → 扫描并生成整理计划
- **"桌面太乱了，清理一下"** → 扫描并生成整理计划
- **"把桌面文件分类"** → 扫描并生成整理计划
- **"恢复桌面到之前的样子"** → 执行恢复操作

## ⚠️ 调用方式（重要）

**禁止** 使用 `subprocess.run(["python", ...])` 或 `subprocess.run(["python3", ...])` 调用脚本 —— 在打包环境中 `python` 命令不存在或指向 WindowsApps 占位符，会导致 exit code 9009。

**依赖声明**: 解析 `.lnk` 快捷方式需要 `pywin32` 包，调用时需设置 `pip_install: ["pywin32"]`。

正确做法：在 `python_execute` 工具中直接 import 调用：

```python
import sys, os

skill_dir = r"<desktop-organizer 目录的绝对路径>"
os.chdir(skill_dir)
sys.path.insert(0, skill_dir)
sys.path.insert(0, os.path.join(skill_dir, "scripts"))

# 导入模块
import scan_and_plan
import execute_organize
import restore_desktop
```

如果直接 import 因模块冲突无法工作，使用 `sys.executable`：

```python
import sys, subprocess
result = subprocess.run(
    [sys.executable, os.path.join(skill_dir, "scripts", "scan_and_plan.py")],
    capture_output=True, text=True, timeout=30
)
print(result.stdout)
if result.stderr:
    print(result.stderr)
```

## 工作流程

```
用户说："帮我整理桌面"
    ↓
调用 scan_and_plan.scan_desktops() 扫描桌面
    ↓
生成整理计划 JSON 文件
    ↓
预览计划（建议文件夹、移动列表、需审查项）
    ↓
获得用户批准后执行
    ↓
移动文件并创建备份记录
```

## 使用流程

### 第一步：扫描并生成整理计划

```python
import sys, os

skill_dir = r"<desktop-organizer 目录的绝对路径>"
os.chdir(skill_dir)
sys.path.insert(0, skill_dir)
sys.path.insert(0, os.path.join(skill_dir, "scripts"))

import scan_and_plan

# 扫描桌面
files = scan_and_plan.scan_desktops()
print(f"发现 {len(files)} 个项目")

# 生成整理计划
plan = scan_and_plan.generate_plan(files)

# 保存计划文件
plan_path = scan_and_plan.save_plan(plan)
print(f"计划已保存到: {plan_path}")

# 输出摘要
print(f"总文件数: {plan['statistics']['total_files']}")
print(f"分类数量: {plan['statistics']['categories']}")
print(f"待移动: {plan['statistics']['to_move']}")
print(f"需审查: {plan['statistics']['to_review']}")
```

### 第二步：预览整理计划

```python
import execute_organize

# 预览计划
execute_organize.preview_plan(plan_path)
```

输出内容包括：
- **建议的文件夹列表**: 每个分类对应的文件夹名称和项目数量
- **移动计划**: 源路径 -> 目标路径的详细列表
- **审查列表**: 需要用户注意的项目（文件冲突、系统文件等）

### 第三步：执行整理（需用户批准）

**必须获得用户明确批准后，才能执行整理操作！**

询问用户：
> 我已生成桌面整理计划，建议将文件按类型分类到以下文件夹：[列出文件夹]。是否确认执行整理？

用户批准后执行：

```python
# 执行整理
result = execute_organize.execute_plan(plan_path, approved=True)

# 检查结果
print(f"成功: {len(result['success'])}")
print(f"失败: {len(result['failed'])}")
print(f"跳过: {len(result['skipped'])}")
```

执行过程：
1. 自动创建分类文件夹
2. 移动文件到对应文件夹
3. 处理文件冲突（自动重命名）
4. 创建备份记录（用于恢复）

### 第四步：恢复到整理前（可选）

如果用户需要恢复：

```python
# 列出可用备份
backups = restore_desktop.list_backups()
for i, b in enumerate(backups, 1):
    print(f"{i}. {b['name']} ({b['time']})")

# 预览恢复
latest_backup = restore_desktop.find_latest_backup()
restore_desktop.preview_restore(latest_backup)

# 执行恢复（需用户批准）
# restore_desktop.restore_from_backup(latest_backup, approved=True)
```

## 文件分类规则

### 普通文件分类

| 分类 | 文件扩展名 |
|------|-----------|
| 文档 | .doc, .docx, .pdf, .txt, .xls, .xlsx, .ppt, .pptx 等 |
| 图片 | .jpg, .jpeg, .png, .gif, .bmp, .webp, .svg 等 |
| 视频 | .mp4, .avi, .mkv, .mov, .wmv, .webm 等 |
| 音频 | .mp3, .wav, .flac, .aac, .ogg 等 |
| 压缩包 | .zip, .rar, .7z, .tar, .gz 等 |
| 程序 | .exe, .msi, .bat, .cmd 等 |
| 代码 | .py, .js, .html, .css, .java, .cpp 等 |
| 其他 | 未匹配的文件类型 |

### 快捷方式分类规则

所有快捷方式（.lnk, .url）统一放到「**快捷方式**」文件夹中，并根据类型进行子分类：

| 子分类 | 说明 |
|--------|------|
| 文件夹快捷方式 | 指向文件夹的快捷方式 |
| 网页快捷方式 | .url 格式的网页链接 |
| 其他快捷方式 | 无法识别类型的快捷方式 |
| 软件 | 指向可执行程序的快捷方式 |

#### 软件快捷方式的智能分类

当桌面上的软件快捷方式数量**超过5个**时，会根据软件名称和目标路径自动识别并细分为：

| 软件类型 | 包含软件示例 |
|----------|-------------|
| 浏览器 | Chrome, Firefox, Edge, Opera, 360浏览器等 |
| 开发工具 | VS Code, PyCharm, Git, Postman, Docker等 |
| 办公软件 | Word, Excel, PowerPoint, WPS, PDF阅读器等 |
| 通讯工具 | 微信, QQ, 钉钉, Teams, Skype, Zoom等 |
| 媒体播放器 | PotPlayer, VLC, 音乐播放器等 |
| 下载工具 | IDM, 迅雷, Motrix等 |
| 压缩工具 | WinRAR, 7-Zip, Bandizip等 |
| 系统工具 | 控制面板, 资源管理器, 终端等 |
| 游戏平台 | Steam, Epic, GOG, Xbox等 |
| 其他软件 | 无法识别类型的软件 |

**注意**：如果软件快捷方式数量**不超过5个**，则统一放到「快捷方式/软件」文件夹中，不进行细分。

### 生成的文件夹结构示例

```
桌面/
├── 文档/
├── 图片/
├── 视频/
├── 快捷方式/
│   ├── 软件/
│   │   ├── 浏览器/
│   │   ├── 开发工具/
│   │   └── ...
│   ├── 文件夹快捷方式/
│   └── 网页快捷方式/
└── ...
```

## 输出格式说明

### 建议的文件夹（Suggested Folders）

```json
{
  "suggested_folders": [
    {
      "name": "文档",
      "count": 15,
      "items": ["报告.docx", "数据.xlsx", ...]
    }
  ]
}
```

### 移动计划（Move Plan）

```json
{
  "move_plan": [
    {
      "source": "C:\\Users\\XXX\\Desktop\\报告.docx",
      "target": "C:\\Users\\XXX\\Desktop\\文档\\报告.docx",
      "filename": "报告.docx",
      "category": "文档",
      "desktop": "用户桌面",
      "conflict": false
    }
  ]
}
```

### 审查列表（Review Items）

包含以下情况的文件：
- 目标位置已存在同名文件（conflict: true）
- 系统文件（desktop.ini 等）
- 需要用户确认是否移动的项目

## 注意事项

1. **执行前必须获得用户批准**: 所有移动操作都需要用户明确确认
2. **自动备份**: 每次整理会自动创建备份记录，可用于恢复
3. **冲突处理**: 同名文件会自动重命名（添加数字后缀）
4. **跳过已分类文件夹**: 已存在的分类文件夹不会被重复处理
5. **系统文件保护**: 自动跳过 desktop.ini、回收站等系统项目
6. **依赖包**: 解析 `.lnk` 快捷方式需要 `pywin32`，调用时需设置 `pip_install: ["pywin32"]`

## 脚本文件说明

- `scripts/scan_and_plan.py` - 扫描桌面并生成整理计划
- `scripts/execute_organize.py` - 执行整理计划
- `scripts/restore_desktop.py` - 恢复桌面到整理前状态

## 完整整理流程示例

```python
import sys, os

skill_dir = r"<desktop-organizer 目录的绝对路径>"
os.chdir(skill_dir)
sys.path.insert(0, skill_dir)
sys.path.insert(0, os.path.join(skill_dir, "scripts"))

import scan_and_plan
import execute_organize

# 1. 扫描并生成计划
files = scan_and_plan.scan_desktops()
plan = scan_and_plan.generate_plan(files)
plan_path = scan_and_plan.save_plan(plan)
print(f"计划已保存: {plan_path}")

# 2. 预览计划
execute_organize.preview_plan(plan_path)

# 3. 询问用户并获得批准后执行
# execute_organize.execute_plan(plan_path, approved=True)
```

## 恢复桌面示例

```python
import sys, os

skill_dir = r"<desktop-organizer 目录的绝对路径>"
os.chdir(skill_dir)
sys.path.insert(0, skill_dir)
sys.path.insert(0, os.path.join(skill_dir, "scripts"))

import restore_desktop

# 列出可用备份
backups = restore_desktop.list_backups()
for b in backups:
    print(f"{b['name']} ({b['time']})")

# 获取最新备份并预览
latest = restore_desktop.find_latest_backup()
if latest:
    restore_desktop.preview_restore(latest)
    # 用户批准后执行恢复
    # restore_desktop.restore_from_backup(latest, approved=True)
```
