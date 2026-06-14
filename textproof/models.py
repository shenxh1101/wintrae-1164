from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueKind(Enum):
    FORBIDDEN_WORD = "forbidden_word"
    TERMINOLOGY = "terminology"
    NAME_INCONSISTENCY = "name_inconsistency"
    NUMBER_FORMAT = "number_format"
    DATE_FORMAT = "date_format"
    HEADING_LEVEL = "heading_level"
    DUPLICATE_PARAGRAPH = "duplicate_paragraph"
    MISSING_CHAPTER = "missing_chapter"


@dataclass
class Issue:
    kind: IssueKind
    severity: Severity
    file: str
    line: int
    message: str
    original: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "severity": self.severity.value,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "original": self.original,
            "suggestion": self.suggestion,
        }


@dataclass
class ScanResult:
    files: list[str] = field(default_factory=list)
    groups: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class CompareResult:
    issues: list[Issue] = field(default_factory=list)

    def by_severity(self) -> dict[Severity, list[Issue]]:
        buckets: dict[Severity, list[Issue]] = {s: [] for s in Severity}
        for issue in self.issues:
            buckets[issue.severity].append(issue)
        return buckets

    def to_dict(self) -> dict:
        return {
            "total": len(self.issues),
            "by_severity": {
                s.value: len(issues) for s, issues in self.by_severity().items()
            },
            "issues": [i.to_dict() for i in self.issues],
        }
