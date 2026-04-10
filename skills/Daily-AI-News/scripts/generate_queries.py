#!/usr/bin/env python3
"""Generate date-aware search queries for Daily AI News skill.

Usage:
    python generate_queries.py              # daily queries (default)
    python generate_queries.py --mode weekly
    python generate_queries.py --mode research
    python generate_queries.py --mode industry
    python generate_queries.py --mode product
    python generate_queries.py --company OpenAI
    python generate_queries.py --format json
"""

import argparse
import json
from datetime import datetime, timedelta

QUERY_TEMPLATES = {
    "daily": [
        '"AI news today" OR "artificial intelligence breakthrough" after:{yesterday}',
        '"AI research paper" OR "machine learning breakthrough" after:{yesterday}',
        '"AI startup funding" OR "AI company news" after:{week_ago}',
        '"AI product release" OR "new AI tool" after:{yesterday}',
    ],
    "weekly": [
        '"AI news this week" OR "artificial intelligence announcement" after:{week_ago}',
        '"AI research paper" OR "machine learning breakthrough" after:{week_ago}',
        '"AI startup funding" OR "artificial intelligence investment" after:{week_ago}',
        '"open source AI" OR "AI model release" after:{week_ago}',
    ],
    "research": [
        '"AI research paper" OR "machine learning breakthrough" after:{yesterday}',
        'arXiv "cs.AI" OR "cs.LG" paper after:{yesterday}',
        '"AI breakthrough" OR "research advancement" after:{yesterday}',
    ],
    "industry": [
        '"AI startup funding" OR "artificial intelligence investment" after:{week_ago}',
        '"AI company news" OR "OpenAI news" OR "Google AI" after:{yesterday}',
        '"AI acquisition" OR "AI partnership" after:{week_ago}',
    ],
    "product": [
        '"AI product release" OR "new AI tool" after:{yesterday}',
        '"open source AI" OR "AI model release" OR "LLM release" after:{yesterday}',
        '"GPT update" OR "Claude update" OR "Gemini update" after:{yesterday}',
    ],
}

COMPANY_QUERIES = {
    "OpenAI": '"OpenAI announcement" OR "GPT update" OR "ChatGPT news" after:{yesterday}',
    "Google": '"Google AI" OR "Gemini update" OR "DeepMind" after:{yesterday}',
    "Anthropic": '"Anthropic news" OR "Claude update" after:{yesterday}',
    "Meta": '"Meta AI" OR "LLaMA update" after:{yesterday}',
    "Microsoft": '"Microsoft AI" OR "Copilot update" after:{yesterday}',
}


def build_dates():
    today = datetime.now()
    return {
        "today": today.strftime("%Y-%m-%d"),
        "yesterday": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        "week_ago": (today - timedelta(days=7)).strftime("%Y-%m-%d"),
        "current_year": str(today.year),
    }


def render(template: str, dates: dict) -> str:
    result = template
    for key, val in dates.items():
        result = result.replace(f"{{{key}}}", val)
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate AI news search queries")
    parser.add_argument(
        "--mode",
        choices=list(QUERY_TEMPLATES.keys()),
        default="daily",
        help="Query category (default: daily)",
    )
    parser.add_argument("--company", help="Generate company-specific query")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    dates = build_dates()
    queries = []

    if args.company:
        name = args.company
        if name in COMPANY_QUERIES:
            queries.append(render(COMPANY_QUERIES[name], dates))
        else:
            available = ", ".join(COMPANY_QUERIES.keys())
            print(f"Unknown company: {name}. Available: {available}")
            return
    else:
        queries = [render(q, dates) for q in QUERY_TEMPLATES[args.mode]]

    if args.format == "json":
        print(json.dumps({"mode": args.mode, "date": dates["today"], "queries": queries}, ensure_ascii=False, indent=2))
    else:
        print(f"# {args.mode.upper()} queries — {dates['today']}\n")
        for i, q in enumerate(queries, 1):
            print(f"{i}. {q}")


if __name__ == "__main__":
    main()
