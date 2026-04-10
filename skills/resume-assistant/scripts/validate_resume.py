#!/usr/bin/env python3
"""
简历验证脚本 - 检查简历内容完整性
用法: py validate_resume.py <resume.md>
"""

import sys
import re
from pathlib import Path

SECTIONS = {
    "contact": {
        "email": "邮箱",
        "phone": "电话",
    },
    "summary": {
        "exists": "个人简介",
        "length": "简介长度 (50-200字)",
    },
    "experience": {
        "exists": "工作经历",
        "has_numbers": "量化数据",
    },
    "skills": {
        "exists": "技能列表",
    },
}


def validate_resume(content: str) -> dict:
    """验证简历内容，返回通过/失败/警告列表和分数"""
    results = {"passed": [], "failed": [], "warnings": [], "score": 0}

    # --- 联系信息 ---
    if re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', content):
        results["passed"].append(f"✓ {SECTIONS['contact']['email']}")
    else:
        results["failed"].append(f"✗ 缺少{SECTIONS['contact']['email']}")

    if re.search(r'1[3-9]\d[- ]?\d{4}[- ]?\d{4}', content):
        results["passed"].append(f"✓ {SECTIONS['contact']['phone']}")
    else:
        results["warnings"].append("⚠ 未检测到手机号")

    # --- 个人简介 ---
    summary_match = re.search(
        r'(?:简介|summary|about|个人简介).*?\n(.+?)(?=\n##|\n---|\Z)',
        content, re.DOTALL | re.IGNORECASE,
    )
    if summary_match:
        results["passed"].append(f"✓ {SECTIONS['summary']['exists']}")
        summary_len = len(summary_match.group(1).strip())
        if 50 <= summary_len <= 500:
            results["passed"].append(f"✓ {SECTIONS['summary']['length']}")
        else:
            results["warnings"].append("⚠ 简介长度建议 50-200 字")
    else:
        results["failed"].append(f"✗ 缺少{SECTIONS['summary']['exists']}")

    # --- 工作经历 ---
    has_exp = re.search(r'(工作经历|experience|工作|work)', content, re.IGNORECASE)
    if has_exp:
        results["passed"].append(f"✓ {SECTIONS['experience']['exists']}")
    else:
        results["failed"].append(f"✗ 缺少{SECTIONS['experience']['exists']}")

    if re.search(r'\d+[%万+]|\d{2,}', content):
        results["passed"].append(f"✓ {SECTIONS['experience']['has_numbers']}")
    else:
        results["warnings"].append("⚠ 建议添加量化数据 (如: 提升 30% 效率)")

    # --- 技能 ---
    has_skills = re.search(r'(技能|skills|专业技能)', content, re.IGNORECASE)
    if has_skills:
        results["passed"].append(f"✓ {SECTIONS['skills']['exists']}")
    else:
        results["failed"].append(f"✗ 缺少{SECTIONS['skills']['exists']}")

    # --- 计算分数 ---
    passed = len(results["passed"])
    failed = len(results["failed"])
    if passed + failed > 0:
        results["score"] = int(passed / (passed + failed) * 100)

    return results


def print_results(results: dict):
    """打印验证结果"""
    print("\n" + "=" * 50)
    print("简历验证报告")
    print("=" * 50)

    print(f"\n📊 基础分数: {results['score']}/100")
    print(f"✓ 通过: {len(results['passed'])} 项")
    print(f"✗ 失败: {len(results['failed'])} 项")
    print(f"⚠ 警告: {len(results['warnings'])} 项")

    if results["failed"]:
        print("\n❌ 必须修复:")
        for item in results["failed"]:
            print(f"   {item}")

    if results["warnings"]:
        print("\n⚠️ 建议优化:")
        for item in results["warnings"]:
            print(f"   {item}")

    if results["passed"]:
        print("\n✅ 已完善:")
        for item in results["passed"]:
            print(f"   {item}")

    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: py validate_resume.py <resume.md>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"错误: 文件不存在: {input_path}")
        sys.exit(1)

    content = input_path.read_text(encoding="utf-8")
    results = validate_resume(content)
    print_results(results)
