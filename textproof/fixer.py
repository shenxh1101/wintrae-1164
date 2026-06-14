from __future__ import annotations

from pathlib import Path

from textproof.models import Issue, IssueKind


def apply_fixes(
    root: str | Path,
    issues: list[Issue],
    interactive: bool = True,
) -> int:
    root = Path(root)
    fixable = [i for i in issues if i.suggestion and i.original]
    if not fixable:
        return 0

    grouped: dict[str, list[Issue]] = {}
    for i in fixable:
        grouped.setdefault(i.file, []).append(i)

    applied = 0
    for rel, file_issues in grouped.items():
        path = root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        lines = text.splitlines(keepends=True)
        for issue in file_issues:
            if issue.line < 1 or issue.line > len(lines):
                continue
            line = lines[issue.line - 1]
            if issue.original not in line:
                continue
            new_line = line.replace(issue.original, issue.suggestion)
            if interactive:
                print(f"\n文件：{rel}  第 {issue.line} 行")
                print(f"  原文：{line.rstrip()}")
                print(f"  替换：{new_line.rstrip()}")
                choice = input("  应用此修改？[y/N/a(ll)/q(uit)] ").strip().lower()
                if choice == "a":
                    interactive = False
                elif choice == "q":
                    return applied
                elif choice != "y":
                    continue
            lines[issue.line - 1] = new_line
            applied += 1

        path.write_text("".join(lines), encoding="utf-8")

    return applied
