# 党政机关公文生成 Skill 使用说明

## 快速开始

### 方法一：直接输入文本生成

```python
# 调用 generate_document.py 脚本
python scripts/generate_document.py \
  --title "关于 XXX 的通知" \
  --sender "XXX 局" \
  --content "正文内容..." \
  --output "output.pdf"
```

### 方法二：读取文件后生成

```python
# 1. 先读取文件
python scripts/read_file.py input.txt

# 2. 使用读取的内容生成 PDF
python scripts/generate_document.py \
  --input input.txt \
  --output output.pdf
```

## 参数说明

### read_file.py

| 参数 | 说明 |
|------|------|
| 文件路径 | txt 或 pdf 文件的绝对路径 |

输出为 JSON 格式，包含：
- `success`: 是否成功
- `content`: 提取的文字内容
- `tables`: 提取的表格内容（仅 PDF）
- `file_type`: 文件类型

### generate_document.py

| 参数 | 必填 | 说明 |
|------|------|------|
| `--input`, `-i` | 否 | 输入文件路径（txt 或 json） |
| `--output`, `-o` | 否 | 输出 PDF 路径（默认自动生成） |
| `--type`, `-t` | 否 | 公文类型（默认：通知） |
| `--title` | 否 | 公文标题 |
| `--sender` | 否 | 发文机关 |
| `--date` | 否 | 成文日期 |
| `--recipient` | 否 | 主送机关 |
| `--copy-to` | 否 | 抄送机关 |
| `--content`, `-c` | 否 | 直接输入公文内容 |

## 公文类型

支持 15 种法定公文类型：
- 决议、决定、命令、公报、公告、通告
- 意见、通知、通报、报告、请示、批复
- 议案、函、纪要

## 输出格式

生成的 PDF 符合 GB/T 9704-2012 标准：
- A4 纸张（210×297mm）
- 页边距：上 37mm、下 35mm、左 28mm、右 26mm
- 正文字体：三号仿宋
- 标题字体：二号小标宋
- 行距：28 磅

## 依赖安装

```bash
pip install reportlab pdfplumber
```

## 示例

### 示例 1：生成简单通知

```bash
python scripts/generate_document.py \
  --title "关于召开年度会议的通知" \
  --sender "办公室" \
  --content "定于 2024 年 3 月 15 日召开年度工作会议，请各部门负责人准时参加。" \
  --output "meeting_notice.pdf"
```

### 示例 2：从 JSON 模板生成

创建 `input.json`：
```json
{
  "title": "关于 XXX 的通知",
  "sender": "XXX 局",
  "content": "正文内容..."
}
```

```bash
python scripts/generate_document.py --input input.json --output output.pdf
```

## 注意事项

1. 确保系统已安装中文字体（仿宋、楷体、黑体）
2. 输出目录需要有写入权限
3. 复杂表格可能需要手动调整
4. 红色分隔线使用字符模拟，打印效果可能略有差异
