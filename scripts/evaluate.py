#!/usr/bin/env python3
"""检查一段去AI味改写：脚本看得见的痕迹。

用法：
  python3 scripts/evaluate.py 输入文件 改写文件
  python3 scripts/evaluate.py --all

脚本只查机器指纹、破折号省略号、高频词、均匀句长和丢失的数字，
判断不了意思和声音，所以它是关卡不是评审。WARN 需要人工复核，
FAIL 直接不通过。词表是 SKILL.md §12 的保守子集。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "eval" / "cases"

# 模型指纹（模式 #26）。
FINGERPRINTS: list[tuple[str, str]] = [
    (r"oaicite", "ChatGPT 引用残渣"),
    (r"turn0search[0-9]*", "ChatGPT 搜索残渣"),
    (r"\[cite: ?[0-9]+\]", "Gemini 引用残渣"),
    (r"grok_card", "Grok 残渣"),
    (r"ppl-ai-file-upload", "Perplexity 残渣"),
    (r"utm_source=", "链接里的跟踪参数"),
    (r"[\u200b\u200c\u200d\u2060\ufeff\ufe00-\ufe0f]", "不可见 Unicode 字符"),
]

# §12 词表的保守子集：真人也常用、误报高的词不进脚本。
VOCABULARY = [
    "赋能", "助力", "加持", "深耕", "致力于", "旨在", "彰显", "诠释",
    "勾勒", "画卷", "底色", "淋漓尽致", "可圈可点", "值得一提的是",
    "不难发现", "综上所述", "众所周知", "总而言之", "归根结底",
    "从本质上讲", "说到底", "深入探讨", "深入浅出",
]

# §4、§22 的套话。
PHRASES = [
    "接下来让我们", "话不多说", "废话不多说",
    "希望这对你有帮助", "当然可以！", "还有什么可以帮",
    "请随时告诉我", "如果还有其他问题", "以下是关于",
]

NON_PROSE = re.compile(r"(?m)^\s*(#|>|\||[-*+]|\d+\.)\s")
FENCED = re.compile(r"```.*?```", re.DOTALL)
INLINE = re.compile(r"`[^`\n]*`")
SENTENCE_SPLIT = re.compile(r"[。！？!?]+")
PUNCT = set("，。！？；：、,.!?;:()（）""''\u2014\u2026 ")


def prose(text: str) -> str:
    """只留散文：去掉代码、标题、引用、表格和列表。"""
    text = FENCED.sub(" ", text)
    text = INLINE.sub(" ", text)
    text = "\n".join(
        line for line in text.splitlines() if not NON_PROSE.match(line)
    )
    return text.strip()


def strip_fingerprints(text: str) -> str:
    """先删掉指纹，免得指纹里的数字被当成事实。"""
    for pattern, _ in FINGERPRINTS:
        text = re.sub(pattern, " ", text)
    return text


def check_fingerprints(rewrite: str) -> list[tuple[str, str]]:
    return [
        ("FAIL", f"指纹：{label}")
        for pattern, label in FINGERPRINTS
        if re.search(pattern, rewrite, re.IGNORECASE)
    ]


def check_dashes(rewrite: str) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    plain = prose(rewrite)
    if "\u2014" in plain or "\u2013" in plain:
        findings.append(("FAIL", "破折号：正文里出现 —— 或 –（代码除外）"))
    if "\u2026" in plain:
        findings.append(("FAIL", "省略号：正文里用 …… 当连接（代码除外）"))
    if re.search(r"\S -- \S", plain):
        findings.append(("FAIL", "破折号：双连字符当破折号"))
    return findings


def check_vocabulary(rewrite: str) -> list[tuple[str, str]]:
    plain = prose(rewrite)
    hits = [w for w in VOCABULARY if w in plain]
    hits += [p for p in PHRASES if p in plain]
    if hits:
        return [("FAIL", f"高频词：{', '.join(sorted(set(hits)))}")]
    return []


def check_rhythm(rewrite: str) -> list[tuple[str, str]]:
    """连续四句以上长度几乎相同就算均匀句长（模式 #7）。"""
    findings: list[tuple[str, str]] = []
    for block in re.split(r"\n\s*\n", prose(rewrite)):
        lengths = [
            len([c for c in s if c not in PUNCT])
            for s in SENTENCE_SPLIT.split(block)
            if s.strip()
        ]
        for start in range(len(lengths) - 3):
            run = lengths[start : start + 4]
            mean = sum(run) / len(run)
            if mean == 0:
                continue
            if all(abs(n - mean) <= 0.2 * mean for n in run):
                findings.append(
                    ("FAIL", f"均匀句长：连续 4 句约 {mean:.0f} 字")
                )
                break
    return findings


def check_numbers(source: str, rewrite: str) -> list[tuple[str, str]]:
    source_digits = set(re.findall(r"\d+", strip_fingerprints(prose(source))))
    rewrite_digits = set(re.findall(r"\d+", prose(rewrite)))
    missing = sorted(source_digits - rewrite_digits, key=int)
    if missing:
        return [("WARN", f"输入里的数字在改写中丢失：{', '.join(missing)}")]
    return []


def evaluate(source: str, rewrite: str) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    findings += check_fingerprints(rewrite)
    findings += check_dashes(rewrite)
    findings += check_vocabulary(rewrite)
    findings += check_rhythm(rewrite)
    findings += check_numbers(source, rewrite)
    return findings


def report(label: str, findings: list[tuple[str, str]]) -> bool:
    print(label)
    if not findings:
        print("  PASS")
        return True
    ok = True
    for severity, message in findings:
        print(f"  {severity}: {message}")
        if severity == "FAIL":
            ok = False
    return ok


def main() -> int:
    args = sys.argv[1:]
    if args == ["--all"]:
        case_dirs = sorted(p for p in CASES.iterdir() if p.is_dir()) if CASES.is_dir() else []
        if not case_dirs:
            print(f"{CASES.relative_to(ROOT)} 下没有用例")
            return 1
        ok = True
        for case in case_dirs:
            source_path, rewrite_path = case / "input.md", case / "rewrite.md"
            if not source_path.is_file() or not rewrite_path.is_file():
                print(f"{case.name}: 需要 input.md 和 rewrite.md")
                ok = False
                continue
            findings = evaluate(source_path.read_text(), rewrite_path.read_text())
            ok = report(case.name, findings) and ok
        return 0 if ok else 1
    if len(args) != 2:
        print(__doc__)
        return 2
    source, rewrite = Path(args[0]), Path(args[1])
    findings = evaluate(source.read_text(), rewrite.read_text())
    return 0 if report(f"{source.name} -> {rewrite.name}", findings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
