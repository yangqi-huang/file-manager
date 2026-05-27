from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


_WHITESPACE = re.compile(r"\s+")


def clean_label(value: object, fallback: str = "未命名节点") -> str:
    text = _WHITESPACE.sub(" ", str(value or "")).strip()
    return text[:120] or fallback


@dataclass
class Node:
    label: str
    children: list["Node"] = field(default_factory=list)
    note: str = ""

    @classmethod
    def from_dict(cls, value: Any) -> "Node":
        if not isinstance(value, dict):
            return cls(clean_label(value))
        raw_children = value.get("children") or []
        if not isinstance(raw_children, list):
            raw_children = []
        return cls(
            label=clean_label(value.get("label") or value.get("name")),
            note=clean_label(value.get("note") or "", fallback="")[:240],
            children=[cls.from_dict(child) for child in raw_children[:30]],
        )

    def as_dict(self) -> dict[str, Any]:
        output: dict[str, Any] = {"label": self.label}
        if self.note:
            output["note"] = self.note
        if self.children:
            output["children"] = [child.as_dict() for child in self.children]
        return output


@dataclass
class DiagramSpec:
    title: str
    diagram_type: str
    root: Node

    @classmethod
    def from_dict(cls, value: dict[str, Any], diagram_type: str) -> "DiagramSpec":
        title = clean_label(value.get("title") or "文档结构图")
        root = Node.from_dict(value.get("root") or {"label": title})
        return cls(title=title, diagram_type=diagram_type, root=root)

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "diagram_type": self.diagram_type,
            "root": self.root.as_dict(),
        }

