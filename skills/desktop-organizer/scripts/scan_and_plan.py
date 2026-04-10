#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桌面文件扫描与整理计划生成器
扫描用户桌面和公用桌面，按文件类型生成整理计划
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

# 文件类型分类规则（中文文件夹名）
FILE_CATEGORIES = {
    "文档": [".doc", ".docx", ".pdf", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".csv", ".ppt", ".pptx"],
    "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".ico", ".raw"],
    "视频": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"],
    "音频": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"],
    "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "程序": [".exe", ".msi", ".bat", ".cmd", ".ps1", ".sh"],
    "代码": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".h", ".php", ".go", ".rs", ".ts", ".json", ".xml", ".yml", ".yaml"],
}

# 软件类型分类规则（根据快捷方式名称或目标路径关键字判断）
SOFTWARE_CATEGORIES = {
    "浏览器": ["chrome", "firefox", "edge", "opera", "brave", "safari", "360", "搜狗", "qq浏览器", "uc"],
    "开发工具": ["code", "visual studio", "jetbrains", "pycharm", "idea", "eclipse", "sublime", "atom", "vim", "git", "github", "postman", "docker"],
    "办公软件": ["word", "excel", "powerpoint", "office", "wps", "pdf", "onenote", "outlook"],
    "通讯工具": ["微信", "qq", "钉钉", "飞书", "teams", "skype", "zoom", "腾讯会议", "钉钉"],
    "媒体播放器": ["potplayer", "vlc", "mpv", "media", "player", "音乐", "video"],
    "下载工具": ["idm", "迅雷", "xdown", "motrix", "aria", "torrent", "download"],
    "压缩工具": ["winrar", "7zip", "bandizip", "peazip", "压缩"],
    "系统工具": ["控制面板", "资源管理器", "任务管理器", "注册表", "cmd", "powershell", "终端"],
    "游戏平台": ["steam", "epic", "gog", "origin", "uplay", "battle.net", "wegame", "xbox"],
}


def get_desktop_paths():
    """获取用户桌面和公用桌面的路径"""
    user_desktop = Path.home() / "Desktop"
    public_desktop = Path("C:/Users/Public/Desktop")
    
    desktops = []
    if user_desktop.exists():
        desktops.append(("用户桌面", str(user_desktop)))
    if public_desktop.exists():
        desktops.append(("公用桌面", str(public_desktop)))
    
    return desktops


def get_software_category(target_path, shortcut_name):
    """根据目标路径和快捷方式名称判断软件类型"""
    # 合并检查文本（目标路径 + 快捷方式名称）
    check_text = (target_path + " " + shortcut_name).lower()
    
    for category, keywords in SOFTWARE_CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in check_text:
                return category
    
    return "其他软件"


def get_category(file_path):
    """根据文件扩展名判断分类"""
    ext = Path(file_path).suffix.lower()
    
    # 检查是否是快捷方式
    if ext == ".lnk":
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(file_path)
            target = shortcut.TargetPath
            
            if os.path.isdir(target):
                # 文件夹快捷方式 -> 放在快捷方式/文件夹快捷方式
                return ("快捷方式", "文件夹快捷方式")
            elif target.endswith(".exe") or target.endswith(".msi"):
                # 软件快捷方式 -> 进一步分类
                software_type = get_software_category(target, Path(file_path).stem)
                return ("快捷方式", f"软件/{software_type}")
            else:
                # 其他快捷方式 -> 放在快捷方式/其他快捷方式
                return ("快捷方式", "其他快捷方式")
        except:
            # 解析失败时，归为其他快捷方式
            return ("快捷方式", "其他快捷方式")
    
    # .url 网页快捷方式
    if ext == ".url":
        return ("快捷方式", "网页快捷方式")
    
    # 普通文件分类
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    
    return "其他"


def scan_desktops():
    """扫描所有桌面文件"""
    desktops = get_desktop_paths()
    all_files = []
    software_shortcut_count = 0
    
    for desktop_name, desktop_path in desktops:
        if not os.path.exists(desktop_path):
            continue
            
        for item in os.listdir(desktop_path):
            item_path = os.path.join(desktop_path, item)
            
            # 跳过系统文件和隐藏文件
            if item.startswith(".") or item.startswith("~"):
                continue
                
            # 跳过已经存在的分类文件夹（避免重复整理）
            skip_folders = list(FILE_CATEGORIES.keys()) + ["其他", "快捷方式", "文件夹"]
            if os.path.isdir(item_path) and item in skip_folders:
                continue
                
            file_info = {
                "name": item,
                "source_path": item_path,
                "desktop": desktop_name,
                "is_directory": os.path.isdir(item_path),
                "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0,
                "modified": datetime.fromtimestamp(os.path.getmtime(item_path)).strftime("%Y-%m-%d %H:%M"),
            }
            
            if file_info["is_directory"]:
                file_info["category"] = "文件夹"
                file_info["sub_category"] = None
            else:
                cat_result = get_category(item_path)
                if isinstance(cat_result, tuple):
                    # 快捷方式返回 (主分类, 子分类)
                    file_info["category"] = cat_result[0]
                    file_info["sub_category"] = cat_result[1]
                    # 统计软件快捷方式数量
                    if cat_result[1] and cat_result[1].startswith("软件/"):
                        software_shortcut_count += 1
                else:
                    file_info["category"] = cat_result
                    file_info["sub_category"] = None
                file_info["extension"] = Path(item_path).suffix.lower()
            
            all_files.append(file_info)
    
    # 如果软件快捷方式数量少于等于5个，不细分，全部归为"软件"
    if software_shortcut_count <= 5:
        for f in all_files:
            if f.get("sub_category") and f["sub_category"].startswith("软件/"):
                f["sub_category"] = "软件"
    
    return all_files


def generate_plan(files):
    """生成整理计划"""
    # 按分类和子分类分组
    categorized = {}
    shortcut_subcategories = {}  # 记录快捷方式的子分类统计
    
    for f in files:
        cat = f["category"]
        sub_cat = f.get("sub_category")
        
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(f)
        
        # 统计快捷方式的子分类
        if cat == "快捷方式" and sub_cat:
            if sub_cat not in shortcut_subcategories:
                shortcut_subcategories[sub_cat] = []
            shortcut_subcategories[sub_cat].append(f)
    
    plan = {
        "timestamp": datetime.now().isoformat(),
        "suggested_folders": [],
        "move_plan": [],
        "review_items": [],
        "statistics": {}
    }
    
    desktops = get_desktop_paths()
    
    for category, items in sorted(categorized.items()):
        # 只为非空分类创建文件夹
        if not items:
            continue
        
        # 处理快捷方式的子文件夹结构
        if category == "快捷方式":
            # 按子分类分组
            sub_groups = {}
            for item in items:
                sub_cat = item.get("sub_category", "其他快捷方式")
                if sub_cat not in sub_groups:
                    sub_groups[sub_cat] = []
                sub_groups[sub_cat].append(item)
            
            # 添加到建议文件夹（包含子结构）
            folder_info = {
                "name": category,
                "count": len(items),
                "sub_folders": []
            }
            for sub_name, sub_items in sorted(sub_groups.items()):
                folder_info["sub_folders"].append({
                    "name": sub_name,
                    "count": len(sub_items)
                })
            plan["suggested_folders"].append(folder_info)
            
            # 为每个文件生成移动计划（包含子文件夹路径）
            # 快捷方式统一放到用户桌面的快捷方式文件夹中
            shortcut_target_base = Path.home() / "Desktop"
            
            for item in items:
                sub_cat = item.get("sub_category", "其他快捷方式")
                
                # 快捷方式统一放在用户桌面的快捷方式文件夹中
                target_folder = shortcut_target_base / category / sub_cat
                target_path = target_folder / item["name"]
                
                # 检查目标是否已存在
                conflict = os.path.exists(target_path)
                
                move_item = {
                    "source": item["source_path"],
                    "target": str(target_path),
                    "filename": item["name"],
                    "category": category,
                    "sub_category": sub_cat,
                    "desktop": item["desktop"],  # 保留原始来源信息
                    "conflict": conflict,
                    "size": item.get("size", 0),
                    "modified": item.get("modified", "")
                }
                
                # 如果有冲突或需要用户确认的文件，放入review列表
                if conflict or item["name"].lower() in ["desktop.ini", "回收站", "此电脑", "网络", "控制面板"]:
                    plan["review_items"].append(move_item)
                else:
                    plan["move_plan"].append(move_item)
        else:
            # 普通分类处理
            plan["suggested_folders"].append({
                "name": category,
                "count": len(items),
                "items": [i["name"] for i in items]
            })
            
            # 为每个文件生成移动计划
            for item in items:
                # 根据文件来源决定目标桌面
                if item["desktop"] == "公用桌面":
                    target_base = Path("C:/Users/Public/Desktop")
                else:
                    target_base = Path.home() / "Desktop"
                
                target_folder = target_base / category
                target_path = target_folder / item["name"]
                
                # 检查目标是否已存在
                conflict = os.path.exists(target_path)
                
                move_item = {
                    "source": item["source_path"],
                    "target": str(target_path),
                    "filename": item["name"],
                    "category": category,
                    "sub_category": None,
                    "desktop": item["desktop"],
                    "conflict": conflict,
                    "size": item.get("size", 0),
                    "modified": item.get("modified", "")
                }
                
                # 如果有冲突或需要用户确认的文件，放入review列表
                if conflict or item["name"].lower() in ["desktop.ini", "回收站", "此电脑", "网络", "控制面板"]:
                    plan["review_items"].append(move_item)
                else:
                    plan["move_plan"].append(move_item)
    
    # 统计信息
    plan["statistics"] = {
        "total_files": len(files),
        "categories": len(categorized),
        "to_move": len(plan["move_plan"]),
        "to_review": len(plan["review_items"]),
        "by_category": {k: len(v) for k, v in categorized.items()},
        "shortcut_subcategories": {k: len(v) for k, v in shortcut_subcategories.items()}
    }
    
    return plan


def save_plan(plan, output_path=None):
    """保存整理计划到JSON文件"""
    if output_path is None:
        backup_dir = Path(__file__).parent.parent / "assets" / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        output_path = backup_dir / f"organize_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    
    return str(output_path)


if __name__ == "__main__":
    print("正在扫描桌面文件...")
    files = scan_desktops()
    print(f"发现 {len(files)} 个项目")
    
    print("\n正在生成整理计划...")
    plan = generate_plan(files)
    
    plan_path = save_plan(plan)
    print(f"\n计划已保存到: {plan_path}")
    
    # 输出摘要
    print("\n" + "="*60)
    print("整理计划摘要")
    print("="*60)
    print(f"总文件数: {plan['statistics']['total_files']}")
    print(f"分类数量: {plan['statistics']['categories']}")
    print(f"待移动: {plan['statistics']['to_move']}")
    print(f"需审查: {plan['statistics']['to_review']}")
    
    print("\n建议创建的文件夹:")
    for folder in plan["suggested_folders"]:
        folder_name = folder['name']
        count = folder['count']
        print(f"  [{folder_name}] - {count} 个项目")
        
        # 显示快捷方式的子文件夹结构
        if folder_name == "快捷方式" and "sub_folders" in folder:
            for sub in folder["sub_folders"]:
                print(f"    └─ [{sub['name']}] - {sub['count']} 个项目")
