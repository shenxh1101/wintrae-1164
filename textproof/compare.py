from __future__ import annotations

from textproof.models import CompareResult, Issue, Severity
from textproof.scanner import scan_directory
from textproof.checker import Checker
from textproof.rules import Rules
from pathlib import Path


def compare(
    root: str | Path,
    rules: Rules,
    pattern: str = "*.md",
    ignore_files: list[str] | None = None,
) -> CompareResult:
    root = Path(root)
    scan = scan_directory(root, pattern=pattern, ignore_files=ignore_files)
    checker = Checker(rules)
    result = CompareResult()

    seen: set[str] = set()
    for f in scan.files:
        if f not in seen:
            result.issues.extend(checker.check_file(f, root))
            seen.add(f)

    for _group, files in scan.groups.items():
        if len(files) > 1:
            result.issues.extend(checker.check_group(files, root))

    return result


def diff_summary(result: CompareResult) -> str:
    lines: list[str] = []
    by_sev = result.by_severity()

    lines.append("═══ 差异摘要 ═══")
    lines.append(f"  问题总数：{len(result.issues)}")
    for sev in (Severity.ERROR, Severity.WARNING, Severity.INFO):
        count = len(by_sev[sev])
        if count:
            label = {"error": "错误", "warning": "警告", "info": "提示"}[sev.value]
            lines.append(f"  {label}：{count}")

    lines.append("")
    for sev in (Severity.ERROR, Severity.WARNING, Severity.INFO):
        issues = by_sev[sev]
        if not issues:
            continue
        label = {"error": "错误", "warning": "警告", "info": "提示"}[sev.value]
        lines.append(f"── {label} ──")
        for i in issues:
            loc = f"{i.file}:{i.line}" if i.line else i.file
            lines.append(f"  [{i.kind.value}] {loc}  {i.message}")
        lines.append("")

    return "\n".join(lines)
