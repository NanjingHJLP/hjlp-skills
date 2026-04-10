#!/usr/bin/env python3
"""
智能学习排程生成器

基于约束条件和优化策略，自动生成最优学习排程。

用法：
    python schedule_generator.py --courses courses.json --tasks tasks.json --output schedule.json
    python schedule_generator.py --input plan.yaml --format ics
"""

import argparse
import json
import yaml
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict
import random


@dataclass
class TimeSlot:
    """时间段"""
    start: datetime
    end: datetime
    
    @property
    def duration(self) -> int:
        """持续时间（分钟）"""
        return int((self.end - self.start).total_seconds() / 60)


@dataclass
class Course:
    """课程/固定事件"""
    name: str
    day: int  # 0=周一, 6=周日
    start_time: str  # "HH:MM"
    end_time: str
    location: Optional[str] = None
    is_fixed: bool = True
    
    def to_datetime(self, week_start: datetime) -> tuple:
        """转换为datetime对象"""
        date = week_start + timedelta(days=self.day)
        h1, m1 = map(int, self.start_time.split(':'))
        h2, m2 = map(int, self.end_time.split(':'))
        start = date.replace(hour=h1, minute=m1, second=0)
        end = date.replace(hour=h2, minute=m2, second=0)
        return start, end


@dataclass
class Task:
    """学习任务"""
    name: str
    subject: str
    estimated_duration: int  # 分钟
    deadline: Optional[datetime] = None
    importance: int = 5  # 1-10
    difficulty: str = "medium"  # easy/medium/hard
    priority: float = 0.0
    min_slot: int = 30  # 最小时间块


@dataclass
class StudyEvent:
    """学习事件"""
    name: str
    subject: str
    start: datetime
    end: datetime
    type: str = "study"  # study/class/break
    task_id: Optional[str] = None
    location: Optional[str] = None
    
    def to_dict(self):
        return {
            "name": self.name,
            "subject": self.subject,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "type": self.type,
            "location": self.location
        }


@dataclass
class Preferences:
    """用户偏好"""
    productive_hours: List[str] = field(default_factory=list)  # ["19:00-22:00"]
    day_start: str = "08:00"
    day_end: str = "23:00"
    break_duration: int = 15
    min_slot_size: int = 30
    prefer_morning: bool = False
    prefer_evening: bool = True
    max_continuous_study: int = 120  # 最大连续学习时间


class SmartScheduler:
    """智能排程器"""
    
    DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    def __init__(self, preferences: Preferences):
        self.preferences = preferences
        self.schedule: List[StudyEvent] = []
    
    def generate_schedule(
        self,
        fixed_events: List[Course],
        tasks: List[Task],
        week_start: datetime
    ) -> List[StudyEvent]:
        """生成排程
        
        Args:
            fixed_events: 固定事件（课程）
            tasks: 学习任务
            week_start: 周一开始日期
            
        Returns:
            完整排程
        """
        # 1. 计算任务优先级
        self._calculate_priorities(tasks)
        
        # 2. 识别可用时间段
        available_slots = self._find_available_slots(fixed_events, week_start)
        
        # 3. 智能分配任务
        scheduled = []
        remaining_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)
        
        for task in remaining_tasks:
            assigned_duration = 0
            
            while assigned_duration < task.estimated_duration:
                remaining = task.estimated_duration - assigned_duration
                
                # 找到最佳时间段
                slot = self._find_best_slot(task, available_slots, remaining)
                
                if not slot:
                    print(f"警告：无法为'{task.name}'分配足够时间")
                    break
                
                # 分配时间（不超过任务剩余时间）
                slot_duration = min(slot.duration, remaining, self.preferences.max_continuous_study)
                event_end = slot.start + timedelta(minutes=slot_duration)
                
                scheduled.append(StudyEvent(
                    name=task.name,
                    subject=task.subject,
                    start=slot.start,
                    end=event_end,
                    type="study"
                ))
                
                assigned_duration += slot_duration
                
                # 更新可用时间段
                if slot_duration < slot.duration:
                    # 剩余时间生成新时间段
                    new_slot = TimeSlot(event_end, slot.end)
                    available_slots.append(new_slot)
                available_slots.remove(slot)
                
                # 添加休息
                if assigned_duration < task.estimated_duration:
                    break_start = event_end
                    break_end = break_start + timedelta(minutes=self.preferences.break_duration)
                    scheduled.append(StudyEvent(
                        name="休息",
                        subject="break",
                        start=break_start,
                        end=break_end,
                        type="break"
                    ))
                    # 移除休息时间
                    for s in available_slots[:]:
                        if s.start < break_end and s.end > break_start:
                            available_slots.remove(s)
        
        # 4. 整合固定事件和学习事件
        fixed_study_events = []
        for course in fixed_events:
            start, end = course.to_datetime(week_start)
            fixed_study_events.append(StudyEvent(
                name=course.name,
                subject=course.name,
                start=start,
                end=end,
                type="class",
                location=course.location
            ))
        
        all_events = fixed_study_events + scheduled
        all_events.sort(key=lambda e: e.start)
        
        self.schedule = all_events
        return all_events
    
    def _calculate_priorities(self, tasks: List[Task]):
        """计算任务优先级（Eisenhower矩阵）"""
        now = datetime.now()
        
        for task in tasks:
            # 紧急度（截止日期）
            if task.deadline:
                hours_until = (task.deadline - now).total_seconds() / 3600
                if hours_until <= 24:
                    urgency = 10
                elif hours_until <= 72:
                    urgency = 8
                elif hours_until <= 168:  # 一周
                    urgency = 6
                else:
                    urgency = 4
            else:
                urgency = 5
            
            # 重要度
            importance = task.importance
            
            # 难度系数
            difficulty_score = {"easy": 1, "medium": 2, "hard": 3}.get(task.difficulty, 2)
            
            # 综合优先级
            task.priority = urgency * 0.4 + importance * 0.4 + difficulty_score * 0.2
    
    def _find_available_slots(
        self,
        fixed_events: List[Course],
        week_start: datetime
    ) -> List[TimeSlot]:
        """识别可用时间段"""
        slots = []
        
        # 每天的时间范围
        day_start_h, day_start_m = map(int, self.preferences.day_start.split(':'))
        day_end_h, day_end_m = map(int, self.preferences.day_end.split(':'))
        
        for day in range(7):
            date = week_start + timedelta(days=day)
            day_start = date.replace(hour=day_start_h, minute=day_start_m)
            day_end = date.replace(hour=day_end_h, minute=day_end_m)
            
            # 获取当天的固定事件
            day_events = []
            for event in fixed_events:
                if event.day == day:
                    start, end = event.to_datetime(week_start)
                    day_events.append((start, end))
            
            # 按时间排序
            day_events.sort()
            
            # 计算空闲时间段
            current = day_start
            for event_start, event_end in day_events:
                if current < event_start:
                    gap = int((event_start - current).total_seconds() / 60)
                    if gap >= self.preferences.min_slot_size:
                        slots.append(TimeSlot(current, event_start))
                current = max(current, event_end)
            
            # 一天结束后的空闲时间
            if current < day_end:
                gap = int((day_end - current).total_seconds() / 60)
                if gap >= self.preferences.min_slot_size:
                    slots.append(TimeSlot(current, day_end))
        
        return slots
    
    def _find_best_slot(
        self,
        task: Task,
        available_slots: List[TimeSlot],
        remaining_duration: int
    ) -> Optional[TimeSlot]:
        """找到最佳时间段"""
        candidates = []
        
        for slot in available_slots:
            if slot.duration < task.min_slot:
                continue
            
            score = 0
            slot_hour = slot.start.hour
            
            # 1. 偏好时段评分
            if self.preferences.prefer_evening and 19 <= slot_hour <= 22:
                score += 20
            if self.preferences.prefer_morning and 8 <= slot_hour <= 11:
                score += 20
            
            # 2. 黄金时间加分（困难任务安排在高效时段）
            if task.difficulty == "hard" and (19 <= slot_hour <= 22 or 9 <= slot_hour <= 11):
                score += 15
            
            # 3. 科目连续性加分（检查前一天是否有同科目）
            # 简化处理：随机加分避免过于集中
            if random.random() > 0.7:
                score += 5
            
            # 4. 时间匹配度（越接近需要的时间越好，但不要太碎）
            ideal_duration = min(remaining_duration, self.preferences.max_continuous_study)
            if slot.duration >= ideal_duration:
                score += 10
            
            # 5. 截止日期临近优先早安排
            if task.deadline:
                days_until = (task.deadline.date() - slot.start.date()).days
                if days_until <= 1:
                    score += 25
                elif days_until <= 3:
                    score += 15
            
            candidates.append((slot, score))
        
        if not candidates:
            return None
        
        # 选择评分最高的
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    def check_conflicts(self) -> List[dict]:
        """检查排程冲突"""
        conflicts = []
        events = sorted(self.schedule, key=lambda e: e.start)
        
        for i in range(len(events) - 1):
            current = events[i]
            next_event = events[i + 1]
            
            if current.end > next_event.start:
                conflicts.append({
                    "event1": current.name,
                    "event2": next_event.name,
                    "overlap": (current.end - next_event.start).total_seconds() / 60
                })
        
        return conflicts
    
    def generate_ics(self, output_path: str):
        """生成ICS日历文件"""
        from icalendar import Calendar, Event
        
        cal = Calendar()
        cal.add('prodid', '-//Smart Study Scheduler//CN')
        cal.add('version', '2.0')
        
        for event in self.schedule:
            if event.type == "break":
                continue
                
            ics_event = Event()
            ics_event.add('summary', event.name)
            ics_event.add('dtstart', event.start)
            ics_event.add('dtend', event.end)
            if event.location:
                ics_event.add('location', event.location)
            cal.add_component(ics_event)
        
        with open(output_path, 'wb') as f:
            f.write(cal.to_ical())
        
        print(f"日历文件已导出: {output_path}")
    
    def print_schedule(self, week_start: datetime):
        """打印排程表"""
        print("\n" + "="*60)
        print(f"学习排程表 ({week_start.strftime('%Y-%m-%d')} 起)")
        print("="*60)
        
        current_day = -1
        for event in self.schedule:
            day = event.start.weekday()
            if day != current_day:
                current_day = day
                print(f"\n【{self.DAYS[day]}】")
            
            time_str = f"{event.start.strftime('%H:%M')}-{event.end.strftime('%H:%M')}"
            icon = {"class": "📚", "study": "✏️", "break": "☕"}.get(event.type, "•")
            location = f" @{event.location}" if event.location else ""
            
            print(f"  {icon} {time_str} {event.name}{location}")
        
        print("\n" + "="*60)


def load_courses_from_json(path: str) -> List[Course]:
    """从JSON加载课程"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    courses = []
    for c in data.get("courses", []):
        day_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, 
                   "周五": 4, "周六": 5, "周日": 6}
        day = day_map.get(c.get("day", "周一"), 0)
        
        courses.append(Course(
            name=c.get("name", "未知课程"),
            day=day,
            start_time=c.get("start_time", "08:00"),
            end_time=c.get("end_time", "09:40"),
            location=c.get("location"),
            is_fixed=True
        ))
    
    return courses


def load_tasks_from_json(path: str) -> List[Task]:
    """从JSON加载任务"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tasks = []
    for t in data.get("tasks", []):
        deadline = None
        if t.get("deadline"):
            try:
                deadline = datetime.fromisoformat(t["deadline"])
            except:
                pass
        
        tasks.append(Task(
            name=t.get("name", "未命名任务"),
            subject=t.get("subject", "通用"),
            estimated_duration=t.get("estimated_duration", 60),
            deadline=deadline,
            importance=t.get("importance", 5),
            difficulty=t.get("difficulty", "medium")
        ))
    
    return tasks


def main():
    parser = argparse.ArgumentParser(description='智能学习排程生成器')
    parser.add_argument('--courses', '-c', help='课程JSON文件')
    parser.add_argument('--tasks', '-t', help='任务JSON文件')
    parser.add_argument('--input', '-i', help='综合输入YAML文件')
    parser.add_argument('--output', '-o', help='输出JSON文件')
    parser.add_argument('--ics', help='导出ICS日历文件')
    parser.add_argument('--week-start', help='周开始日期 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # 确定周开始日期
    if args.week_start:
        week_start = datetime.strptime(args.week_start, '%Y-%m-%d')
    else:
        # 默认从本周一开始
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 加载数据
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            plan = yaml.safe_load(f)
        
        fixed_events = []
        for c in plan.get("courses", []):
            day_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, 
                       "周五": 4, "周六": 5, "周日": 6}
            fixed_events.append(Course(
                name=c["name"],
                day=day_map.get(c.get("day", "周一"), 0),
                start_time=c.get("start_time", "08:00"),
                end_time=c.get("end_time", "09:40"),
                location=c.get("location"),
                is_fixed=True
            ))
        
        tasks = []
        for t in plan.get("tasks", []):
            deadline = None
            if t.get("deadline"):
                try:
                    deadline = datetime.fromisoformat(t["deadline"])
                except:
                    pass
            tasks.append(Task(
                name=t["name"],
                subject=t.get("subject", "通用"),
                estimated_duration=t.get("estimated_duration", 60),
                deadline=deadline,
                importance=t.get("importance", 5),
                difficulty=t.get("difficulty", "medium")
            ))
        
        prefs_data = plan.get("preferences", {})
        preferences = Preferences(
            productive_hours=prefs_data.get("productive_hours", ["19:00-22:00"]),
            day_start=prefs_data.get("day_start", "08:00"),
            day_end=prefs_data.get("day_end", "23:00"),
            break_duration=prefs_data.get("break_duration", 15),
            min_slot_size=prefs_data.get("min_slot_size", 30),
            prefer_morning=prefs_data.get("prefer_morning", False),
            prefer_evening=prefs_data.get("prefer_evening", True),
            max_continuous_study=prefs_data.get("max_continuous_study", 120)
        )
    else:
        fixed_events = load_courses_from_json(args.courses) if args.courses else []
        tasks = load_tasks_from_json(args.tasks) if args.tasks else []
        preferences = Preferences()
    
    # 生成排程
    scheduler = SmartScheduler(preferences)
    schedule = scheduler.generate_schedule(fixed_events, tasks, week_start)
    
    # 打印
    scheduler.print_schedule(week_start)
    
    # 检查冲突
    conflicts = scheduler.check_conflicts()
    if conflicts:
        print("\n⚠️ 发现冲突:")
        for c in conflicts:
            print(f"  - {c['event1']} 与 {c['event2']} 重叠 {c['overlap']:.0f} 分钟")
    else:
        print("\n✅ 无冲突")
    
    # 导出
    if args.output:
        data = {
            "week_start": week_start.isoformat(),
            "events": [e.to_dict() for e in schedule if e.type != "break"],
            "total_events": len([e for e in schedule if e.type != "break"]),
            "total_study_hours": sum(
                (e.end - e.start).total_seconds() / 3600 
                for e in schedule if e.type == "study"
            )
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n已导出到: {args.output}")
    
    if args.ics:
        try:
            scheduler.generate_ics(args.ics)
        except ImportError:
            print("\n⚠️ 请安装 icalendar: pip install icalendar")


if __name__ == "__main__":
    main()
