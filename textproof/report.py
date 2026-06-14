from __future__ import annotations

import json
from pathlib import Path

from textproof.models import CompareResult, Severity


def generate_report(
    result: CompareResult,
    output: str | Path | None = None,
    fmt: str = "text",
) -> str:
    if fmt == "json":
        text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    else:
        text = _text_report(result)

    if output:
        Path(output).write_text(text, encoding="utf-8")

    return text


def _text_report(result: CompareResult) -> str:
    lines: list[str] = []
    by_sev = result.by_severity()

    lines.append("╔══════════════════════════════════════╗")
    lines.append("║          校 对 报 告                 ║")
    lines.append("╚══════════════════════════════════════╝")
    lines.append("")

    lines.append(f"问题总数：{len(result.issues)}")
    for sev in (Severity.ERROR, Severity.WARNING, Severity.INFO):
        count = len(by_sev[sev])
        label = {"error": "错误", "warning": "警告", "info": "提示"}[sev.value]
        lines.append(f"  {label}：{count}")
    lines.append("")

    kind_labels = {
        "forbidden_word": "禁用词",
        "terminology": "术语不一致",
        "name_inconsistency": "人名/地名不统一",
        "number_format": "数字格式",
        "date_format": "日期格式",
        "heading_level": "标题层级",
        "duplicate_paragraph": "重复段落",
        "missing_chapter": "缺失章节",
    }

    for sev in (Severity.ERROR, Severity.WARNING, Severity.INFO):
        issues = by_sev[sev]
        if not issues:
            continue
        label = {"error": "错误", "warning": "警告", "info": "提示"}[sev.value]
        lines.append(f"━━ {label} ━━")
        for i in issues:
            loc = f"{i.file}:{i.line}" if i.line else i.file
            kind_label = kind_labels.get(i.kind.value, i.kind.value)
            lines.append(f"  [{kind_label}] {loc}")
            lines.append(f"    {i.message}")
            if i.suggestion:
                lines.append(f"    建议：{i.original} → {i.suggestion}")
            lines.append("")
        lines.append("")

    return "\n".join(lines)
