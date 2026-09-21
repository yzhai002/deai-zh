#!/usr/bin/env python3
"""检查 deai-zh 的包文件，无外部依赖。"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read_package_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"无法读取 {path.relative_to(ROOT)}：{error}")


SKILL_PATH = ROOT / "SKILL.md"
SKILL = read_package_file(SKILL_PATH)
README = read_package_file(ROOT / "README.md")
try:
    PLUGIN = json.loads(read_package_file(ROOT / ".claude-plugin" / "plugin.json"))
except json.JSONDecodeError as error:
    raise SystemExit(f"修复 .claude-plugin/plugin.json 的 JSON：{error}")


def require_match(match: re.Match[str] | None, message: str) -> re.Match[str]:
    if match is None:
        raise SystemExit(message)
    return match


yaml_metadata = require_match(
    re.match(r"\A---\n(.*?)\n---\n", SKILL, re.DOTALL),
    "SKILL.md 必须以 YAML 元数据开头",
).group(1)

for unsupported_field in ("version:", "compatibility:", "allowed-tools:"):
    if re.search(rf"(?m)^{re.escape(unsupported_field)}", yaml_metadata):
        raise SystemExit(f"删除不支持的 YAML 字段：{unsupported_field[:-1]}")

skill_version = require_match(
    re.search(r'(?m)^\s+version:\s*["\']?([0-9]+\.[0-9]+\.[0-9]+)["\']?\s*$', yaml_metadata),
    "在 SKILL.md 的 metadata.version 写三段版本号",
).group(1)
readme_version = require_match(
    re.search(r"(?m)^- \*\*([0-9]+\.[0-9]+\.[0-9]+)\*\*", README),
    "在 README.md 加版本条目",
).group(1)

package_versions = {skill_version, readme_version, str(PLUGIN.get("version", ""))}
if len(package_versions) != 1:
    raise SystemExit(
        f"所有文件用同一个包版本号：{sorted(package_versions)}"
    )

skill_files = {path.relative_to(ROOT) for path in ROOT.rglob("SKILL.md")}
if SKILL_PATH.is_symlink() or skill_files != {Path("SKILL.md")}:
    raise SystemExit("仓库根目录只保留一个普通 SKILL.md")
if PLUGIN.get("skills") != ["./"]:
    raise SystemExit("插件技能加载指向仓库根目录")

pattern_numbers = [
    int(number)
    for number in re.findall(r"(?m)^### ([0-9]+)\. ", SKILL)
]
pattern_count = len(pattern_numbers)
if pattern_count == 0 or pattern_numbers != list(range(1, pattern_count + 1)):
    raise SystemExit(f"SKILL.md 模式从 1 连续编号：{pattern_numbers}")

readme_numbers = [
    int(number) for number in re.findall(r"(?m)^\| ([0-9]+) \|", README)
]
if sorted(readme_numbers) != pattern_numbers:
    raise SystemExit(
        f"README 表格把 1 到 {pattern_count} 每个模式各列一行：{sorted(readme_numbers)}"
    )
if f"## {pattern_count} 个模式" not in README:
    raise SystemExit(f"README 模式一节的标题写成 'The {pattern_count} 个模式'")

if len(SKILL.splitlines()) > 400:
    raise SystemExit("SKILL.md 保持在 400 行以内")

print(f"deai-zh 包 v{skill_version} 有效")
