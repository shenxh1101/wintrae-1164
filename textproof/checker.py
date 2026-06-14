from __future__ import annotations

import re
from pathlib import Path
from collections import Counter

from textproof.models import Issue, IssueKind, Severity, CompareResult
from textproof.rules import Rules


_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
_DATE_CANDIDATES = re.compile(
    r"\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})"
    r"|(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    r"|(\d{4}年\d{1,2}月\d{1,2}日)"
    r"|(\d{1,2}月\d{1,2}日)"
)
_NUMBER_CANDIDATES = re.compile(r"[\d０-９]+(?:\.[\d０-９]+)?")


class Checker:
    def __init__(self, rules: Rules) -> None:
        self.rules = rules

    def check_file(self, file_path: str | Path, root: str | Path) -> list[Issue]:
        path = Path(root) / file_path
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []
        lines = text.splitlines()
        rel = str(file_path)
        issues: list[Issue] = []
        issues.extend(self._check_forbidden(rel, lines))
        issues.extend(self._check_terminology(rel, lines))
        issues.extend(self._check_names(rel, lines))
        issues.extend(self._check_numbers(rel, lines))
        issues.extend(self._check_dates(rel, lines))
        issues.extend(self._check_headings(rel, text))
        issues.extend(self._check_duplicate_paragraphs(rel, lines))
        return issues

    def check_group(
        self,
        files: list[str],
        root: str | Path,
    ) -> list[Issue]:
        all_issues: list[Issue] = []
        all_issues.extend(self._check_missing_chapters(files, root))
        all_issues.extend(self._check_heading_consistency(files, root))
        return all_issues

    def _check_forbidden(self, rel: str, lines: list[str]) -> list[Issue]:
        issues: list[Issue] = []
        for idx, line in enumerate(lines, 1):
            for word in self.rules.forbidden_words:
                pos = line.find(word)
                while pos != -1:
                    issues.append(
                        Issue(
                            kind=IssueKind.FORBIDDEN_WORD,
                            severity=Severity.ERROR,
                            file=rel,
                            line=idx,
                            message=f"禁用词「{word}」",
                            original=word,
                            suggestion="",
                        )
                    )
                    pos = line.find(word, pos + len(word))
        return issues

    def _check_terminology(self, rel: str, lines: list[str]) -> list[Issue]:
        issues: list[Issue] = []
        for idx, line in enumerate(lines, 1):
            for wrong, correct in self.rules.terminology.items():
                pos = line.find(wrong)
                while pos != -1:
                    issues.append(
                        Issue(
                            kind=IssueKind.TERMINOLOGY,
                            severity=Severity.WARNING,
                            file=rel,
                            line=idx,
                            message=f"术语不一致：「{wrong}」应为「{correct}」",
                            original=wrong,
                            suggestion=correct,
                        )
                    )
                    pos = line.find(wrong, pos + len(wrong))
        return issues

    def _check_names(self, rel: str, lines: list[str]) -> list[Issue]:
        issues: list[Issue] = []
        for idx, line in enumerate(lines, 1):
            for canonical, aliases in self.rules.name_aliases.items():
                for alias in aliases:
                    pos = line.find(alias)
                    while pos != -1:
                        issues.append(
                            Issue(
                                kind=IssueKind.NAME_INCONSISTENCY,
                                severity=Severity.WARNING,
                                file=rel,
                                line=idx,
                                message=f"人名/地名不统一：「{alias}」应为「{canonical}」",
                                original=alias,
                                suggestion=canonical,
                            )
                        )
                        pos = line.find(alias, pos + len(alias))
        return issues

    def _check_numbers(self, rel: str, lines: list[str]) -> list[Issue]:
        issues: list[Issue] = []
        if self.rules.number_style == "halfwidth":
            for idx, line in enumerate(lines, 1):
                for m in _NUMBER_CANDIDATES.finditer(line):
                    token = m.group()
                    if any("\uff10" <= c <= "\uff19" for c in token):
                        corrected = token.translate(_FULLWIDTH_DIGITS)
                        issues.append(
                            Issue(
                                kind=IssueKind.NUMBER_FORMAT,
                                severity=Severity.INFO,
                                file=rel,
                                line=idx,
                                message=f"数字格式：「{token}」应为半角「{corrected}」",
                                original=token,
                                suggestion=corrected,
                            )
                        )
        elif self.rules.number_style == "fullwidth":
            for idx, line in enumerate(lines, 1):
                for m in _NUMBER_CANDIDATES.finditer(line):
                    token = m.group()
                    if any("0" <= c <= "9" for c in token):
                        fw = "".join(
                            chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in token
                        )
                        issues.append(
                            Issue(
                                kind=IssueKind.NUMBER_FORMAT,
                                severity=Severity.INFO,
                                file=rel,
                                line=idx,
                                message=f"数字格式：「{token}」应为全角「{fw}」",
                                original=token,
                                suggestion=fw,
                            )
                        )
        return issues

    def _check_dates(self, rel: str, lines: list[str]) -> list[Issue]:
        issues: list[Issue] = []
        expected = self.rules.date_patterns
        for idx, line in enumerate(lines, 1):
            for m in _DATE_CANDIDATES.finditer(line):
                token = m.group()
                if not self._date_matches_any(token, expected):
                    issues.append(
                        Issue(
                            kind=IssueKind.DATE_FORMAT,
                            severity=Severity.INFO,
                            file=rel,
                            line=idx,
                            message=f"日期格式「{token}」不符合要求（期望：{' / '.join(expected)}）",
                            original=token,
                            suggestion="",
                        )
                    )
        return issues

    @staticmethod
    def _date_matches_any(token: str, patterns: list[str]) -> bool:
        for pat in patterns:
            if pat == "YYYY-MM-DD":
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
                    return True
            elif pat == "YYYY/MM/DD":
                if re.fullmatch(r"\d{4}/\d{2}/\d{2}", token):
                    return True
            elif pat == "YYYY年MM月DD日":
                if re.fullmatch(r"\d{4}年\d{1,2}月\d{1,2}日", token):
                    return True
            elif pat == "MM月DD日":
                if re.fullmatch(r"\d{1,2}月\d{1,2}日", token):
                    return True
        return False

    def _check_headings(self, rel: str, text: str) -> list[Issue]:
        issues: list[Issue] = []
        for m in _HEADING_RE.finditer(text):
            level = len(m.group(1))
            title = m.group(2).strip()
            line_no = text[: m.start()].count("\n") + 1
            if title in self.rules.heading_levels:
                expected = self.rules.heading_levels[title]
                if level != expected:
                    issues.append(
                        Issue(
                            kind=IssueKind.HEADING_LEVEL,
                            severity=Severity.WARNING,
                            file=rel,
                            line=line_no,
                            message=f"标题层级：「{title}」为 H{level}，期望 H{expected}",
                            original="#" * level,
                            suggestion="#" * expected,
                        )
                    )
        return issues

    @staticmethod
    def _check_duplicate_paragraphs(rel: str, lines: list[str]) -> list[Issue]:
        issues: list[Issue] = []
        para: list[str] = []
        start_line = 0
        para_map: dict[str, list[tuple[int, int]]] = {}

        def flush() -> None:
            nonlocal para, start_line
            if not para:
                return
            text = "\n".join(para).strip()
            if text:
                para_map.setdefault(text, []).append((start_line, len(para)))
            para = []

        for idx, line in enumerate(lines, 1):
            if line.strip() == "":
                flush()
                continue
            if not para:
                start_line = idx
            para.append(line)
        flush()

        for _text, spans in para_map.items():
            if len(spans) > 1:
                first_start, first_len = spans[0]
                preview = _text[:60] + ("…" if len(_text) > 60 else "")
                issues.append(
                    Issue(
                        kind=IssueKind.DUPLICATE_PARAGRAPH,
                        severity=Severity.WARNING,
                        file=rel,
                        line=first_start,
                        message=f"重复段落（出现 {len(spans)} 次）：{preview}",
                        original=_text,
                        suggestion="",
                    )
                )
        return issues

    @staticmethod
    def _check_missing_chapters(files: list[str], root: str | Path) -> list[Issue]:
        issues: list[Issue] = []
        if not files:
            return issues

        file_titles: dict[str, set[str]] = {}
        group = Path(files[0]).stem
        for f in files:
            path = Path(root) / f
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            headings = {m.group(2).strip() for m in _HEADING_RE.finditer(text)}
            file_titles[f] = headings

        all_titles: set[str] = set()
        for titles in file_titles.values():
            all_titles.update(titles)

        for f, titles in file_titles.items():
            missing = all_titles - titles
            for title in sorted(missing):
                issues.append(
                    Issue(
                        kind=IssueKind.MISSING_CHAPTER,
                        severity=Severity.WARNING,
                        file=f,
                        line=0,
                        message=f"缺失章节：「{title}」",
                        original="",
                        suggestion="",
                    )
                )
        return issues

    @staticmethod
    def _check_heading_consistency(files: list[str], root: str | Path) -> list[Issue]:
        issues: list[Issue] = []
        title_levels: dict[str, set[int]] = {}
        for f in files:
            path = Path(root) / f
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for m in _HEADING_RE.finditer(text):
                level = len(m.group(1))
                title = m.group(2).strip()
                title_levels.setdefault(title, set()).add(level)

        for title, levels in title_levels.items():
            if len(levels) > 1:
                issues.append(
                    Issue(
                        kind=IssueKind.HEADING_LEVEL,
                        severity=Severity.WARNING,
                        file="",
                        line=0,
                        message=f"标题层级不一致：「{title}」同时出现在 {', '.join(f'H{l}' for l in sorted(levels))}",
                        original="",
                        suggestion="",
                    )
                )
        return issues
