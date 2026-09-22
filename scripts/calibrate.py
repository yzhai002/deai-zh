#!/usr/bin/env python3
"""校准中文 AI 高频词表：比较 AI 语料与真人语料的词频。

用法：
  python3 scripts/calibrate.py

读取 calibration/ai/*.txt 与 calibration/human/*.txt，对候选词计算
两侧每万字频率与比值，并对 AI 侧做 n-gram 差异分析，寻找词表漏掉的
候选词。输出写到 calibration/report.md。语料小，比值只作排序参考，
改动词表前先看每万字频率的绝对值。
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AI_DIR = ROOT / "calibration" / "ai"
HUMAN_DIR = ROOT / "calibration" / "human"
REPORT = ROOT / "calibration" / "report.md"

# 候选词：SKILL.md §12/§13/§16 的观察名单加上待验证的常见疑点。
CANDIDATES = [
    "赋能", "助力", "加持", "深耕", "打造", "致力于", "旨在", "彰显",
    "诠释", "拥抱", "引领", "勾勒", "展望", "画卷", "底色", "淋漓尽致",
    "可圈可点", "值得一提的是", "值得注意的是", "不难发现", "综上所述",
    "众所周知", "总而言之", "归根结底", "从本质上讲", "说到底", "深入探讨",
    "深入浅出", "进一步", "充分", "有效", "重要意义", "标志着", "注入",
    "新动能", "新篇章", "奠定", "坚实基础", "前景广阔", "未来可期",
    "蓬勃发展", "迈上新台阶", "焕发", "新的生机", "强劲", "引擎", "红利",
    "缩影", "见证", "绽放", "缩影", "战略要地", "高质量发展", "深入推进",
    "不可替代", "令人瞩目", "备受瞩目", "周密", "关心", "温馨", "深深",
]

# 排除通用功能词与虚词，避免 n-gram 差异列表全是噪音。
STOP_CHARS = set("的了着是在和与对为把将向从被以及等各就也都还又并或者但而因此所")


def corpus_text(directory: Path) -> str:
    parts = [p.read_text(encoding="utf-8") for p in sorted(directory.glob("*.txt"))]
    return "".join(parts)


def per_10k(count: int, total_chars: int) -> float:
    return count * 10000 / total_chars if total_chars else 0.0


def ngram_report(ai: str, human: str, sizes: tuple[int, ...] = (3, 4)) -> list[tuple[str, int]]:
    """AI 语料中反复出现、人类语料中一次没出现的 n-gram。"""
    findings: list[tuple[str, int]] = []
    for n in sizes:
        ai_counts = Counter(ai[i : i + n] for i in range(len(ai) - n + 1))
        for gram, count in ai_counts.items():
            if count < 3:
                continue
            if gram in human:
                continue
            if any(ch in STOP_CHARS or not "\u4e00" <= ch <= "\u9fff" for ch in gram):
                continue
            findings.append((gram, count))
    # 同一短语的长短 n-gram 重复出现时，只留长的。
    findings.sort(key=lambda item: (-item[1], -len(item[0])))
    kept: list[tuple[str, int]] = []
    for gram, count in findings:
        if any(gram in kept_gram for kept_gram, _ in kept):
            continue
        kept.append((gram, count))
    return kept[:40]


def main() -> None:
    ai = corpus_text(AI_DIR)
    human = corpus_text(HUMAN_DIR)
    lines = [
        "# 词表校准报告",
        "",
        f"- AI 语料：{len(list(AI_DIR.glob('*.txt')))} 篇，{len(ai)} 字",
        f"- 人类语料：{len(list(HUMAN_DIR.glob('*.txt')))} 篇，{len(human)} 字（澎湃新闻、中国新闻网，2026-09-22 抓取）",
        "- 语料规模小：比值用于排序，绝对频率和出现次数都要看；两侧都为零的词没有信号。",
        "",
        "## 候选词频率",
        "",
        "| 词 | AI 次数 | AI /万字 | 人类次数 | 人类 /万字 | 比值 |",
        "|---|---|---|---|---|---|",
    ]
    rows = []
    for word in sorted(set(CANDIDATES)):
        ai_count = ai.count(word)
        human_count = human.count(word)
        ai_freq = per_10k(ai_count, len(ai))
        human_freq = per_10k(human_count, len(human))
        ratio = (ai_freq + 0.5) / (human_freq + 0.5)
        rows.append((ratio, word, ai_count, ai_freq, human_count, human_freq))
    rows.sort(reverse=True)
    for ratio, word, ai_count, ai_freq, human_count, human_freq in rows:
        lines.append(
            f"| {word} | {ai_count} | {ai_freq:.1f} | {human_count} | {human_freq:.1f} | {ratio:.1f} |"
        )

    lines += ["", "## AI 侧独有 n-gram（出现 ≥3 次且人类语料为零）", "", "| n-gram | AI 次数 |", "|---|---|"]
    for gram, count in ngram_report(ai, human):
        lines.append(f"| {gram} | {count} |")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"报告已写入 {REPORT.relative_to(ROOT)}")
    print(f"AI {len(ai)} 字 / 人类 {len(human)} 字")
    top = rows[:15]
    print("比值最高的 15 个：")
    for ratio, word, ai_count, _, human_count, _ in top:
        print(f"  {word}: AI {ai_count} 次 / 人类 {human_count} 次，比值 {ratio:.1f}")


if __name__ == "__main__":
    main()
