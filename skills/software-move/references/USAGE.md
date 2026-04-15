# software-move 使用说明

## 命令速查

```bash
# 扫描磁盘上的软件
softwaremove scan disk D

# 检测软件是否支持搬迁（推荐迁移前执行）
softwaremove move check --source "C:\\Users\\1\\AppData\\Local\\Figma" --name "Figma"

# 迁移软件目录
softwaremove move start --source "D:\\Apps\\Foo" --target "E:\\SoftwareMoved\\Foo"

# 迁移需要管理员权限的软件（如 Program Files 下的软件）
softwaremove move start --source "C:\\Program Files (x86)\\ScreenRecord" --target "E:\\SoftwareMoved\\ScreenRecord" --admin

# 从历史记录还原
softwaremove history restore --id 1 --admin

# 撤销上一次迁移
softwaremove history undo --admin

# 重做上一次还原的迁移
softwaremove history redo --admin

# 查看历史记录
softwaremove history list
```

## 管理员权限

**Program Files** 或 **Program Files (x86)** 目录下的软件需要管理员权限才能创建 junction 链接。

### 自动提升权限

使用 `--admin` 参数自动请求管理员权限：

```bash
softwaremove move start --source "C:\\Program Files\\Software" --target "E:\\SoftwareMoved\\Software" --admin
```

### 权限指示器

运行任何命令时，前面会显示权限状态：
- `[Administrator]` - 当前在管理员权限下运行（绿色）
- `[User]` - 当前在用户权限下运行（黄色）

### 无需管理员的情况

以下位置的软件不需要管理员权限：
- `C:\Users\<用户名>\AppData\Local` （如 Figma、Postman）
- `C:\Users\<用户名>\AppData\Roaming`
- 自定义安装目录（如 `D:\Apps`）

## 迁移检测说明

`move check` 会检测以下情况：
- **UWP/MSIX 应用**：不支持 junction 链接方式
- **注册表路径引用**：迁移后可能需要手动更新注册表
- **被锁定的文件**：迁移时将跳过
- **正在运行的进程**：迁移前会警告
