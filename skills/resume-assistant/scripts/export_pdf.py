#!/usr/bin/env python3
"""
PDF 导出脚本 - 使用 fpdf2 生成中文简历 PDF
Windows 优化版本

用法: py export_pdf.py <input.md> <output.pdf> [--template <template>]
"""

import sys
import os
from pathlib import Path

try:
    from fpdf import FPDF
except ImportError:
    print("错误: 需要安装 fpdf2")
    print("运行: pip install fpdf2")
    sys.exit(1)


# Windows 中文字体路径
WINDOWS_FONTS = [
    'C:/Windows/Fonts/simhei.ttf',      # 黑体
    'C:/Windows/Fonts/msyh.ttc',       # 微软雅黑
    'C:/Windows/Fonts/simkai.ttf',      # 楷体
]

def find_chinese_font():
    """查找可用的中文字体"""
    for font_path in WINDOWS_FONTS:
        if Path(font_path).exists():
            return font_path
    return None


class ResumePDF(FPDF):
    """简历 PDF 生成器"""

    def __init__(self):
        super().__init__()
        self.BLUE = (30, 58, 95)
        self.GRAY = (85, 85, 85)
        self.LIGHT_GRAY = (136, 136, 136)
        self.DARK = (51, 51, 51)

    def add_chinese_font(self, font_path=None):
        """添加中文字体"""
        if font_path is None:
            font_path = find_chinese_font()

        if font_path is None or not Path(font_path).exists():
            print("警告: 未找到中文字体，PDF 可能无法正确显示中文")
            return False

        self.add_font('Hei', '', font_path)
        self.add_font('Hei', 'B', font_path)
        return True

    def set_colors(self):
        """设置颜色"""
        pass  # 使用默认值

    def add_header(self, name, contact_info):
        """添加页眉"""
        self.set_font('Hei', 'B', 20)
        self.set_text_color(*self.BLUE)
        self.cell(0, 12, name, new_x='LMARGIN', new_y='NEXT', align='C')

        self.set_font('Hei', '', 9)
        self.set_text_color(*self.GRAY)
        self.cell(0, 6, contact_info, new_x='LMARGIN', new_y='NEXT', align='C')
        self.ln(2)

        self.set_draw_color(*self.BLUE)
        self.set_line_width(0.8)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(6)

    def add_section_title(self, title):
        """添加章节标题"""
        self.set_font('Hei', 'B', 11)
        self.set_text_color(*self.BLUE)
        self.cell(0, 7, title, new_x='LMARGIN', new_y='NEXT')
        self.set_line_width(0.4)
        self.set_draw_color(*self.BLUE)
        self.line(self.l_margin, self.get_y() + 1, self.l_margin + 25, self.get_y() + 1)
        self.ln(4)

    def add_experience_item(self, title, company, date, location, bullets):
        """添加工作经历条目"""
        W = self.w - self.l_margin - self.r_margin

        # 标题行
        self.set_font('Hei', 'B', 10)
        self.set_text_color(*self.BLUE)
        title_w = W * 0.55
        self.cell(title_w, 6, title, new_x='RIGHT', new_y='TOP')
        self.set_font('Hei', '', 9)
        self.set_text_color(*self.LIGHT_GRAY)
        self.cell(W - title_w, 6, date, new_x='LMARGIN', new_y='NEXT', align='R')

        # 公司地点
        self.set_font('Hei', '', 9)
        self.set_text_color(*self.GRAY)
        self.cell(W, 5, company + '  |  ' + location, new_x='LMARGIN', new_y='NEXT')

        # 要点 - 使用 write 避免宽度问题
        self.set_text_color(*self.DARK)
        for bullet in bullets:
            self.set_font('Hei', '', 9)
            self.cell(4, 5, '-', new_x='RIGHT', new_y='TOP')
            self.write(5, bullet)
            self.ln()
        self.ln(2)

    def add_skill_category(self, label, items):
        """添加技能分类"""
        self.set_font('Hei', 'B', 9)
        self.set_text_color(*self.BLUE)
        self.cell(24, 5, label, new_x='RIGHT', new_y='TOP')
        self.set_font('Hei', '', 9)
        self.set_text_color(*self.DARK)
        self.write(5, items)
        self.ln()


def export_to_pdf(markdown_content: str, output_path: str, template: str = "professional"):
    """将 Markdown 简历内容转换为 PDF"""

    pdf = ResumePDF()
    pdf.add_page()
    pdf.add_chinese_font()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)

    # 解析 Markdown（简化版，实际应该用 markdown 库）
    lines = markdown_content.strip().split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 标题处理
        if line.startswith('# '):
            name = line[2:]
            pdf.add_header(name, 'liqiang@email.com  |  138-0000-5678  |  上海')
        elif line.startswith('## '):
            current_section = line[3:].strip()
            if current_section:
                pdf.add_section_title(current_section.upper())
        elif line.startswith('- '):
            # 列表项
            text = line[2:]
            pdf.set_font('Hei', '', 9)
            pdf.set_text_color(*pdf.DARK)
            pdf.cell(4, 5, '-', new_x='RIGHT', new_y='TOP')
            pdf.write(5, text)
            pdf.ln()
        elif '|' in line and current_section in ['工作经历', '教育背景', '专业技能']:
            # 表格行 - 简化处理
            pass
        else:
            # 普通文本
            if current_section == '个人简介':
                pdf.set_font('Hei', '', 9)
                pdf.set_text_color(*pdf.DARK)
                pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 5, line)
                pdf.ln(2)

    pdf.output(output_path)
    print(f"PDF 已生成: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: py export_pdf.py <input.md> <output.pdf> [--template <template>]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(input_file).exists():
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)

    content = Path(input_file).read_text(encoding='utf-8')
    export_to_pdf(content, output_file)
