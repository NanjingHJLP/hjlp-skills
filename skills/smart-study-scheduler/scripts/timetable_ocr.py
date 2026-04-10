#!/usr/bin/env python3
"""
课表图片OCR识别工具

支持从课表截图中提取结构化课程信息。
依赖：paddleocr, pillow, numpy

用法：
    python timetable_ocr.py --input timetable.png --output courses.json
    python timetable_ocr.py --input timetable.png --format csv
"""

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

try:
    from paddleocr import PaddleOCR
    from PIL import Image
    import numpy as np
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    print("警告：PaddleOCR 未安装，将使用模拟模式")


@dataclass
class Course:
    """课程信息"""
    name: str
    day: str
    start_time: str
    end_time: str
    location: Optional[str] = None
    teacher: Optional[str] = None
    type: str = "必修"

    def to_dict(self):
        return asdict(self)


@dataclass
class Cell:
    """表格单元格"""
    row: int
    col: int
    content: str
    x: int = 0
    y: int = 0


class TimetableOCR:
    """课表OCR识别器"""
    
    DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self.ocr = None
        if PADDLE_AVAILABLE:
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang='ch',
                use_gpu=use_gpu,
                show_log=False
            )
    
    def recognize(self, image_path: str) -> List[Course]:
        """识别课表图片
        
        Args:
            image_path: 课表图片路径
            
        Returns:
            课程列表
        """
        if not PADDLE_AVAILABLE:
            return self._mock_recognize(image_path)
        
        # 图像预处理
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # OCR识别
        result = self.ocr.ocr(img_array, cls=True)
        
        # 提取文本和位置
        texts = []
        for line in result[0]:
            if line:
                box, (text, score) = line
                x = sum(p[0] for p in box) / 4
                y = sum(p[1] for p in box) / 4
                texts.append({
                    "text": text,
                    "x": int(x),
                    "y": int(y),
                    "score": score
                })
        
        # 解析表格结构
        cells = self._detect_table_structure(texts)
        
        # 提取课程
        courses = self._parse_courses(cells)
        
        return courses
    
    def _detect_table_structure(self, texts: List[dict]) -> List[Cell]:
        """检测表格结构"""
        # 按Y坐标分组（同一行）
        y_groups = {}
        for text in texts:
            y = text["y"] // 30  # 30像素容差
            if y not in y_groups:
                y_groups[y] = []
            y_groups[y].append(text)
        
        cells = []
        row_idx = 0
        for y in sorted(y_groups.keys()):
            row_texts = sorted(y_groups[y], key=lambda x: x["x"])
            for col_idx, text in enumerate(row_texts):
                cells.append(Cell(
                    row=row_idx,
                    col=col_idx,
                    content=text["text"],
                    x=text["x"],
                    y=text["y"]
                ))
            row_idx += 1
        
        return cells
    
    def _parse_courses(self, cells: List[Cell]) -> List[Course]:
        """解析课程信息"""
        courses = []
        
        # 识别表头（时间列、星期行）
        header_row = [c for c in cells if c.row == 0]
        time_col = [c for c in cells if c.col == 0]
        
        # 提取星期映射
        day_map = {}
        for cell in header_row:
            for i, day in enumerate(self.DAYS):
                if day in cell.content or cell.content in ["一", "二", "三", "四", "五", "六", "日"]:
                    day_map[cell.col] = self.DAYS[i]
        
        # 提取时间段
        time_slots = {}
        for cell in time_col:
            time_match = re.search(r'(\d{1,2}):?(\d{2})?[-~](\d{1,2}):?(\d{2})?', cell.content)
            if time_match:
                time_slots[cell.row] = cell.content
        
        # 提取课程单元格
        for cell in cells:
            if cell.row == 0 or cell.col == 0:
                continue
            
            content = cell.content.strip()
            if not content or len(content) < 2:
                continue
            
            # 判断是否为课程（非时间、非星期）
            if self._is_course_content(content):
                day = day_map.get(cell.col, "未知")
                time_str = time_slots.get(cell.row, "08:00-10:00")
                start_time, end_time = self._parse_time_range(time_str)
                
                # 解析课程详细信息
                course_info = self._parse_course_info(content)
                
                courses.append(Course(
                    name=course_info.get("name", content),
                    day=day,
                    start_time=start_time,
                    end_time=end_time,
                    location=course_info.get("location"),
                    teacher=course_info.get("teacher"),
                    type=course_info.get("type", "必修")
                ))
        
        return courses
    
    def _is_course_content(self, content: str) -> bool:
        """判断内容是否为课程信息"""
        # 排除纯时间、纯数字
        if re.match(r'^\d{1,2}:?\d{2}$', content):
            return False
        if re.match(r'^\d+$', content):
            return False
        # 排除星期字样
        if content in self.DAYS or content in ["一", "二", "三", "四", "五", "六", "日"]:
            return False
        return True
    
    def _parse_time_range(self, time_str: str) -> tuple:
        """解析时间范围"""
        match = re.search(r'(\d{1,2}):?(\d{2})?[-~](\d{1,2}):?(\d{2})?', time_str)
        if match:
            h1, m1, h2, m2 = match.groups()
            m1 = m1 or "00"
            m2 = m2 or "00"
            return f"{h1.zfill(2)}:{m1}", f"{h2.zfill(2)}:{m2}"
        return "08:00", "09:40"
    
    def _parse_course_info(self, content: str) -> dict:
        """解析课程详细信息"""
        info = {"name": content}
        
        # 提取教室信息（通常包含数字）
        location_match = re.search(r'([\u4e00-\u9fa5]+\d+[\u4e00-\u9fa5]*\d*)', content)
        if location_match:
            info["location"] = location_match.group(1)
        
        # 提取教师姓名
        teacher_match = re.search(r'([\u4e00-\u9fa5]{2,4})(?:老师|教授)?', content)
        if teacher_match and len(teacher_match.group(1)) <= 4:
            info["teacher"] = teacher_match.group(1)
        
        # 判断课程类型
        if any(kw in content for kw in ["选修", "任选", "公选"]):
            info["type"] = "选修"
        elif any(kw in content for kw in ["实验", "上机", "实践"]):
            info["type"] = "实验"
        
        return info
    
    def _mock_recognize(self, image_path: str) -> List[Course]:
        """模拟识别（用于测试）"""
        return [
            Course("高等数学", "周一", "08:00", "09:40", "3教201", type="必修"),
            Course("大学英语", "周二", "14:00", "15:40", "5教102", type="必修"),
            Course("计算机基础", "周三", "10:00", "11:40", "机房A", type="实验"),
        ]


def export_to_json(courses: List[Course], output_path: str):
    """导出为JSON"""
    data = {
        "courses": [c.to_dict() for c in courses],
        "total": len(courses)
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已导出到: {output_path}")


def export_to_csv(courses: List[Course], output_path: str):
    """导出为CSV"""
    import csv
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["课程名称", "星期", "开始时间", "结束时间", "地点", "教师", "类型"])
        for c in courses:
            writer.writerow([c.name, c.day, c.start_time, c.end_time, 
                           c.location or "", c.teacher or "", c.type])
    print(f"已导出到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='课表图片OCR识别')
    parser.add_argument('--input', '-i', required=True, help='输入图片路径')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--format', '-f', choices=['json', 'csv'], default='json',
                       help='输出格式')
    parser.add_argument('--gpu', action='store_true', help='使用GPU加速')
    
    args = parser.parse_args()
    
    # 识别
    ocr = TimetableOCR(use_gpu=args.gpu)
    courses = ocr.recognize(args.input)
    
    print(f"识别到 {len(courses)} 门课程:")
    for c in courses:
        print(f"  - {c.day} {c.start_time}-{c.end_time}: {c.name} @ {c.location or '未知'}")
    
    # 导出
    if args.output:
        if args.format == 'json':
            export_to_json(courses, args.output)
        else:
            export_to_csv(courses, args.output)


if __name__ == "__main__":
    main()
