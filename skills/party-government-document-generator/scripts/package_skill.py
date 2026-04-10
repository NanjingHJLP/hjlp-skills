#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Skill 打包脚本
将 Skill 目录打包为 .skill 文件（本质是 zip 文件）
用法：python package_skill.py <skill 目录路径> [输出目录]
"""

import sys
import os
import zipfile
import json
import yaml

def validate_skill(skill_path):
    """验证 Skill 目录结构"""
    errors = []
    warnings = []
    
    # 检查 SKILL.md 是否存在
    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.exists(skill_md):
        errors.append("缺少 SKILL.md 文件")
        return errors, warnings
    
    # 验证 frontmatter
    with open(skill_md, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not content.startswith('---'):
        errors.append("SKILL.md 缺少 YAML frontmatter")
        return errors, warnings
    
    # 解析 frontmatter
    try:
        end_marker = content.find('---', 3)
        if end_marker == -1:
            errors.append("SKILL.md frontmatter 格式错误")
            return errors, warnings
        
        frontmatter = yaml.safe_load(content[3:end_marker])
        
        if not frontmatter:
            errors.append("SKILL.md frontmatter 为空")
            return errors, warnings
        
        if 'name' not in frontmatter:
            errors.append("SKILL.md 缺少 name 字段")
        
        if 'description' not in frontmatter:
            errors.append("SKILL.md 缺少 description 字段")
        elif len(frontmatter['description']) < 20:
            warnings.append("description 可能过短，建议更详细描述触发场景")
        
    except yaml.YAMLError as e:
        errors.append(f"YAML frontmatter 解析失败：{e}")
    
    # 检查目录结构
    scripts_dir = os.path.join(skill_path, "scripts")
    references_dir = os.path.join(skill_path, "references")
    assets_dir = os.path.join(skill_path, "assets")
    
    if os.path.exists(scripts_dir):
        scripts = [f for f in os.listdir(scripts_dir) if f.endswith('.py')]
        if scripts:
            print(f"  找到 {len(scripts)} 个脚本文件")
    
    if os.path.exists(references_dir):
        refs = [f for f in os.listdir(references_dir) if f.endswith('.md')]
        if refs:
            print(f"  找到 {len(refs)} 个参考文档")
    
    if os.path.exists(assets_dir):
        assets = os.listdir(assets_dir)
        if assets:
            print(f"  找到 {len(assets)} 个资产文件")
    
    return errors, warnings

def package_skill(skill_path, output_dir=None):
    """打包 Skill 为 .skill 文件"""
    
    # 获取 Skill 名称
    skill_name = os.path.basename(skill_path)
    
    # 确定输出路径
    if output_dir is None:
        output_dir = os.path.dirname(skill_path)
    
    output_file = os.path.join(output_dir, f"{skill_name}.skill")
    
    # 验证 Skill
    print(f"验证 Skill: {skill_path}")
    errors, warnings = validate_skill(skill_path)
    
    if warnings:
        print("\n警告:")
        for w in warnings:
            print(f"  - {w}")
    
    if errors:
        print("\n错误:")
        for e in errors:
            print(f"  - {e}")
        return None
    
    print("\n验证通过，开始打包...")
    
    # 创建 zip 文件
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(skill_path):
            for file in files:
                if file.endswith('.skill'):
                    continue  # 跳过 .skill 文件
                
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(skill_path))
                zipf.write(file_path, arcname)
                print(f"  添加：{arcname}")
    
    print(f"\n打包完成：{output_file}")
    print(f"文件大小：{os.path.getsize(output_file) / 1024:.1f} KB")
    
    return output_file

def main():
    if len(sys.argv) < 2:
        print("用法：python package_skill.py <skill 目录路径> [输出目录]")
        sys.exit(1)
    
    skill_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.isdir(skill_path):
        print(f"错误：目录不存在：{skill_path}")
        sys.exit(1)
    
    result = package_skill(skill_path, output_dir)
    
    if result:
        print("\n[OK] Skill 打包成功")
        sys.exit(0)
    else:
        print("\n[FAIL] Skill 打包失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
