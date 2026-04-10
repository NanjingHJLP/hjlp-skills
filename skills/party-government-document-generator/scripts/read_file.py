#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
公文文件读取脚本
支持读取 txt 和 pdf 文件，提取文字和表格内容
用法：python read_file.py <文件路径>
"""

import sys
import os
import json

def read_txt_file(file_path):
    """读取 txt 文件内容"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            return {
                'success': True,
                'content': content,
                'file_type': 'txt',
                'encoding': encoding
            }
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return {
                'success': False,
                'error': f"读取文件失败：{str(e)}",
                'file_type': 'txt'
            }
    
    return {
        'success': False,
        'error': "无法识别文件编码，请尝试其他编码格式",
        'file_type': 'txt'
    }

def read_pdf_file(file_path):
    """读取 PDF 文件内容"""
    try:
        # 尝试使用 pdfplumber
        import pdfplumber
        
        text_content = []
        tables_content = []
        
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # 提取文字
                page_text = page.extract_text()
                if page_text:
                    text_content.append(f"--- 第 {i+1} 页 ---\n{page_text}")
                
                # 提取表格
                tables = page.extract_tables()
                if tables:
                    for j, table in enumerate(tables):
                        table_str = "表格内容:\n"
                        for row in table:
                            if row:
                                table_str += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"
                        tables_content.append(table_str)
        
        result = {
            'success': True,
            'content': '\n\n'.join(text_content),
            'tables': '\n\n'.join(tables_content) if tables_content else None,
            'file_type': 'pdf',
            'pages': len(pdf.pages)
        }
        return result
        
    except ImportError:
        # pdfplumber 未安装，尝试 PyPDF2
        try:
            import PyPDF2
            
            text_content = []
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(f"--- 第 {i+1} 页 ---\n{page_text}")
            
            return {
                'success': True,
                'content': '\n\n'.join(text_content),
                'tables': None,
                'file_type': 'pdf',
                'pages': len(reader.pages),
                'note': '表格提取需要 pdfplumber 库'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"读取 PDF 失败：{str(e)}",
                'file_type': 'pdf'
            }
    except Exception as e:
        return {
            'success': False,
            'error': f"读取 PDF 失败：{str(e)}",
            'file_type': 'pdf'
        }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            'success': False,
            'error': '请提供文件路径',
            'usage': 'python read_file.py <文件路径>'
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(json.dumps({
            'success': False,
            'error': f'文件不存在：{file_path}'
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    
    # 根据文件扩展名选择读取方式
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.txt':
        result = read_txt_file(file_path)
    elif file_ext == '.pdf':
        result = read_pdf_file(file_path)
    else:
        # 尝试作为 txt 读取
        result = read_txt_file(file_path)
    
    # 输出 JSON 结果
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
