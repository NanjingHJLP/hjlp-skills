#!/usr/bin/env python3
"""
文本处理工具：读取文本文件或 .docx 文件，并按指定方式分割场景。
"""

import os
import re
from docx import Document

def read_text_file(filepath):
    """读取纯文本文件（.txt）"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def read_docx_file(filepath):
    """读取 Word 文档（.docx）"""
    doc = Document(filepath)
    return '\n'.join([para.text for para in doc.paragraphs])

def split_by_paragraphs(text):
    """按空行分割段落"""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return paragraphs

def split_by_sentences(text):
    """按句子分割（简单句号、问号、感叹号）"""
    sentences = re.split(r'(?<=[。！？])', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

def split_by_custom(text, delimiter):
    """按自定义分隔符分割"""
    parts = text.split(delimiter)
    parts = [p.strip() for p in parts if p.strip()]
    return parts

def auto_split(text, method='paragraph'):
    """
    自动分割文本
    method: 'paragraph', 'sentence', 或自定义分隔符字符串
    """
    if method == 'paragraph':
        return split_by_paragraphs(text)
    elif method == 'sentence':
        return split_by_sentences(text)
    else:
        return split_by_custom(text, method)

if __name__ == '__main__':
    # 测试代码
    test_text = """这是一个测试段落。

这是第二个段落。包含两个句子。对吧？
第三个段落！"""
    print("原文:", test_text)
    print("按段落分割:", split_by_paragraphs(test_text))
    print("按句子分割:", split_by_sentences(test_text))
    print("按'。'分割:", split_by_custom(test_text, '。'))