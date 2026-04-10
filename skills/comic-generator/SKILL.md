---
name: 漫画生成器
description: 将描述性文字转换为漫画页面的完整工作流。支持素描（黑白线稿）和彩绘（彩色漫画）两种风格，可从直接输入或文件（.docx、.txt）读取文字，生成后可编辑单页，最终输出为 PDF 文档。
---

# 漫画生成器

本 Skill 提供将描述性文字转换为漫画页面的完整工作流。支持素描（黑白线稿）和彩绘（彩色漫画）两种风格，可从直接输入或文件（.docx、.txt）读取文字，生成后可编辑单页，最终输出为 PDF 文档。

## 工作流程概览

1. **获取输入**：接收用户直接输入的文本，或读取 Word (.docx) / 记事本 (.txt) 文件。
2. **分割场景**：将文本按段落、句子或用户指定的分隔符拆分为多个场景（每个场景对应一页漫画）。
3. **选择风格**：用户选择素描（sketch）或彩绘（color）风格。
4. **生成图像**：为每个场景生成漫画图像，图像上方或下方预留文字说明区域。
5. **添加文字**：在每页漫画下方添加对应的描述文字。
6. **编辑功能**：允许用户选择编辑特定编号的漫画图像或文字，重新生成该页。
7. **预览**：展示所有漫画页面（图像+文字）供用户确认。
8. **输出 PDF**：将所有页面组合成单个 PDF 文件。

## 详细步骤指南

### 1. 获取输入

**直接输入**：请用户粘贴或输入描述性文字。

**文件读取**：
- 对于 .txt 文件：使用 Python 内置 `open()` 读取。

示例代码（读取文件）：
```python
def read_text_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()
```

### 2. 分割场景

询问用户希望如何分割文本：
- 按段落（空行分隔）
- 按句子（句号、问号、感叹号分隔）
- 按自定义分隔符（如“###”）

提供默认分割方式（按段落）。

示例代码（按段落分割）：
```python
def split_by_paragraphs(text):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return paragraphs
```

### 3. 选择风格

提供两个选项：
- **素描风格**：黑白线稿，prompt 中添加“sketch, black and white, line drawing, comic style”
- **彩绘风格**：彩色漫画，prompt 中添加“color, vibrant, comic book style, detailed coloring”

### 4. 生成图像

对于每个场景文本，构建图像生成 prompt。建议格式：
```
[场景描述]，漫画风格，[素描/彩绘]，清晰构图，背景丰富，人物生动
```

注意：调用 `image_generate` 工具时，可根据用户选择的风格调整 prompt 和参数。素描风格可使用黑白提示词，彩绘风格使用彩色提示词。

图像尺寸建议使用 16:9 或 4:3 的横屏比例，以适应漫画页面。

### 5. 添加文字

每页漫画应包含图像和下方的说明文字。文字可使用相同场景文本，或用户提供的精简版本。

可考虑将文字直接叠加在图像上，或单独保存文字内容，在生成 PDF 时放置在图像下方。

### 6. 编辑功能

用户可能想修改某页漫画的图像或文字。实现方式：
- 展示所有页面编号和预览
- 询问要编辑的页面编号
- 对于图像编辑：重新生成该页图像（可允许用户修改 prompt）
- 对于文字编辑：允许用户修改该页文字
- 更新后重新预览该页

### 7. 预览

将所有生成的图像（和文字）以列表形式展示给用户。可提供简略描述（如“第1页：场景描述...”）。若图像文件较多，可逐页显示或生成一个 HTML 预览页面。

### 8. 输出 PDF

使用 `formPDF.exe` 工具将图像和文字组合成 PDF。每页 PDF 包含图像和下方文字。

`formPDF.exe` 接受 JSON 格式的配置文件作为参数，生成指定布局的 PDF 文档。

**命令行用法：**
```bash
formPDF.exe --config config.json --output output.pdf
```

**配置文件格式（config.json）：**
```json
{
  "pages": [
    {
      "image": "path/to/image1.png",
      "text": "第一页的描述文字"
    },
    {
      "image": "path/to/image2.png",
      "text": "第二页的描述文字"
    }
  ],
  "layout": {
    "page_width": 210,
    "page_height": 297,
    "margin": 10,
    "image_height": 180,
    "font_size": 12
  }
}
```

**Python 调用示例：**
```python
import subprocess
import json
import os

def create_pdf(image_paths, texts, output_path):
    # 构建配置文件
    config = {
        "pages": [
            {"image": img, "text": txt} 
            for img, txt in zip(image_paths, texts)
        ],
        "layout": {
            "page_width": 210,
            "page_height": 297,
            "margin": 10,
            "image_height": 180,
            "font_size": 12
        }
    }
    
    # 保存临时配置文件
    config_path = "temp_config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # 调用 formPDF.exe
    subprocess.run([
        "formPDF.exe",
        "--config", config_path,
        "--output", output_path
    ], check=True)
    
    # 清理临时文件
    os.remove(config_path)
```

## 打包资源

### scripts/
- `text_processor.py`：文本读取与分割工具
- `comic_generator.py`：调用图像生成、管理页面编辑的主脚本

### tools/
- `formPDF.exe`：PDF 生成工具（接受 JSON 配置生成 PDF）
- `formPDF.py`：PDF 生成工具源码（可用 PyInstaller 自行打包）

### references/
- `prompt_guide.md`：素描/彩绘风格 prompt 构建指南
- `editing_workflow.md`：单页编辑的详细流程

### assets/
- `layout_template.pdf`：漫画页面布局参考（可选）

## 注意事项

1. **图像生成成本**：每页漫画都需要调用 `image_generate`，生成多页时需提醒用户可能耗时。
2. **文字长度**：过长的描述文字可能影响图像生成效果，建议用户精简场景描述。
3. **文件管理**：生成的图像文件应妥善保存于临时目录，PDF 输出后可按用户意愿清理。
4. **错误处理**：图像生成失败时应有重试机制；PDF 生成失败时提供错误信息。

## 示例对话

**用户**：“帮我将这段故事变成漫画，要彩绘风格。”

**Agent**：
1. 询问输入方式（直接输入或文件）
2. 获取文本后询问分割方式（按段落）
3. 确认选择彩绘风格
4. 开始为每个段落生成图像
5. 展示预览，询问是否编辑任何页面
6. 确认后生成 PDF 并交付

---
Skill 创建者：焊枪
最后更新：2025-03-11