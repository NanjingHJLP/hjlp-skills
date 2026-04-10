#!/usr/bin/env python3
"""
漫画生成器主脚本：管理页面状态、调用图像生成、处理编辑操作。
注意：本脚本不直接调用 image_generate 工具，而是提供函数供 Agent 在 python_execute 中使用。
"""

import os
import json
import shutil
from datetime import datetime

class ComicPage:
    """单页漫画"""
    def __init__(self, page_id, text, style='color'):
        self.page_id = page_id
        self.original_text = text
        self.current_text = text
        self.style = style  # 'sketch' 或 'color'
        self.image_path = None
        self.edited = False
        self.generate_prompt()
    
    def generate_prompt(self):
        """根据风格和文本生成图像 prompt"""
        base_prompt = f"{self.current_text}, 漫画风格"
        if self.style == 'sketch':
            self.prompt = f"{base_prompt}, 素描, 黑白线稿, 清晰线条, 背景丰富, 人物生动"
        else:
            self.prompt = f"{base_prompt}, 彩绘, 色彩鲜艳, 细节丰富, 漫画书风格"
        return self.prompt
    
    def update_text(self, new_text):
        """更新文本并重新生成 prompt"""
        self.current_text = new_text
        self.edited = True
        self.generate_prompt()
    
    def update_style(self, new_style):
        """更新风格并重新生成 prompt"""
        self.style = new_style
        self.generate_prompt()
    
    def set_image_path(self, path):
        self.image_path = path
    
    def to_dict(self):
        return {
            'page_id': self.page_id,
            'original_text': self.original_text,
            'current_text': self.current_text,
            'style': self.style,
            'image_path': self.image_path,
            'edited': self.edited,
            'prompt': self.prompt
        }

class ComicProject:
    """整个漫画项目"""
    def __init__(self, project_name, style='color'):
        self.project_name = project_name
        self.style = style
        self.pages = []
        self.created_at = datetime.now()
        self.work_dir = os.path.join(os.path.expanduser('~'), 'Desktop', f'comic_{project_name}_{self.created_at.strftime("%Y%m%d_%H%M%S")}')
        os.makedirs(self.work_dir, exist_ok=True)
        self.images_dir = os.path.join(self.work_dir, 'images')
        os.makedirs(self.images_dir, exist_ok=True)
    
    def add_page(self, text):
        page_id = len(self.pages) + 1
        page = ComicPage(page_id, text, self.style)
        self.pages.append(page)
        return page
    
    def add_pages(self, texts):
        for text in texts:
            self.add_page(text)
    
    def get_page(self, page_id):
        """获取指定页面（1-based）"""
        if 1 <= page_id <= len(self.pages):
            return self.pages[page_id-1]
        return None
    
    def edit_page_text(self, page_id, new_text):
        page = self.get_page(page_id)
        if page:
            page.update_text(new_text)
            return True
        return False
    
    def edit_page_style(self, page_id, new_style):
        page = self.get_page(page_id)
        if page:
            page.update_style(new_style)
            return True
        return False
    
    def save_project(self):
        """保存项目状态到 JSON 文件"""
        project_file = os.path.join(self.work_dir, 'project.json')
        data = {
            'project_name': self.project_name,
            'style': self.style,
            'created_at': self.created_at.isoformat(),
            'pages': [p.to_dict() for p in self.pages]
        }
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return project_file
    
    def load_project(project_file):
        """从 JSON 文件加载项目"""
        with open(project_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        project = ComicProject(data['project_name'], data['style'])
        project.created_at = datetime.fromisoformat(data['created_at'])
        project.pages = []
        
        for page_data in data['pages']:
            page = ComicPage(page_data['page_id'], page_data['original_text'], page_data['style'])
            page.current_text = page_data['current_text']
            page.image_path = page_data['image_path']
            page.edited = page_data['edited']
            project.pages.append(page)
        
        return project
    
    def generate_image_filename(self, page_id, suffix=''):
        """生成图像文件名"""
        base = f'page_{page_id:03d}'
        if suffix:
            base = f'{base}_{suffix}'
        return os.path.join(self.images_dir, f'{base}.png')

def preview_pages(project):
    """生成预览文本"""
    preview = f"漫画项目: {project.project_name}\n"
    preview += f"风格: {'素描' if project.style == 'sketch' else '彩绘'}\n"
    preview += f"页数: {len(project.pages)}\n\n"
    
    for i, page in enumerate(project.pages, 1):
        preview += f"第 {i} 页:\n"
        preview += f"  文本: {page.current_text[:50]}...\n"
        preview += f"  图像: {page.image_path if page.image_path else '未生成'}\n"
        preview += f"  编辑: {'是' if page.edited else '否'}\n\n"
    
    return preview

if __name__ == '__main__':
    # 测试代码
    project = ComicProject("测试漫画", style='color')
    project.add_pages([
        "一个英雄站在山顶上，眺望远方",
        "英雄拔出剑，准备战斗",
        "英雄与怪物激烈交战"
    ])
    print(preview_pages(project))
    
    # 编辑第一页
    project.edit_page_text(1, "一个英雄站在山顶上，眺望远方，阳光洒在他身上")
    print("编辑后第一页 prompt:", project.pages[0].prompt)
    
    # 保存项目
    project_file = project.save_project()
    print(f"项目已保存: {project_file}")