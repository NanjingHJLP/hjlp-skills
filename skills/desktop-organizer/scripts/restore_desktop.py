#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恢复桌面到整理前的状态
"""

import os
import json
import shutil
import glob
from pathlib import Path


def find_latest_backup():
    """查找最新的备份记录"""
    backup_dir = Path(__file__).parent.parent / "assets" / "backup"
    
    if not backup_dir.exists():
        return None
    
    backup_files = list(backup_dir.glob("backup_*.json"))
    if not backup_files:
        return None
    
    # 按修改时间排序，取最新的
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return str(backup_files[0])


def list_backups():
    """列出所有可用的备份"""
    backup_dir = Path(__file__).parent.parent / "assets" / "backup"
    
    if not backup_dir.exists():
        return []
    
    backups = []
    for f in backup_dir.glob("backup_*.json"):
        stat = f.stat()
        from datetime import datetime
        backups.append({
            "path": str(f),
            "name": f.name,
            "time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "size": stat.st_size
        })
    
    backups.sort(key=lambda x: x["time"], reverse=True)
    return backups


def restore_from_backup(backup_path, approved=False):
    """从备份恢复桌面"""
    if not os.path.exists(backup_path):
        print(f"错误: 备份文件不存在: {backup_path}")
        return False
    
    with open(backup_path, "r", encoding="utf-8") as f:
        backup = json.load(f)
    
    if not approved:
        print("错误: 未经用户批准不能执行恢复操作")
        print("请确认要恢复桌面到整理前的状态")
        return False
    
    results = {
        "restored": [],
        "failed": [],
        "already_in_place": []
    }
    
    print(f"\n正在从备份恢复: {backup_path}")
    print(f"备份时间: {backup.get('timestamp', '未知')}")
    print(f"需要恢复的项目数: {len(backup.get('original_locations', []))}")
    print()
    
    for item in backup.get("original_locations", []):
        source = item["target"]  # 备份中target是移动后的位置
        target = item["source"]  # source是原始位置
        
        try:
            # 检查文件是否还在原位置
            if not os.path.exists(source):
                # 可能已经手动移动过了，检查目标位置
                if os.path.exists(target):
                    results["already_in_place"].append(item)
                    continue
                else:
                    results["failed"].append({"item": item, "reason": "找不到文件"})
                    continue
            
            # 确保目标目录存在
            target_dir = os.path.dirname(target)
            os.makedirs(target_dir, exist_ok=True)
            
            # 处理目标已存在的情况
            if os.path.exists(target):
                # 如果目标已存在，可能是恢复过了或同名文件
                results["already_in_place"].append(item)
                continue
            
            # 执行恢复移动
            shutil.move(source, target)
            results["restored"].append({"from": source, "to": target})
            print(f"已恢复: {os.path.basename(source)} -> 桌面")
            
        except Exception as e:
            results["failed"].append({"item": item, "error": str(e)})
            print(f"失败: {os.path.basename(source)} - {e}")
    
    print(f"\n恢复完成!")
    print(f"成功恢复: {len(results['restored'])}")
    print(f"已在原位: {len(results['already_in_place'])}")
    print(f"失败: {len(results['failed'])}")
    
    # 尝试清理空文件夹
    cleanup_empty_folders()
    
    return results


def cleanup_empty_folders():
    """清理空的分类文件夹"""
    desktops = [
        Path.home() / "Desktop",
        Path("C:/Users/Public/Desktop")
    ]
    
    categories = ["文档", "图片", "视频", "音频", "压缩包", "程序", "代码", 
                  "快捷方式", "软件快捷方式", "文件夹快捷方式", "网页快捷方式", 
                  "其他快捷方式", "其他", "文件夹"]
    
    for desktop in desktops:
        if not desktop.exists():
            continue
        
        for category in categories:
            folder = desktop / category
            if folder.exists() and folder.is_dir():
                try:
                    # 检查是否为空
                    if not any(folder.iterdir()):
                        folder.rmdir()
                        print(f"已删除空文件夹: {folder}")
                except:
                    pass


def preview_restore(backup_path):
    """预览恢复操作"""
    if not os.path.exists(backup_path):
        print(f"错误: 备份文件不存在: {backup_path}")
        return
    
    with open(backup_path, "r", encoding="utf-8") as f:
        backup = json.load(f)
    
    print("\n" + "="*70)
    print("桌面恢复预览")
    print("="*70)
    print(f"备份文件: {backup_path}")
    print(f"备份时间: {backup.get('timestamp', '未知')}")
    print(f"\n将恢复以下 {len(backup.get('original_locations', []))} 个项目到原始位置:")
    
    for item in backup.get("original_locations", [])[:20]:
        print(f"  {item['filename']} ({item['category']})")
        print(f"    从: {item['target']}")
        print(f"    到: {item['source']}")
    
    if len(backup.get("original_locations", [])) > 20:
        print(f"  ... 还有 {len(backup['original_locations']) - 20} 个项目")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="恢复桌面到整理前状态")
    parser.add_argument("--list", action="store_true", help="列出所有备份")
    parser.add_argument("--backup", help="指定备份文件路径")
    parser.add_argument("--preview", action="store_true", help="仅预览不执行")
    parser.add_argument("--yes", action="store_true", help="确认执行恢复")
    parser.add_argument("--latest", action="store_true", help="使用最新的备份")
    
    args = parser.parse_args()
    
    if args.list:
        backups = list_backups()
        if backups:
            print("可用的备份文件:")
            for i, b in enumerate(backups, 1):
                print(f"  {i}. {b['name']} ({b['time']})")
        else:
            print("没有找到备份文件")
    
    elif args.preview:
        if args.backup:
            preview_restore(args.backup)
        elif args.latest:
            latest = find_latest_backup()
            if latest:
                preview_restore(latest)
            else:
                print("没有找到备份文件")
        else:
            print("请使用 --backup 指定备份文件或使用 --latest 使用最新备份")
    
    elif args.yes:
        backup_path = None
        if args.backup:
            backup_path = args.backup
        elif args.latest:
            backup_path = find_latest_backup()
        
        if backup_path:
            restore_from_backup(backup_path, approved=True)
        else:
            print("错误: 未指定备份文件")
    
    else:
        print("桌面恢复工具")
        print("\n用法:")
        print("  python restore_desktop.py --list                    # 列出所有备份")
        print("  python restore_desktop.py --latest --preview        # 预览最新备份")
        print("  python restore_desktop.py --latest --yes            # 执行恢复")
        print("  python restore_desktop.py --backup <路径> --yes     # 指定备份恢复")
