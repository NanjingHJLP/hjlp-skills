---
name: 系统体检
description: 给电脑做个全身检查，帮你查看CPU温度、内存占用、磁盘健康状态等系统运行情况
---

# 系统体检 Skill

当用户请求对电脑进行全面体检/健康检查时，按以下流程逐步执行：

## 检查流程

### 第一步：基础硬件信息
调用 `system_info` 工具，获取 CPU、内存、磁盘、GPU 等基础配置信息。

### 第二步：资源占用排查
调用 `process_manager`（action: `top_cpu`）查看 CPU 占用前 10 的进程。
调用 `process_manager`（action: `top_memory`）查看内存占用前 10 的进程。

### 第三步：磁盘健康检查
使用 `python_execute` 运行以下检查：
- 各磁盘分区的使用率（超过 90% 标红预警）
- 系统盘剩余空间

### 第四步：启动项检查
使用 `powershell_command` 执行：
```powershell
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Format-Table -AutoSize
```

### 第五步：系统更新状态
使用 `powershell_command` 检查最近的 Windows Update：
```powershell
Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5
```

## 输出格式

完成所有检查后，输出一份结构化的体检报告：

```
📋 电脑体检报告
━━━━━━━━━━━━━━━━━━━━━━━
🖥️ 基础配置: ...
💻 CPU 状态: 使用率 xx% [正常/偏高/过高]
🧠 内存状态: 使用 xx/xx GB (xx%) [正常/偏高/过高]
💾 磁盘状态: C盘剩余 xx GB [正常/预警/危险]
🚀 启动项: xx 个 [正常/偏多]
🔄 系统更新: 最近更新于 xxxx-xx-xx [正常/需更新]
━━━━━━━━━━━━━━━━━━━━━━━
综合评分: ⭐⭐⭐⭐ (x/5)
建议: ...
```
