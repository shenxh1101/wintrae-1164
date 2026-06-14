from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Rules:
    def __init__(self) -> None:
        self.terminology: dict[str, str] = {}
        self.forbidden_words: list[str] = []
        self.name_aliases: dict[str, list[str]] = {}
        self.date_patterns: list[str] = ["YYYY-MM-DD"]
        self.number_style: str = "halfwidth"
        self.heading_levels: dict[str, int] = {}

    @classmethod
    def from_file(cls, path: str | Path) -> "Rules":
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        if p.suffix in (".yaml", ".yml"):
            return cls._from_yaml(text)
        data = json.loads(text)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Rules":
        r = cls()
        r.terminology = data.get("terminology", {})
        r.forbidden_words = data.get("forbidden_words", [])
        raw_names: dict[str, list[str]] = data.get("name_aliases", {})
        r.name_aliases = {canonical: aliases for canonical, aliases in raw_names.items()}
        r.date_patterns = data.get("date_patterns", r.date_patterns)
        r.number_style = data.get("number_style", r.number_style)
        r.heading_levels = data.get("heading_levels", {})
        return r

    @classmethod
    def _from_yaml(cls, text: str) -> "Rules":
        try:
            import yaml

            data = yaml.safe_load(text) or {}
            return cls._from_dict(data)
        except ImportError:
            raise RuntimeError("PyYAML is required to load .yaml/.yml rules files.  pip install pyyaml")

    def canonical_name(self, token: str) -> str | None:
        for canonical, aliases in self.name_aliases.items():
            if token == canonical or token in aliases:
                return canonical
        return None
