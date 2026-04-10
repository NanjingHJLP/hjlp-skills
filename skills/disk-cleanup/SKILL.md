---
name: 磁盘与临时文件清理
description: 磁盘空间清理 临时文件Temp 回收站清空 磁盘清理 空间不足 大文件扫描 C盘满了
---

# 磁盘与临时文件清理 Skill

## 核心原则

1. **一步到位**：简单任务（清空回收站、清理 Temp）用一条 PowerShell 命令完成并直接报告结果，禁止额外验证轮次。
2. **优先 powershell_command**：磁盘清理场景首选 `powershell_command`，避免用 `python_execute` 调用 Windows API（ctypes 兼容性差）。
3. **命令成功即停止**：工具返回 success=True 后，直接向用户汇报结果，不要再用另一种工具重复执行同一操作。
4. **不主动删除系统关键文件**，仅删除用户明确同意的目录（Temp、回收站等）。

## 快速任务（单一操作直接执行）

当用户请求的是以下单一操作时，**只需一条命令 + 输出结果**，不要走完整流程：

### 清空回收站
```powershell
Clear-RecycleBin -Force -ErrorAction SilentlyContinue; Write-Output '回收站已清空'
```

### 清理用户临时文件
```powershell
$t = "$env:LOCALAPPDATA\Temp"; $before = (Get-ChildItem $t -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum; Remove-Item "$t\*" -Recurse -Force -ErrorAction SilentlyContinue; $after = (Get-ChildItem $t -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum; Write-Output "已清理临时文件: 释放 $([math]::Round(($before - $after)/1MB, 1)) MB"
```

### 查看磁盘空间
```powershell
Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Used(GB)';E={[math]::Round($_.Used/1GB,2)}}, @{N='Free(GB)';E={[math]::Round($_.Free/1GB,2)}} | Format-Table -AutoSize
```

## 完整流程（综合磁盘清理/C盘空间不足）

仅当用户需要全面清理或 C 盘空间不足时才走以下流程：

### 第一步：磁盘空间总览
```powershell
Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Used(GB)';E={[math]::Round($_.Used/1GB,2)}}, @{N='Free(GB)';E={[math]::Round($_.Free/1GB,2)}} | Format-Table -AutoSize
```

### 第二步：扫描可清理项（一条命令获取所有大小，不要分多条）
```powershell
$temp = "$env:LOCALAPPDATA\Temp"; $sysTemp = "$env:SystemRoot\Temp"
$results = @()
$results += [PSCustomObject]@{Item='用户Temp'; SizeMB=[math]::Round(((Get-ChildItem $temp -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum)/1MB,1)}
$results += [PSCustomObject]@{Item='系统Temp'; SizeMB=[math]::Round(((Get-ChildItem $sysTemp -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum)/1MB,1)}
$results += [PSCustomObject]@{Item='Downloads'; SizeMB=[math]::Round(((Get-ChildItem "$env:USERPROFILE\Downloads" -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum)/1MB,1)}
$results | Format-Table -AutoSize
```

### 第三步：按用户确认逐项清理
用户同意后再执行对应清理命令。回收站用 `Clear-RecycleBin -Force`，Temp 用 `Remove-Item`。

### 第四步：大文件/大目录扫描（可选）
仅在用户要求时扫描指定目录（避免全盘扫描）：
```powershell
Get-ChildItem -Path "C:\Users\$env:USERNAME" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
  $size = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
  [PSCustomObject]@{ Path = $_.FullName; SizeMB = [math]::Round($size/1MB, 2) }
} | Sort-Object SizeMB -Descending | Select-Object -First 15
```

### 第五步：C盘深度清理（可选）

仅当用户要求深度清理C盘时执行。扫描项分两类：

**系统文件类**（需管理员权限的标注★）：
- 回收站 → `Clear-RecycleBin -Force`
- 用户 Temp → `Remove-Item "$env:LOCALAPPDATA\Temp\*" -Recurse -Force -EA SilentlyContinue`
- 系统 Temp★ → `Remove-Item "$env:SystemRoot\Temp\*" -Recurse -Force -EA SilentlyContinue`
- Windows.old → 存在则提示用户可删（`Remove-Item C:\Windows.old -Recurse -Force`）
- Windows 更新缓存★ → 停止 wuauserv 后清理 `C:\Windows\SoftwareDistribution\Download`
- WinSxS★ → `Dism /Online /Cleanup-Image /StartComponentCleanup`
- 休眠文件 → `powercfg /hibernate off`（需确认用户不需要快速启动）
- 内存转储 → 删除 `C:\Windows\Memory.dmp` 和 `C:\Windows\Minidump\*.dmp`

**软件缓存类**（清理前确认应用已关闭）：
- 下载文件夹 `$env:USERPROFILE\Downloads` — 需用户确认
- 微信 `$env:USERPROFILE\Documents\WeChat Files`
- 企业微信 `$env:USERPROFILE\Documents\WXWork`
- QQ `$env:USERPROFILE\Documents\Tencent Files`
- Chrome 缓存 `$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache`
- Edge 缓存 `$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cache`

### 安全提示
- 不主动删除系统关键目录
- C盘深度清理前建议创建系统还原点
- WinSxS 清理必须使用 DISM 工具，禁止直接删除文件
- 休眠文件关闭前确认用户不需要快速启动功能

## 输出格式

- **简单任务**（清回收站、清 Temp）：一句话说明操作结果即可，如"已清空回收站"。
- **综合清理**：列出各项大小表格 + 建议清理顺序。
- **C盘深度清理**：分系统文件类和软件缓存类列出各项大小，末尾给出预计可释放空间和建议顺序。
