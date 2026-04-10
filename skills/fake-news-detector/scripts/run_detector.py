#!/usr/bin/env python3
"""
假新闻检测脚本。从 stdin 或 --text 读入待检测文本，输出约定 JSON。
开箱可用：仅用标准库，无需配置。输出为「由 Agent 按 Skill 流程查证」的占位结果；
若需使用本地 FactChecker，可配置 FAKE_NEWS_DETECTOR_DIR 等环境变量（见 SKILL.md）。
"""
import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Fake news detector (zero-config, Agent follows Skill flow).")
    parser.add_argument("--text", type=str, help="Text to analyze. If omitted, read from stdin.")
    args = parser.parse_args()

    if args.text is not None:
        text = args.text
    else:
        text = sys.stdin.read()

    text = (text or "").strip()
    if not text:
        out = {
            "label": "unknown",
            "score": 0.5,
            "explanation": "输入为空，无法检测。",
            "source_urls": [],
        }
    else:
        out = {
            "label": "unknown",
            "score": 0.5,
            "explanation": "由 Agent 按 Skill 流程执行查证并填写输出格式（提取声明、查证来源、对照权威列表）。",
            "source_urls": [],
        }

    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
