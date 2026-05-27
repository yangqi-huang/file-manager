from __future__ import annotations

from dataclasses import dataclass
import math
import re
import xml.etree.ElementTree as ET

from .models import DiagramSpec, Node


@dataclass
class PositionedNode:
    node_id: str
    label: str
    x: int
    y: int
    parent_id: str | None


def to_markdown(spec: DiagramSpec) -> str:
    lines = [f"# {spec.root.label}", ""]

    def write(node: Node, depth: int) -> None:
        if depth <= 5:
            lines.append(f"{'#' * (depth + 1)} {node.label}")
        else:
            lines.append(f"{'  ' * (depth - 5)}- {node.label}")
        if node.note:
            lines.append(node.note)
        for child in node.children:
            write(child, depth + 1)

    for child in spec.root.children:
        write(child, 1)
    return "\n".join(lines).rstrip() + "\n"


def to_mermaid(spec: DiagramSpec) -> str:
    if spec.diagram_type == "mindmap":
        lines = ["mindmap", f"  root(({_mermaid_text(spec.root.label)}))"]

        def append_mindmap(node: Node, depth: int) -> None:
            lines.append(f"{'  ' * depth}{_mermaid_text(node.label)}")
            for child in node.children:
                append_mindmap(child, depth + 1)

        for child in spec.root.children:
            append_mindmap(child, 2)
        return "\n".join(lines) + "\n"

    direction = "TB" if spec.diagram_type == "orgchart" else "TD"
    lines = [f"flowchart {direction}"]
    counter = 0

    def append_graph(node: Node, parent_id: str | None = None) -> None:
        nonlocal counter
        node_id = f"N{counter}"
        counter += 1
        label = _mermaid_text(node.label).replace('"', "'")
        shape = f'{node_id}["{label}"]'
        lines.append(f"    {shape}")
        if parent_id:
            lines.append(f"    {parent_id} --> {node_id}")
        for child in node.children:
            append_graph(child, node_id)

    append_graph(spec.root)
    return "\n".join(lines) + "\n"


def to_drawio(spec: DiagramSpec) -> str:
    nodes = _layout_nodes(spec.root)
    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "version": "24.7.17"})
    diagram = ET.SubElement(mxfile, "diagram", {"name": spec.title, "id": "diagram-1"})
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": "1200",
            "dy": "800",
            "grid": "1",
            "gridSize": "10",
            "page": "1",
            "pageWidth": "1169",
            "pageHeight": "827",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    for positioned in nodes:
        style = (
            "rounded=1;whiteSpace=wrap;html=1;fillColor=#e8f0fe;"
            "strokeColor=#4f76d9;fontSize=14;"
        )
        if positioned.parent_id is None:
            style = (
                "ellipse;whiteSpace=wrap;html=1;fillColor=#2563eb;"
                "fontColor=#ffffff;strokeColor=#1d4ed8;fontSize=16;fontStyle=1;"
            )
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": positioned.node_id,
                "value": positioned.label,
                "style": style,
                "vertex": "1",
                "parent": "1",
            },
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": str(positioned.x),
                "y": str(positioned.y),
                "width": "150",
                "height": "58",
                "as": "geometry",
            },
        )
        if positioned.parent_id:
            edge = ET.SubElement(
                root,
                "mxCell",
                {
                    "id": f"e-{positioned.parent_id}-{positioned.node_id}",
                    "style": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;",
                    "edge": "1",
                    "parent": "1",
                    "source": positioned.parent_id,
                    "target": positioned.node_id,
                },
            )
            ET.SubElement(edge, "mxGeometry", {"relative": "1", "as": "geometry"})
    ET.indent(mxfile, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        mxfile, encoding="unicode"
    )


def _layout_nodes(root: Node) -> list[PositionedNode]:
    flattened: list[PositionedNode] = []
    next_y = 40

    def place(node: Node, depth: int, parent_id: str | None) -> tuple[str, float]:
        nonlocal next_y
        node_id = f"n{len(flattened) + 2}"
        item = PositionedNode(node_id, node.label, 50 + depth * 220, 0, parent_id)
        flattened.append(item)
        if not node.children:
            item.y = next_y
            next_y += 90
            return node_id, item.y
        child_ys = [place(child, depth + 1, node_id)[1] for child in node.children]
        item.y = math.floor(sum(child_ys) / len(child_ys))
        return node_id, item.y

    place(root, 0, None)
    return flattened


def _mermaid_text(value: str) -> str:
    return re.sub(r"[\[\]{}()]", "", value).replace("\n", " ").strip()

