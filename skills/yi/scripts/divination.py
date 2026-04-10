#!/usr/bin/env python3
"""
周易占卜起卦工具
支持：铜钱起卦（coin）、数字起卦（number）、时间起卦（time）
输出：JSON（stdout），错误信息输出到 stderr
仅依赖标准库，Python 3.8+
"""

import json
import random
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from hexagram_data import HEXAGRAMS, BAGUA
except ImportError:
    HEXAGRAMS = {}
    BAGUA = {}

TRIGRAMS = {
    1: {"name": "乾", "symbol": "☰", "nature": "天", "bits": (1, 1, 1)},
    2: {"name": "兑", "symbol": "☱", "nature": "泽", "bits": (1, 1, 0)},
    3: {"name": "离", "symbol": "☲", "nature": "火", "bits": (1, 0, 1)},
    4: {"name": "震", "symbol": "☳", "nature": "雷", "bits": (1, 0, 0)},
    5: {"name": "巽", "symbol": "☴", "nature": "风", "bits": (0, 1, 1)},
    6: {"name": "坎", "symbol": "☵", "nature": "水", "bits": (0, 1, 0)},
    7: {"name": "艮", "symbol": "☶", "nature": "山", "bits": (0, 0, 1)},
    8: {"name": "坤", "symbol": "☷", "nature": "地", "bits": (0, 0, 0)},
}

BITS_TO_TRIGRAM = {v["bits"]: k for k, v in TRIGRAMS.items()}

HEXAGRAM_MAP = {
    (1, 1): (1, "乾为天"),   (8, 8): (2, "坤为地"),
    (6, 4): (3, "水雷屯"),   (7, 6): (4, "山水蒙"),
    (6, 1): (5, "水天需"),   (1, 6): (6, "天水讼"),
    (8, 6): (7, "地水师"),   (6, 8): (8, "水地比"),
    (5, 1): (9, "风天小畜"), (1, 2): (10, "天泽履"),
    (8, 1): (11, "地天泰"),  (1, 8): (12, "天地否"),
    (1, 3): (13, "天火同人"),(3, 1): (14, "火天大有"),
    (8, 7): (15, "地山谦"),  (4, 8): (16, "雷地豫"),
    (2, 4): (17, "泽雷随"),  (7, 5): (18, "山风蛊"),
    (8, 2): (19, "地泽临"),  (5, 8): (20, "风地观"),
    (3, 4): (21, "火雷噬嗑"),(7, 3): (22, "山火贲"),
    (7, 8): (23, "山地剥"),  (8, 4): (24, "地雷复"),
    (1, 4): (25, "天雷无妄"),(7, 1): (26, "山天大畜"),
    (7, 4): (27, "山雷颐"),  (2, 5): (28, "泽风大过"),
    (6, 6): (29, "坎为水"),  (3, 3): (30, "离为火"),
    (2, 7): (31, "泽山咸"),  (4, 5): (32, "雷风恒"),
    (1, 7): (33, "天山遁"),  (4, 1): (34, "雷天大壮"),
    (3, 8): (35, "火地晋"),  (8, 3): (36, "地火明夷"),
    (5, 3): (37, "风火家人"),(3, 2): (38, "火泽睽"),
    (6, 7): (39, "水山蹇"),  (4, 6): (40, "雷水解"),
    (7, 2): (41, "山泽损"),  (5, 4): (42, "风雷益"),
    (2, 1): (43, "泽天夬"),  (1, 5): (44, "天风姤"),
    (2, 8): (45, "泽地萃"),  (8, 5): (46, "地风升"),
    (2, 6): (47, "泽水困"),  (6, 5): (48, "水风井"),
    (2, 3): (49, "泽火革"),  (3, 5): (50, "火风鼎"),
    (4, 4): (51, "震为雷"),  (7, 7): (52, "艮为山"),
    (5, 7): (53, "风山渐"),  (4, 2): (54, "雷泽归妹"),
    (4, 3): (55, "雷火丰"),  (3, 7): (56, "火山旅"),
    (5, 5): (57, "巽为风"),  (2, 2): (58, "兑为泽"),
    (5, 6): (59, "风水涣"),  (6, 2): (60, "水泽节"),
    (5, 2): (61, "风泽中孚"),(4, 7): (62, "雷山小过"),
    (6, 3): (63, "水火既济"),(3, 6): (64, "火水未济"),
}


def _line_to_bit(value: int) -> int:
    """爻值转阴阳位：7/9 为阳(1)，6/8 为阴(0)"""
    return 1 if value in (7, 9) else 0


def _lines_to_trigram(lines):
    """三个爻值转八卦序号"""
    bits = tuple(_line_to_bit(v) for v in lines)
    return BITS_TO_TRIGRAM[bits]


def _changed_value(value: int) -> int:
    """变爻后的爻值：老阴(6)→少阳(7)，老阳(9)→少阴(8)"""
    if value == 6:
        return 7
    if value == 9:
        return 8
    return value


def _build_trigram_info(number: int) -> dict:
    t = TRIGRAMS[number]
    return {
        "number": number,
        "name": t["name"],
        "symbol": t["symbol"],
        "nature": t["nature"],
    }


def _build_hexagram(upper: int, lower: int) -> dict:
    number, full_name = HEXAGRAM_MAP[(upper, lower)]
    data = HEXAGRAMS.get(number, {})
    return {
        "number": number,
        "name": full_name,
        "short_name": data.get("name", full_name.replace("为", "")),
        "upper": _build_trigram_info(upper),
        "lower": _build_trigram_info(lower),
    }


def _interpret(hexagram_number: int, changing_yao: list) -> dict:
    """根据卦号和变爻生成解读信息"""
    data = HEXAGRAMS.get(hexagram_number, {})
    result = {
        "summary": data.get("meaning", "可结合卦辞、象辞与现实问题综合判断。"),
    }
    for field in ("guaci", "xiang", "tuan"):
        if data.get(field):
            result[field] = data[field]

    if changing_yao and data.get("yaoci"):
        yao_texts = []
        for idx in changing_yao:
            if 1 <= idx <= len(data["yaoci"]):
                yao_texts.append({"yao": idx, "text": data["yaoci"][idx - 1]})
        if yao_texts:
            result["changing_yao_text"] = yao_texts

    if data.get("yong"):
        result["yong"] = data["yong"]

    return result


def _analyze_lines(lines):
    """六爻拆为上下卦序号"""
    lower = _lines_to_trigram(lines[:3])
    upper = _lines_to_trigram(lines[3:])
    return upper, lower


def _coin_toss() -> tuple:
    """模拟一次三枚铜钱投掷，返回 (爻值, 符号, 是否变爻)"""
    total = sum(random.choice([2, 3]) for _ in range(3))
    return {
        6: (6, "⚋", True, "老阴"),
        7: (7, "⚊", False, "少阳"),
        8: (8, "⚋", False, "少阴"),
        9: (9, "⚊", True, "老阳"),
    }[total]


def coin_divination() -> dict:
    """铜钱起卦"""
    lines = []
    details = []
    changing_yao = []

    for idx in range(1, 7):
        value, symbol, changing, label = _coin_toss()
        lines.append(value)
        details.append({
            "yao": idx,
            "value": value,
            "symbol": symbol,
            "changing": changing,
            "label": label,
        })
        if changing:
            changing_yao.append(idx)

    upper, lower = _analyze_lines(lines)
    changed = [_changed_value(v) for v in lines]
    changed_upper, changed_lower = _analyze_lines(changed)
    hex_number = HEXAGRAM_MAP[(upper, lower)][0]

    result = {
        "method": "coin",
        "method_zh": "铜钱起卦",
        "lines": details,
        "changing_yao": changing_yao,
        "changing_yao_count": len(changing_yao),
        "hexagram": _build_hexagram(upper, lower),
        "interpretation": _interpret(hex_number, changing_yao),
    }

    if changing_yao:
        result["changed_hexagram"] = _build_hexagram(changed_upper, changed_lower)

    return result


def number_divination(num1: int, num2: int) -> dict:
    """数字起卦"""
    upper = num1 % 8 or 8
    lower = num2 % 8 or 8
    changing_yao_pos = (num1 + num2) % 6 or 6
    changing_yao = [changing_yao_pos]
    hex_number = HEXAGRAM_MAP[(upper, lower)][0]

    return {
        "method": "number",
        "method_zh": "数字起卦",
        "input": {"num1": num1, "num2": num2},
        "calculation": {
            "upper": f"{num1} % 8 = {upper}（{TRIGRAMS[upper]['name']}）",
            "lower": f"{num2} % 8 = {lower}（{TRIGRAMS[lower]['name']}）",
            "changing": f"({num1}+{num2}) % 6 = {changing_yao_pos}",
        },
        "changing_yao": changing_yao,
        "changing_yao_count": 1,
        "hexagram": _build_hexagram(upper, lower),
        "interpretation": _interpret(hex_number, changing_yao),
    }


def time_divination(now: datetime = None) -> dict:
    """时间起卦"""
    now = now or datetime.now()
    y, m, d, h, mi = now.year, now.month, now.day, now.hour, now.minute

    upper = (y + m + d) % 8 or 8
    lower = (y + m + d + h) % 8 or 8
    changing_yao_pos = (y + m + d + h + mi) % 6 or 6
    changing_yao = [changing_yao_pos]
    hex_number = HEXAGRAM_MAP[(upper, lower)][0]

    return {
        "method": "time",
        "method_zh": "时间起卦",
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "calculation": {
            "upper": f"({y}+{m}+{d}) % 8 = {upper}（{TRIGRAMS[upper]['name']}）",
            "lower": f"({y}+{m}+{d}+{h}) % 8 = {lower}（{TRIGRAMS[lower]['name']}）",
            "changing": f"({y}+{m}+{d}+{h}+{mi}) % 6 = {changing_yao_pos}",
        },
        "changing_yao": changing_yao,
        "changing_yao_count": 1,
        "hexagram": _build_hexagram(upper, lower),
        "interpretation": _interpret(hex_number, changing_yao),
    }


def _usage():
    print(
        "周易占卜起卦工具\n"
        "\n"
        "用法（必须用 sys.executable 启动，禁止硬编码 python/python3）：\n"
        "  divination.py coin              铜钱起卦\n"
        "  divination.py number <n1> <n2>  数字起卦（两个整数）\n"
        "  divination.py time              时间起卦（当前时间）\n",
        file=sys.stderr,
    )


def main():
    if len(sys.argv) < 2:
        _usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    try:
        if command == "coin":
            result = coin_divination()
        elif command == "number":
            if len(sys.argv) != 4:
                print("错误：数字起卦需要两个整数参数", file=sys.stderr)
                _usage()
                sys.exit(1)
            try:
                num1, num2 = int(sys.argv[2]), int(sys.argv[3])
            except ValueError:
                print(f"错误：参数必须是整数，收到 '{sys.argv[2]}' 和 '{sys.argv[3]}'", file=sys.stderr)
                sys.exit(1)
            result = number_divination(num1, num2)
        elif command == "time":
            result = time_divination()
        else:
            print(f"错误：未知命令 '{command}'", file=sys.stderr)
            _usage()
            sys.exit(1)
    except KeyError as e:
        print(f"错误：卦象数据查找失败 — {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"错误：起卦过程异常 — {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
