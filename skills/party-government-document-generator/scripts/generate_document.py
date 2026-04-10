#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
党政机关公文 PDF 生成脚本
根据 GB/T 9704-2012《党政机关公文格式》国家标准生成规范格式的公文 PDF

标准要点：
- 纸张：A4（210mm×297mm）
- 页边距：上 37mm，下 35mm，左 28mm，右 26mm
- 版心：156mm×225mm
- 正文行距：28-30磅（固定值）
- 每页22行，每行28字

用法：python generate_document.py --input <输入文件> --output <输出路径> --type <公文类型>
"""

import sys
import os
import json
import argparse
import re
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Line
from reportlab.pdfgen.canvas import Canvas

# ==================== GB/T 9704-2012 标准常量 ====================

# 纸张尺寸 (mm)
A4_WIDTH = 210
A4_HEIGHT = 297

# 页边距 (mm) - 标准规定
MARGIN_TOP = 37      # 上白边
MARGIN_BOTTOM = 35   # 下白边
MARGIN_LEFT = 28     # 左白边（订口）
MARGIN_RIGHT = 26    # 右白边（翻口）

# 版心尺寸 (mm)
BODY_WIDTH = 156     # 版心宽度 = 210 - 28 - 26
BODY_HEIGHT = 225    # 版心高度 = 297 - 37 - 35

# 字体大小（磅）- 标准字号换算
FONT_SIZE_YI_HAO = 26       # 一号
FONT_SIZE_XIAO_YI = 24      # 小一
FONT_SIZE_ER_HAO = 22       # 二号（标题）
FONT_SIZE_XIAO_ER = 18      # 小二
FONT_SIZE_SAN_HAO = 16      # 三号（正文）
FONT_SIZE_XIAO_SAN = 15     # 小三
FONT_SIZE_SI_HAO = 14       # 四号（版记）
FONT_SIZE_XIAO_SI = 12      # 小四
FONT_SIZE_WU_HAO = 10.5     # 五号

# 行距（磅）- 标准规定约28-30磅
LINE_HEIGHT_MAIN = 29       # 主体部分行距
LINE_HEIGHT_FOOTER = 22     # 版记部分行距

# 字符宽度（三号仿宋约5.54mm/字符）
CHAR_WIDTH = 5.54

# 公文类型
DOCUMENT_TYPES = [
    '决议', '决定', '命令', '公报', '公告', '通告',
    '意见', '通知', '通报', '报告', '请示', '批复',
    '议案', '函', '纪要'
]

# ==================== 字体注册与管理 ====================

class FontManager:
    """管理公文所需的中文字体"""

    # 字体搜索路径
    FONT_PATHS = {
        'SimSun': [  # 宋体
            r'C:\Windows\Fonts\simsun.ttc',
            r'C:\Windows\Fonts\simsunb.ttf',
        ],
        'SimFang': [  # 仿宋
            r'C:\Windows\Fonts\simfang.ttf',
            r'C:\Windows\Fonts\FZFANGS.TTF',
        ],
        'SimKai': [  # 楷体
            r'C:\Windows\Fonts\simkai.ttf',
            r'C:\Windows\Fonts\FZKAIK.TTF',
        ],
        'SimHei': [  # 黑体
            r'C:\Windows\Fonts\simhei.ttf',
            r'C:\Windows\Fonts\FZHEIK.TTF',
        ],
        'XiaoBiaoSong': [  # 小标宋（公文标题和标志用）
            r'C:\Windows\Fonts\simsun.ttc',  # 临时用宋体替代
            r'C:\Windows\Fonts\方正小标宋简体.ttf',
        ]
    }

    def __init__(self):
        self.registered_fonts = {}
        self._register_fonts()

    def _register_fonts(self):
        """注册所有可用的中文字体"""
        for font_name, paths in self.FONT_PATHS.items():
            for path in paths:
                if os.path.exists(path):
                    try:
                        # 使用字体名作为内部名称
                        internal_name = font_name
                        pdfmetrics.registerFont(TTFont(internal_name, path))
                        self.registered_fonts[font_name] = internal_name
                        break
                    except Exception as e:
                        continue

    def get_font(self, font_name, fallback='Helvetica'):
        """获取字体名称，如果不可用则返回后备字体"""
        return self.registered_fonts.get(font_name, fallback)

    def has_font(self, font_name):
        """检查字体是否可用"""
        return font_name in self.registered_fonts

    def list_available_fonts(self):
        """列出所有可用字体"""
        return list(self.registered_fonts.keys())

# ==================== 公文PDF生成器 ====================

class OfficialDocumentGenerator:
    """根据GB/T 9704-2012标准生成党政机关公文PDF"""

    def __init__(self):
        self.font_manager = FontManager()
        self.styles = None
        self._init_styles()

    def _init_styles(self):
        """初始化公文样式"""
        styles = getSampleStyleSheet()

        # 获取字体
        fang_font = self.font_manager.get_font('SimFang', 'SimSun')
        kai_font = self.font_manager.get_font('SimKai', 'SimSun')
        hei_font = self.font_manager.get_font('SimHei', 'Helvetica-Bold')
        song_font = self.font_manager.get_font('SimSun', 'SimSun')
        xbs_font = self.font_manager.get_font('XiaoBiaoSong', hei_font)

        # 1. 发文机关标志样式（红色小标宋）
        self.org_logo_style = ParagraphStyle(
            'OrgLogo',
            parent=styles['Normal'],
            fontName=hei_font,  # 暂用黑体，理想是小标宋
            fontSize=FONT_SIZE_YI_HAO,  # 一号
            textColor=colors.red,
            alignment=TA_CENTER,
            spaceAfter=0,
            leading=FONT_SIZE_YI_HAO * 1.2,
        )

        # 2. 发文字号样式（三号仿宋）
        self.doc_number_style = ParagraphStyle(
            'DocNumber',
            parent=styles['Normal'],
            fontName=fang_font,
            fontSize=FONT_SIZE_SAN_HAO,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=0,
            leading=FONT_SIZE_SAN_HAO * 1.2,
        )

        # 3. 签发人样式（三号楷体）
        self.issuer_style = ParagraphStyle(
            'Issuer',
            parent=styles['Normal'],
            fontName=kai_font,
            fontSize=FONT_SIZE_SAN_HAO,
            textColor=colors.black,
            alignment=TA_RIGHT,
            spaceAfter=0,
            leading=FONT_SIZE_SAN_HAO * 1.2,
        )

        # 4. 标题样式（二号小标宋，居中）
        self.title_style = ParagraphStyle(
            'Title',
            parent=styles['Normal'],
            fontName=hei_font,  # 暂用黑体，理想是小标宋
            fontSize=FONT_SIZE_ER_HAO,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=FONT_SIZE_SAN_HAO,  # 标题后空一行（三号字高度）
            leading=FONT_SIZE_ER_HAO * 1.4,
        )

        # 5. 主送机关样式（三号仿宋，顶格）
        self.recipient_style = ParagraphStyle(
            'Recipient',
            parent=styles['Normal'],
            fontName=fang_font,
            fontSize=FONT_SIZE_SAN_HAO,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=FONT_SIZE_SAN_HAO,  # 主送机关后空一行
            leading=LINE_HEIGHT_MAIN,
            leftIndent=0,  # 顶格，无缩进
        )

        # 6. 正文样式（三号仿宋，首行缩进2字符）
        self.body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName=fang_font,
            fontSize=FONT_SIZE_SAN_HAO,
            textColor=colors.black,
            alignment=TA_JUSTIFY,
            spaceBefore=0,
            spaceAfter=0,
            leading=LINE_HEIGHT_MAIN,
            firstLineIndent=FONT_SIZE_SAN_HAO * 2,  # 首行缩进2字符
        )

        # 7. 一级标题样式（三号黑体，首行缩进2字符）
        self.heading1_style = ParagraphStyle(
            'Heading1',
            parent=styles['Normal'],
            fontName=hei_font,
            fontSize=FONT_SIZE_SAN_HAO,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceBefore=LINE_HEIGHT_MAIN,
            spaceAfter=0,
            leading=LINE_HEIGHT_MAIN,
            firstLineIndent=FONT_SIZE_SAN_HAO * 2,  # 首行缩进2字符
        )

        # 8. 二级标题样式（三号楷体，首行缩进2字符）
        self.heading2_style = ParagraphStyle(
            'Heading2',
            parent=styles['Normal'],
            fontName=kai_font,
            fontSize=FONT_SIZE_SAN_HAO,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=0,
            leading=LINE_HEIGHT_MAIN,
            firstLineIndent=FONT_SIZE_SAN_HAO * 2,  # 首行缩进2字符
        )

        # 9. 三级标题样式（三号仿宋加粗，首行缩进2字符）
        self.heading3_style = ParagraphStyle(
            'Heading3',
            parent=styles['Normal'],
            fontName=fang_font,
            fontSize=FONT_SIZE_SAN_HAO,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=0,
            leading=LINE_HEIGHT_MAIN,
            firstLineIndent=FONT_SIZE_SAN_HAO * 2,  # 首行缩进2字符
        )

        # 10. 发文机关署名样式（三号仿宋，右对齐）
        self.signature_style = ParagraphStyle(
            'Signature',
            parent=styles['Normal'],
            fontName=fang_font,
            fontSize=FONT_SIZE_SAN_HAO,
            textColor=colors.black,
            alignment=TA_RIGHT,
            spaceBefore=0,
            spaceAfter=0,
            leading=LINE_HEIGHT_MAIN,
            rightIndent=FONT_SIZE_SAN_HAO * 4,  # 右空4字
        )

        # 11. 成文日期样式（三号仿宋，阿拉伯数字，右空4字）
        self.date_style = ParagraphStyle(
            'Date',
            parent=styles['Normal'],
            fontName=fang_font,
            fontSize=FONT_SIZE_SAN_HAO,
            textColor=colors.black,
            alignment=TA_RIGHT,
            spaceBefore=0,
            spaceAfter=0,
            leading=LINE_HEIGHT_MAIN,
            rightIndent=FONT_SIZE_SAN_HAO * 4,  # 右空4字
        )

        # 12. 版记样式（四号仿宋）
        self.footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontName=fang_font,
            fontSize=FONT_SIZE_SI_HAO,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=0,
            leading=LINE_HEIGHT_FOOTER,
        )

        # 13. 附件说明样式（三号仿宋，左空2字）
        self.attachment_style = ParagraphStyle(
            'Attachment',
            parent=styles['Normal'],
            fontName=fang_font,
            fontSize=FONT_SIZE_SAN_HAO,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceBefore=FONT_SIZE_SAN_HAO,  # 正文下空一行
            spaceAfter=0,
            leading=LINE_HEIGHT_MAIN,
            leftIndent=FONT_SIZE_SAN_HAO * 2,  # 左空2字
        )

        self.styles = styles

    def _detect_heading_level(self, text):
        """检测标题层级"""
        text = text.strip()
        # 一级标题：一、二、三、...
        if re.match(r'^[一二三四五六七八九十百千万]+[、\.]', text):
            return 1
        # 二级标题：（一）（二）（三）...
        if re.match(r'^（[一二三四五六七八九十]+）', text):
            return 2
        # 三级标题：1. 2. 3. ...
        if re.match(r'^\d+[\.\u3001]', text):
            return 3
        # 四级标题：（1）（2）（3）...
        if re.match(r'^（\d+）', text):
            return 4
        return 0

    def _process_content(self, content):
        """处理正文内容，识别标题层级"""
        paragraphs = []
        lines = content.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            level = self._detect_heading_level(line)
            paragraphs.append({'text': line, 'level': level})

        return paragraphs

    def _create_red_line_flowable(self, width_mm, thickness_mm=0.35):
        """创建红色分隔线 - 使用简单可靠的段落方式"""
        # 创建一个红色背景的段落作为分隔线
        from reportlab.platypus import HRFlowable
        return HRFlowable(
            width=width_mm * mm,
            thickness=thickness_mm * mm,
            color=colors.red,
            spaceBefore=0,
            spaceAfter=0,
            hAlign='CENTER'
        )

    def generate(self, content, output_path, doc_type='通知', title=None,
                 sender=None, date=None, main_recipient=None, copy_to=None,
                 doc_number=None, issuer=None, attachment=None, security_level=None,
                 urgency=None):
        """
        生成公文PDF

        参数:
            content: 公文正文内容
            output_path: 输出文件路径
            doc_type: 公文类型
            title: 公文标题
            sender: 发文机关（用于署名）
            date: 成文日期
            main_recipient: 主送机关
            copy_to: 抄送机关
            doc_number: 发文字号（如"国办发〔2024〕1号"）
            issuer: 签发人
            attachment: 附件说明
            security_level: 密级
            urgency: 紧急程度
        """
        try:
            # 创建PDF文档
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                leftMargin=MARGIN_LEFT * mm,
                rightMargin=MARGIN_RIGHT * mm,
                topMargin=MARGIN_TOP * mm,
                bottomMargin=MARGIN_BOTTOM * mm,
            )

            story = []
            body_width = BODY_WIDTH * mm

            # ==================== 版头部分 ====================
            # 根据GB/T 9704-2012，版头包含：
            # 1. 份号（左上角）
            # 2. 密级和保密期限
            # 3. 紧急程度
            # 4. 发文机关标志（红色，居中，上边缘距版心上边缘35mm）
            # 5. 发文字号（标志下空二行，居中）
            # 6. 签发人（上行文需要，居右空一字）
            # 7. 红色分隔线（发文字号下4mm处）

            # 发文机关标志（如果提供了sender）
            if sender:
                # 标准格式：发文机关全称或简称 + "文件"
                org_logo_text = f"{sender}文件"
                story.append(Spacer(1, 20 * mm))  # 上边缘至版心上边缘约35mm
                story.append(Paragraph(org_logo_text, self.org_logo_style))
                story.append(Spacer(1, 2 * FONT_SIZE_SAN_HAO))  # 标志下空二行

                # 发文字号
                if doc_number:
                    story.append(Paragraph(doc_number, self.doc_number_style))
                    story.append(Spacer(1, 4 * mm))  # 发文字号下4mm处印红色分隔线
                else:
                    story.append(Spacer(1, FONT_SIZE_SAN_HAO * 2 + 4 * mm))

                # 红色分隔线（与版心等宽，粗线约0.35mm）
                red_line = self._create_red_line_flowable(BODY_WIDTH, thickness_mm=0.35)
                story.append(red_line)
                story.append(Spacer(1, FONT_SIZE_ER_HAO * 2.5))  # 红色分隔线下空二行（约44磅）
            else:
                # 如果没有发文机关，添加适当的顶部间距
                story.append(Spacer(1, 20 * mm))

            # ==================== 主体部分 ====================

            # 1. 标题（二号小标宋，居中，红色分隔线下空二行）
            if title:
                # 处理长标题换行，保持词意完整
                story.append(Paragraph(title, self.title_style))

            # 2. 主送机关（三号仿宋，顶格，标题下空一行）
            if main_recipient:
                story.append(Paragraph(f"{main_recipient}：", self.recipient_style))

            # 3. 正文（三号仿宋，每个自然段左空二字，回行顶格）
            if content:
                paragraphs = self._process_content(content)
                for para in paragraphs:
                    if para['level'] == 1:
                        story.append(Paragraph(para['text'], self.heading1_style))
                    elif para['level'] == 2:
                        story.append(Paragraph(para['text'], self.heading2_style))
                    elif para['level'] == 3:
                        story.append(Paragraph(para['text'], self.heading3_style))
                    else:
                        story.append(Paragraph(para['text'], self.body_style))

            # 4. 附件说明（如有）
            if attachment:
                story.append(Paragraph(f"附件：{attachment}", self.attachment_style))

            # 5. 发文机关署名和成文日期（右空四字）
            story.append(Spacer(1, LINE_HEIGHT_MAIN * 2))  # 正文下空二行

            if sender:
                story.append(Paragraph(sender, self.signature_style))

            if date:
                # 日期格式：2024年1月25日（阿拉伯数字，不编虚位）
                story.append(Paragraph(date, self.date_style))
            else:
                today = datetime.now()
                date_str = f"{today.year}年{today.month}月{today.day}日"
                story.append(Paragraph(date_str, self.date_style))

            # ==================== 版记部分 ====================
            if copy_to:
                story.append(Spacer(1, LINE_HEIGHT_MAIN * 2))

                # 首条分隔线（粗线 0.35mm）
                first_line = self._create_red_line_flowable(BODY_WIDTH, thickness_mm=0.35)
                story.append(first_line)
                story.append(Spacer(1, 2 * mm))

                # 抄送机关（四号仿宋，左右各空一字）
                copy_text = f"抄送：{copy_to}。"
                story.append(Paragraph(copy_text, self.footer_style))
                story.append(Spacer(1, 2 * mm))

                # 中间分隔线（细线 0.25mm，黑色）
                from reportlab.platypus import HRFlowable
                thin_line = HRFlowable(
                    width=BODY_WIDTH * mm,
                    thickness=0.25 * mm,
                    color=colors.black,
                    spaceBefore=0,
                    spaceAfter=0,
                    hAlign='CENTER'
                )
                story.append(thin_line)
                story.append(Spacer(1, 2 * mm))

                # 印发机关和印发日期（四号仿宋，左右各空一字）
                today = datetime.now()
                print_date = f"{today.year}年{today.month}月{today.day}日印发"

                # 使用表格实现左右对齐
                footer_data = [[sender if sender else '', print_date]]
                footer_table = Table(footer_data, colWidths=[BODY_WIDTH * mm / 2] * 2)
                footer_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), self.font_manager.get_font('SimFang', 'SimSun')),
                    ('FONTSIZE', (0, 0), (-1, -1), FONT_SIZE_SI_HAO),
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (0, 0), FONT_SIZE_SI_HAO),  # 左空一字
                    ('RIGHTPADDING', (1, 0), (1, 0), FONT_SIZE_SI_HAO),  # 右空一字
                ]))
                story.append(footer_table)
                story.append(Spacer(1, 2 * mm))

                # 末条分隔线（粗线 0.35mm）
                last_line = self._create_red_line_flowable(BODY_WIDTH, thickness_mm=0.35)
                story.append(last_line)

            # 生成PDF
            doc.build(story)

            return {
                'success': True,
                'output_path': output_path,
                'message': f'公文PDF已生成：{output_path}'
            }

        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': f'生成PDF失败：{str(e)}\n{traceback.format_exc()}'
            }

# ==================== 命令行接口 ====================

def parse_content(content):
    """解析公文内容，提取结构化信息"""
    result = {
        'title': None,
        'sender': None,
        'date': None,
        'main_recipient': None,
        'copy_to': None,
        'doc_number': None,
        'body': content
    }

    lines = content.strip().split('\n')

    # 提取标题（第一行非空行）
    for line in lines:
        if line.strip():
            result['title'] = line.strip()
            break

    # 提取发文机关和日期（通常在末尾）
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line and not result['sender']:
            # 检测发文机关关键字
            if any(kw in line for kw in ['局', '委', '办', '部', '政府', '院', '厅', '处', '科']):
                # 排除日期格式
                if '年' not in line or '月' not in line:
                    result['sender'] = line

        if line and not result['date']:
            # 检测日期格式：2024年1月25日 或 2024年01月25日
            if re.match(r'\d{4}年\d{1,2}月\d{1,2}日', line):
                result['date'] = line

    return result

def main():
    parser = argparse.ArgumentParser(
        description='根据GB/T 9704-2012标准生成党政机关公文PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_document.py --content "关于XXX的通知\n\n各部门：\n\n正文内容..." --title "关于XXX的通知" --sender "国务院办公厅" --output output.pdf
  python generate_document.py --input input.json --output output.pdf
        """
    )

    parser.add_argument('--input', '-i', help='输入文件路径（txt 或 json）')
    parser.add_argument('--output', '-o', help='输出 PDF 文件路径')
    parser.add_argument('--type', '-t', default='通知', choices=DOCUMENT_TYPES, help='公文类型')
    parser.add_argument('--title', help='公文标题')
    parser.add_argument('--sender', help='发文机关全称（用于版头标志和署名）')
    parser.add_argument('--date', help='成文日期（格式：2024年1月25日）')
    parser.add_argument('--recipient', help='主送机关')
    parser.add_argument('--copy-to', help='抄送机关')
    parser.add_argument('--doc-number', help='发文字号（如"国办发〔2024〕1号"）')
    parser.add_argument('--issuer', help='签发人（上行文需要）')
    parser.add_argument('--attachment', help='附件说明')
    parser.add_argument('--security-level', help='密级（绝密/机密/秘密）')
    parser.add_argument('--urgency', help='紧急程度（特急/加急）')
    parser.add_argument('--content', '-c', help='直接输入公文内容')

    args = parser.parse_args()

    # 获取内容
    content = args.content
    if args.input:
        if not os.path.exists(args.input):
            print(json.dumps({
                'success': False,
                'error': f'输入文件不存在：{args.input}'
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

        with open(args.input, 'r', encoding='utf-8') as f:
            input_data = f.read()

        # 尝试解析为 JSON
        try:
            data = json.loads(input_data)
            content = data.get('content', input_data)
            args.title = args.title or data.get('title')
            args.sender = args.sender or data.get('sender')
            args.date = args.date or data.get('date')
            args.recipient = args.recipient or data.get('recipient')
            args.copy_to = args.copy_to or data.get('copy_to')
            args.doc_number = args.doc_number or data.get('doc_number')
            args.issuer = args.issuer or data.get('issuer')
            args.attachment = args.attachment or data.get('attachment')
        except:
            content = input_data

    if not content:
        print(json.dumps({
            'success': False,
            'error': '请提供公文内容（通过--input 或 --content 参数）'
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 自动解析内容
    parsed = parse_content(content)
    args.title = args.title or parsed.get('title')
    args.sender = args.sender or parsed.get('sender')
    args.date = args.date or parsed.get('date')

    # 设置输出路径
    output_path = args.output
    if not output_path:
        output_path = f"公文_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    # 创建生成器并生成PDF
    generator = OfficialDocumentGenerator()
    result = generator.generate(
        content=content,
        output_path=output_path,
        doc_type=args.type,
        title=args.title,
        sender=args.sender,
        date=args.date,
        main_recipient=args.recipient,
        copy_to=args.copy_to,
        doc_number=args.doc_number,
        issuer=args.issuer,
        attachment=args.attachment,
        security_level=args.security_level,
        urgency=args.urgency
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result['success']:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
