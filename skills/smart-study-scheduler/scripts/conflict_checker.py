#!/usr/bin/env python3
"""
排程冲突检测工具

检测日程安排中的冲突并提供解决建议。

用法：
    python conflict_checker.py --schedule schedule.json
    python conflict_checker.py --courses courses.json --tasks tasks.json
"""

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from pathlib import Path


@dataclass
class TimeRange:
    """时间范围"""
    start: datetime
    end: datetime
    name: str
    type: str
    
    def overlaps(self, other: 'TimeRange') -> bool:
        """检查是否重叠"""
        return self.start < other.end and other.start < self.end
    
    def overlap_duration(self, other: 'TimeRange') -> int:
        """计算重叠时长（分钟）"""
        if not self.overlaps(other):
            return 0
        overlap_start = max(self.start, other.start)
        overlap_end = min(self.end, other.end)
        return int((overlap_end - overlap_start).total_seconds() / 60)


@dataclass
class Conflict:
    """冲突信息"""
    event1: str
    event2: str
    type: str  # hard/soft
    overlap_minutes: int
    severity: str  # high/medium/low
    suggestion: str


class ConflictChecker:
    """冲突检测器"""
    
    def check_schedule(self, events: List[TimeRange]) -> List[Conflict]:
        """检查排程中的冲突
        
        Args:
            events: 日程事件列表
            
        Returns:
            冲突列表
        """
        conflicts = []
        sorted_events = sorted(events, key=lambda e: e.start)
        
        # 检查两两冲突
        for i in range(len(sorted_events)):
            for j in range(i + 1, len(sorted_events)):
                e1 = sorted_events[i]
                e2 = sorted_events[j]
                
                # 如果不重叠了，后面的也不会重叠
                if e1.end <= e2.start:
                    break
                
                if e1.overlaps(e2):
                    overlap = e1.overlap_duration(e2)
                    conflict = self._analyze_conflict(e1, e2, overlap)
                    conflicts.append(conflict)
        
        # 检查密集度问题（软约束）
        conflicts.extend(self._check_density_issues(sorted_events))
        
        # 检查疲劳度问题
        conflicts.extend(self._check_fatigue_issues(sorted_events))
        
        return conflicts
    
    def _analyze_conflict(self, e1: TimeRange, e2: TimeRange, overlap: int) -> Conflict:
        """分析冲突类型和建议"""
        # 硬约束：固定事件（课程）之间冲突
        if e1.type == "class" and e2.type == "class":
            return Conflict(
                event1=e1.name,
                event2=e2.name,
                type="hard",
                overlap_minutes=overlap,
                severity="high",
                suggestion=f"课程时间冲突，需联系教务处调整或申请调课。重叠{overlap}分钟。"
            )
        
        # 硬约束：课程与学习任务的冲突
        if (e1.type == "class" and e2.type == "study") or \
           (e1.type == "study" and e2.type == "class"):
            return Conflict(
                event1=e1.name,
                event2=e2.name,
                type="hard",
                overlap_minutes=overlap,
                severity="high",
                suggestion=f"学习任务与课程冲突，需调整学习时间。重叠{overlap}分钟。"
            )
        
        # 软约束：学习任务之间的冲突
        return Conflict(
            event1=e1.name,
            event2=e2.name,
            type="soft",
            overlap_minutes=overlap,
            severity="medium",
            suggestion=f"两项学习任务时间重叠，建议错开安排或合并处理。重叠{overlap}分钟。"
        )
    
    def _check_density_issues(self, events: List[TimeRange]) -> List[Conflict]:
        """检查密集度问题"""
        conflicts = []
        
        # 按天分组
        day_events = {}
        for e in events:
            day = e.start.date()
            if day not in day_events:
                day_events[day] = []
            day_events[day].append(e)
        
        for day, day_list in day_events.items():
            day_list.sort(key=lambda e: e.start)
            
            # 计算总学习时长
            study_duration = sum(
                (e.end - e.start).total_seconds() / 3600
                for e in day_list if e.type != "break"
            )
            
            # 检查是否超负荷（超过10小时）
            if study_duration > 10:
                conflicts.append(Conflict(
                    event1=f"{day}全天",
                    event2="-",
                    type="soft",
                    overlap_minutes=0,
                    severity="medium",
                    suggestion=f"该日学习任务过重（{study_duration:.1f}小时），建议减少任务或分散到其他日期。"
                ))
            
            # 检查连续学习时间过长
            continuous_start = None
            continuous_duration = 0
            
            for e in day_list:
                if e.type == "break":
                    if continuous_duration > 4:  # 超过4小时连续学习
                        conflicts.append(Conflict(
                            event1=f"{day}连续学习",
                            event2="-",
                            type="soft",
                            overlap_minutes=0,
                            severity="low",
                            suggestion=f"存在{continuous_duration:.1f}小时连续学习，建议增加休息间隔，避免疲劳。"
                        ))
                    continuous_duration = 0
                    continuous_start = None
                else:
                    if continuous_start is None:
                        continuous_start = e.start
                    continuous_duration += (e.end - e.start).total_seconds() / 3600
        
        return conflicts
    
    def _check_fatigue_issues(self, events: List[TimeRange]) -> List[Conflict]:
        """检查疲劳度问题"""
        conflicts = []
        
        # 按天分组
        day_events = {}
        for e in events:
            day = e.start.date()
            if day not in day_events:
                day_events[day] = []
            day_events[day].append(e)
        
        # 检查连续多天高强度学习
        high_intensity_days = []
        for day in sorted(day_events.keys()):
            study_count = len([e for e in day_events[day] if e.type == "study"])
            if study_count >= 5:  # 5个以上学习任务
                high_intensity_days.append(day)
        
        # 检查连续高强度天数
        consecutive_count = 1
        for i in range(1, len(high_intensity_days)):
            if (high_intensity_days[i] - high_intensity_days[i-1]).days == 1:
                consecutive_count += 1
            else:
                consecutive_count = 1
            
            if consecutive_count >= 5:
                conflicts.append(Conflict(
                    event1=f"连续高强度学习{consecutive_count}天",
                    event2="-",
                    type="soft",
                    overlap_minutes=0,
                    severity="medium",
                    suggestion=f"连续{consecutive_count}天学习任务较多，建议安排休息调整，避免过度疲劳。"
                ))
        
        return conflicts
    
    def suggest_resolutions(self, conflicts: List[Conflict]) -> Dict[str, List[str]]:
        """提供冲突解决建议"""
        suggestions = {
            "immediate": [],  # 立即解决
            "adjustment": [],  # 需要调整
            "review": []  # 建议回顾
        }
        
        for c in conflicts:
            if c.type == "hard":
                suggestions["immediate"].append(
                    f"[{c.severity}] {c.event1} vs {c.event2}: {c.suggestion}"
                )
            elif c.severity == "medium":
                suggestions["adjustment"].append(
                    f"{c.event1}: {c.suggestion}"
                )
            else:
                suggestions["review"].append(
                    f"{c.event1}: {c.suggestion}"
                )
        
        return suggestions


def load_schedule(path: str) -> List[TimeRange]:
    """从JSON加载排程"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    events = []
    for e in data.get("events", []):
        events.append(TimeRange(
            start=datetime.fromisoformat(e["start"]),
            end=datetime.fromisoformat(e["end"]),
            name=e.get("name", "未知"),
            type=e.get("type", "study")
        ))
    
    return events


def print_report(conflicts: List[Conflict], suggestions: Dict[str, List[str]]):
    """打印冲突报告"""
    print("\n" + "="*60)
    print("排程冲突检测报告")
    print("="*60)
    
    if not conflicts:
        print("\n✅ 未发现冲突，排程合理！")
        return
    
    # 统计
    hard_conflicts = [c for c in conflicts if c.type == "hard"]
    soft_conflicts = [c for c in conflicts if c.type == "soft"]
    high_severity = [c for c in conflicts if c.severity == "high"]
    
    print(f"\n📊 冲突统计：")
    print(f"  - 硬约束冲突（需立即处理）: {len(hard_conflicts)}个")
    print(f"  - 软约束建议（建议调整）: {len(soft_conflicts)}个")
    print(f"  - 高优先级: {len(high_severity)}个")
    
    # 详细冲突
    if hard_conflicts:
        print(f"\n🔴 硬约束冲突（必须解决）：")
        for c in hard_conflicts:
            print(f"  • {c.event1} <-> {c.event2}")
            print(f"    重叠: {c.overlap_minutes}分钟 | 建议: {c.suggestion}")
    
    if soft_conflicts:
        print(f"\n🟡 优化建议：")
        for c in soft_conflicts:
            if c.event2 == "-":
                print(f"  • {c.event1}")
            else:
                print(f"  • {c.event1} <-> {c.event2} (重叠{c.overlap_minutes}分钟)")
            print(f"    建议: {c.suggestion}")
    
    # 解决建议汇总
    print(f"\n💡 解决建议汇总：")
    if suggestions["immediate"]:
        print(f"\n  【需立即处理】")
        for s in suggestions["immediate"]:
            print(f"    - {s}")
    
    if suggestions["adjustment"]:
        print(f"\n  【建议调整】")
        for s in suggestions["adjustment"]:
            print(f"    - {s}")
    
    if suggestions["review"]:
        print(f"\n  【参考建议】")
        for s in suggestions["review"]:
            print(f"    - {s}")
    
    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description='排程冲突检测工具')
    parser.add_argument('--schedule', '-s', help='排程JSON文件')
    parser.add_argument('--courses', '-c', help='课程JSON文件')
    parser.add_argument('--tasks', '-t', help='任务JSON文件')
    parser.add_argument('--output', '-o', help='导出冲突报告')
    
    args = parser.parse_args()
    
    # 加载事件
    if args.schedule:
        events = load_schedule(args.schedule)
    elif args.courses and args.tasks:
        # 从课程和任务构建事件列表（简化版）
        events = []
        with open(args.courses, 'r', encoding='utf-8') as f:
            courses = json.load(f)
        for c in courses.get("courses", []):
            # 简化为假设本周的事件
            day_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, 
                       "周五": 4, "周六": 5, "周日": 6}
            day_offset = day_map.get(c.get("day", "周一"), 0)
            base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            event_date = base_date + timedelta(days=(day_offset - base_date.weekday()) % 7)
            
            h1, m1 = map(int, c.get("start_time", "08:00").split(':'))
            h2, m2 = map(int, c.get("end_time", "09:40").split(':'))
            
            events.append(TimeRange(
                start=event_date.replace(hour=h1, minute=m1),
                end=event_date.replace(hour=h2, minute=m2),
                name=c.get("name", "课程"),
                type="class"
            ))
    else:
        print("请提供 --schedule 或 --courses + --tasks 参数")
        return
    
    # 检测冲突
    checker = ConflictChecker()
    conflicts = checker.check_schedule(events)
    
    # 生成解决建议
    suggestions = checker.suggest_resolutions(conflicts)
    
    # 打印报告
    print_report(conflicts, suggestions)
    
    # 导出
    if args.output:
        report = {
            "summary": {
                "total_conflicts": len(conflicts),
                "hard_conflicts": len([c for c in conflicts if c.type == "hard"]),
                "soft_conflicts": len([c for c in conflicts if c.type == "soft"])
            },
            "conflicts": [
                {
                    "event1": c.event1,
                    "event2": c.event2,
                    "type": c.type,
                    "severity": c.severity,
                    "overlap_minutes": c.overlap_minutes,
                    "suggestion": c.suggestion
                }
                for c in conflicts
            ],
            "resolutions": suggestions
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n报告已导出: {args.output}")


if __name__ == "__main__":
    main()
