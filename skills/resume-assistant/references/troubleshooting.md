# 常见问题与解决方案

## PDF 导出问题

### WeasyPrint 依赖错误

**错误信息：**
```
OSError: cannot load library 'libgobject-2.0-0'
```

**原因：** WeasyPrint 依赖 GTK 库（Linux 环境库），Windows 系统没有预装。

**解决方案：** 使用 fpdf2 库代替

```python
# ❌ 错误 - Windows 不支持
from weasyprint import HTML

# ✅ 正确 - 使用 fpdf2
from fpdf import FPDF
pdf = FPDF()
pdf.add_font('Hei', '', 'C:/Windows/Fonts/simhei.ttf')
```

---

### fpdf2 中文字体问题

#### 错误 1：Unicode 编码错误

**错误信息：**
```
FPDFUnicodeEncodingException: Character "李" at index 0...
UnicodeEncodeError: 'latin-1' codec can't encode character
```

**原因：** fpdf2 默认使用 Latin-1 编码，无法处理中文字符。

**解决方案：** 添加中文字体

```python
pdf.add_font('Hei', '', 'C:/Windows/Fonts/simhei.ttf')
pdf.add_font('Hei', 'B', 'C:/Windows/Fonts/simhei.ttf')
```

#### 错误 2：字体未定义

**错误信息：**
```
FPDFException: Undefined font: heib
FPDFException: Undefined font: heiI
```

**原因：** 字体名称或样式错误。fpdf2 的 add_font() 格式：

```python
# ✅ 正确
pdf.add_font('Hei', '', '路径/simhei.ttf')    # 常规
pdf.add_font('Hei', 'B', '路径/simhei.ttf')   # 粗体

# ❌ 错误
pdf.add_font('Hei', 'BI', '路径/simhei.ttf')  # 不要这样写
pdf.add_font('HeiB', '', '路径/simhei.ttf')   # 也不要这样写
```

设置字体时也不要组合样式：
```python
# ✅ 正确
pdf.set_font('Hei', 'B', 12)  # 粗体
pdf.set_font('Hei', '', 12)    # 常规

# ❌ 错误 - 斜体后缀会找不到字体
pdf.set_font('Hei', 'BI', 12)
```

#### 错误 3：宽度不足

**错误信息：**
```
FPDFException: Not enough horizontal space to render a single character
```

**原因：** multi_cell 在 cell 后调用时，宽度计算错误。

**解决方案：** 使用 write() 代替 multi_cell()

```python
# ❌ 错误
pdf.cell(5, 5, '-')
pdf.multi_cell(0, 5, text)  # 宽度 0 有问题

# ✅ 正确
pdf.cell(5, 5, '-')
pdf.write(5, text)  # 使用 write
pdf.ln()

# 或者避免在 cell 后使用 multi_cell
```

---

## Windows 环境注意事项

### Python 命令

Windows 上使用 `py` 而不是 `python`：

```bash
# ❌ 可能找不到
python script.py

# ✅ 正确
py script.py
```

### 字体路径

Windows 中文字体路径：

| 字体 | 路径 |
|------|------|
| 黑体 | `C:/Windows/Fonts/simhei.ttf` |
| 宋体 | `C:/Windows/Fonts/simsun.ttc` |
| 微软雅黑 | `C:/Windows/Fonts/msyh.ttc` |
| 楷体 | `C:/Windows/Fonts/simkai.ttf` |

### 路径分隔符

始终使用正斜杠 `/` 或双反斜杠 `\\`：

```python
# ✅ 正确
'C:/Windows/Fonts/simhei.ttf'
'C:\\Windows\\Fonts\\simhei.ttf'

# ❌ 错误 - Windows 不认识单反斜杠在字符串中
'C:\Windows\Fonts\simhei.ttf'  # 会被当作转义字符
```

---

## 推荐的 PDF 生成流程

### 方法 1：fpdf2（推荐，跨平台）

```python
from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.add_font('Hei', '', 'C:/Windows/Fonts/simhei.ttf')
pdf.add_font('Hei', 'B', 'C:/Windows/Fonts/simhei.ttf')
pdf.set_auto_page_break(auto=True, margin=20)

# 标题
pdf.set_font('Hei', 'B', 20)
pdf.cell(0, 12, '李强', align='C')

pdf.output('resume.pdf')
```

### 方法 2：HTML + 浏览器打印

生成 HTML 文件，让用户用浏览器打开并打印为 PDF。

### 方法 3：Windows 命令行工具

```bash
# 使用 Microsoft Print to PDF
# 或安装 wkhtmltopdf
winget install wkhtmltopdf
wkhtmltopdf resume.html resume.pdf
```

---

## 故障排除清单

1. [ ] 确认使用 `py` 而非 `python`
2. [ ] 确认已添加中文字体
3. [ ] 确认字体名称正确（无组合样式后缀）
4. [ ] 使用 write() 代替 multi_cell() 在 cell 后
5. [ ] 路径使用 `/` 或 `\\`
