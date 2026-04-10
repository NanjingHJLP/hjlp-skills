#!/usr/bin/env python3
"""
Skill 打包脚本：将 Skill 目录打包为 .skill 文件（zip 格式）
"""

import os
import zipfile
import sys
from datetime import datetime

def package_skill(skill_dir, output_dir=None):
    """
    打包 Skill 目录
    skill_dir: Skill 根目录（包含 SKILL.md）
    output_dir: 输出目录，默认 skill_dir 父目录
    """
    # 验证 Skill 结构
    skill_md = os.path.join(skill_dir, 'SKILL.md')
    if not os.path.exists(skill_md):
        print(f"错误: {skill_dir} 中未找到 SKILL.md")
        return False
    
    # 读取 SKILL.md 获取 Skill 名称
    with open(skill_md, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 从 frontmatter 提取 name（简单解析）
    import re
    match = re.search(r'name:\s*(.+)', content)
    if match:
        skill_name = match.group(1).strip()
    else:
        # 使用目录名
        skill_name = os.path.basename(skill_dir)
    
    # 清理名称，移除空格和特殊字符
    skill_name_clean = re.sub(r'[^\w\-]', '_', skill_name)
    
    # 确定输出路径
    if output_dir is None:
        output_dir = os.path.dirname(skill_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{skill_name_clean}-{timestamp}.skill"
    output_path = os.path.join(output_dir, output_filename)
    
    # 创建 zip 文件
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 遍历所有文件
        for root, dirs, files in os.walk(skill_dir):
            # 跳过隐藏目录和文件
            files = [f for f in files if not f[0] == '.']
            dirs[:] = [d for d in dirs if not d[0] == '.']
            
            for file in files:
                file_path = os.path.join(root, file)
                # 计算在 zip 中的相对路径
                arcname = os.path.relpath(file_path, skill_dir)
                zipf.write(file_path, arcname)
    
    print(f"Skill 打包完成: {output_path}")
    print(f"Skill 名称: {skill_name}")
    print(f"文件大小: {os.path.getsize(output_path) / 1024:.1f} KB")
    
    return output_path

if __name__ == '__main__':
    # 默认打包当前目录
    skill_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 如果有命令行参数，使用第一个参数作为输出目录
    output_dir = None
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    
    package_skill(skill_dir, output_dir)