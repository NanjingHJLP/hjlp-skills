#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
formPDF - 漫画PDF生成工具
功能：根据JSON配置文件，将图像和文字组合成PDF文档
用法：formPDF.exe --config config.json --output output.pdf
"""

import argparse
import json
import sys
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image


def get_default_font():
    """获取系统默认中文字体"""
    font_paths = [
        # Windows 字体
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
        # Linux 字体
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # macOS 字体
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            return font_path
    return None


def register_font():
    """注册中文字体，返回字体名称"""
    font_path = get_default_font()
    if font_path:
        font_name = "CustomFont"
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            return font_name
        except:
            pass
    return "Helvetica"  # 回退字体


def mm_to_points(mm):
    """毫米转点"""
    return mm * 2.83465


def create_pdf(config_path, output_path):
    """根据配置文件创建PDF"""
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    pages = config.get("pages", [])
    layout = config.get("layout", {})
    
    # 页面设置（默认A4）
    page_width_mm = layout.get("page_width", 210)
    page_height_mm = layout.get("page_height", 297)
    margin_mm = layout.get("margin", 10)
    image_height_mm = layout.get("image_height", 180)
    font_size = layout.get("font_size", 12)
    
    # 转换为点
    page_width = mm_to_points(page_width_mm)
    page_height = mm_to_points(page_height_mm)
    margin = mm_to_points(margin_mm)
    image_height = mm_to_points(image_height_mm)
    
    # 可用内容区域
    content_width = page_width - 2 * margin
    
    # 注册字体
    font_name = register_font()
    
    # 创建PDF
    c = canvas.Canvas(output_path, pagesize=(page_width, page_height))
    
    for page_data in pages:
        image_path = page_data.get("image", "")
        text = page_data.get("text", "")
        
        if not image_path or not os.path.exists(image_path):
            print(f"警告: 图像文件不存在: {image_path}")
            c.showPage()
            continue
        
        # 添加图像
        try:
            # 计算图像显示尺寸
            img = Image.open(image_path)
            img_width, img_height_px = img.size
            aspect = img_width / img_height_px
            
            # 图像显示宽度占满内容区域
            display_width = content_width
            display_height = display_width / aspect
            
            # 如果高度超过设定值，则限制高度
            if display_height > image_height:
                display_height = image_height
                display_width = display_height * aspect
            
            # 居中显示图像
            x = margin + (content_width - display_width) / 2
            y = page_height - margin - display_height
            
            c.drawImage(image_path, x, y, width=display_width, height=display_height)
            
            # 图像下方的文字起始位置
            text_y = y - mm_to_points(10)  # 图像下方10mm
            
        except Exception as e:
            print(f"添加图像时出错: {e}")
            text_y = page_height - margin - mm_to_points(20)
        
        # 添加文字
        c.setFont(font_name, font_size)
        c.setFillColorRGB(0, 0, 0)
        
        # 文字区域
        text_x = margin
        text_width = content_width
        line_height = font_size * 1.5
        
        # 简单的文本换行处理
        lines = wrap_text(text, text_width, font_name, font_size, c)
        
        for line in lines:
            if text_y < margin:  # 超出页面底部
                break
            c.drawString(text_x, text_y, line)
            text_y -= line_height
        
        # 新页面
        c.showPage()
    
    # 保存PDF
    c.save()
    print(f"PDF已生成: {output_path}")


def wrap_text(text, max_width, font_name, font_size, canvas_obj):
    """简单的文本换行"""
    words = text
    lines = []
    current_line = ""
    
    for char in words:
        test_line = current_line + char
        width = canvas_obj.stringWidth(test_line, font_name, font_size)
        
        if width > max_width:
            if current_line:
                lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    
    if current_line:
        lines.append(current_line)
    
    # 如果没有换行（整段文字都能放下），直接返回原文字
    if not lines:
        lines = [text]
    
    return lines


def main():
    parser = argparse.ArgumentParser(
        description="formPDF - 漫画PDF生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  formPDF.exe --config config.json --output comic.pdf
  formPDF.exe -c config.json -o comic.pdf
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        required=True,
        help="JSON配置文件路径"
    )
    
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="输出PDF文件路径"
    )
    
    args = parser.parse_args()
    
    # 检查配置文件是否存在
    if not os.path.exists(args.config):
        print(f"错误: 配置文件不存在: {args.config}")
        sys.exit(1)
    
    # 创建输出目录
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 创建PDF
    try:
        create_pdf(args.config, args.output)
    except Exception as e:
        print(f"生成PDF时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
