#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行桌面整理计划
"""

import os
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def create_backup_record(plan):
    """创建备份记录用于恢复"""
    backup = {
        "timestamp": datetime.now().isoformat(),
        "original_locations": []
    }
    
    # 收集所有原始位置信息
    all_moves = plan.get("move_plan", []) + plan.get("review_items", [])
    for item in all_moves:
        backup["original_locations"].append({
            "source": item["source"],
            "target": item["target"],
            "filename": item["filename"],
            "category": item["category"]
        })
    
    # 保存备份记录
    backup_dir = Path(__file__).parent.parent / "assets" / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)
    
    return str(backup_path)


def execute_plan(plan_path, approved=False):
    """执行整理计划"""
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)
    
    if not approved:
        print("错误: 未经用户批准不能执行移动操作")
        return False
    
    # 创建备份记录
    backup_path = create_backup_record(plan)
    print(f"备份记录已创建: {backup_path}")
    
    results = {
        "success": [],
        "failed": [],
        "skipped": []
    }
    
    # 执行移动计划
    for item in plan.get("move_plan", []):
        try:
            source = item["source"]
            target = item["target"]
            
            # 跳过不存在的源文件
            if not os.path.exists(source):
                results["skipped"].append({"item": item, "reason": "源文件不存在"})
                continue
            
            # 创建目标文件夹
            target_dir = os.path.dirname(target)
            os.makedirs(target_dir, exist_ok=True)
            
            # 处理冲突
            if os.path.exists(target):
                # 重命名冲突文件
                base, ext = os.path.splitext(target)
                counter = 1
                new_target = f"{base}_{counter}{ext}"
                while os.path.exists(new_target):
                    counter += 1
                    new_target = f"{base}_{counter}{ext}"
                target = new_target
            
            # 执行移动
            shutil.move(source, target)
            results["success"].append({"source": source, "target": target})
            print(f"已移动: {os.path.basename(source)} -> {os.path.basename(target_dir)}/")
            
        except Exception as e:
            results["failed"].append({"item": item, "error": str(e)})
            print(f"失败: {os.path.basename(source)} - {e}")
    
    # 保存执行结果
    result_path = Path(plan_path).parent / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n执行完成!")
    print(f"成功: {len(results['success'])}")
    print(f"失败: {len(results['failed'])}")
    print(f"跳过: {len(results['skipped'])}")
    
    return results


def preview_plan(plan_path):
    """预览整理计划"""
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)
    
    print("\n" + "="*70)
    print("桌面整理计划预览")
    print("="*70)
    
    # 建议的文件夹
    print("\n【建议创建的文件夹】")
    for folder in plan.get("suggested_folders", []):
        folder_name = folder['name']
        count = folder['count']
        print(f"  📁 {folder_name} ({count} 个项目)")
        
        # 显示快捷方式的子文件夹结构
        if folder_name == "快捷方式" and "sub_folders" in folder:
            for sub in folder["sub_folders"]:
                print(f"      └─ 📂 {sub['name']} ({sub['count']} 个项目)")
    
    # 移动计划
    print(f"\n【移动计划】共 {len(plan.get('move_plan', []))} 个项目")
    for item in plan.get("move_plan", [])[:20]:  # 只显示前20个
        conflict_mark = " ⚠️冲突" if item.get("conflict") else ""
        sub_cat = f" / {item['sub_category']}" if item.get('sub_category') else ""
        print(f"  {item['filename']}")
        print(f"    {item['source']}")
        print(f"    -> {item['category']}{sub_cat} / {item['filename']}{conflict_mark}")
    
    if len(plan.get("move_plan", [])) > 20:
        print(f"  ... 还有 {len(plan['move_plan']) - 20} 个项目")
    
    # 审查列表
    if plan.get("review_items"):
        print(f"\n【需要审查的项目】共 {len(plan['review_items'])} 个")
        for item in plan.get("review_items", []):
            print(f"  ⚠️ {item['filename']} ({item['category']})")
            if item.get("conflict"):
                print(f"     原因: 目标位置已存在同名文件")
    
    print("\n" + "="*70)
    print("请检查以上计划，确认无误后执行整理")
    print("="*70)
    
    return plan


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="执行桌面整理计划")
    parser.add_argument("plan", help="整理计划JSON文件路径")
    parser.add_argument("--preview", action="store_true", help="仅预览不执行")
    parser.add_argument("--yes", action="store_true", help="确认执行（需用户批准）")
    
    args = parser.parse_args()
    
    if args.preview:
        preview_plan(args.plan)
    elif args.yes:
        execute_plan(args.plan, approved=True)
    else:
        print("用法:")
        print(f"  python execute_organize.py {args.plan} --preview  # 预览计划")
        print(f"  python execute_organize.py {args.plan} --yes      # 执行整理")
