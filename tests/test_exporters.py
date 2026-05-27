from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from office_diagram.exporters import to_drawio, to_markdown, to_mermaid
from office_diagram.models import DiagramSpec, Node


class ExporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = DiagramSpec(
            title="项目启动会",
            diagram_type="mindmap",
            root=Node("项目启动会", children=[Node("分工", children=[Node("技术组")])]),
        )

    def test_exports_xmind_markdown_hierarchy(self) -> None:
        result = to_markdown(self.spec)

        self.assertIn("# 项目启动会", result)
        self.assertIn("## 分工", result)
        self.assertIn("### 技术组", result)

    def test_exports_mermaid_mindmap(self) -> None:
        result = to_mermaid(self.spec)

        self.assertIn("mindmap", result)
        self.assertIn("root((项目启动会))", result)

    def test_exports_parseable_drawio_xml(self) -> None:
        result = to_drawio(self.spec)
        root = ET.fromstring(result)

        self.assertEqual(root.tag, "mxfile")
        labels = [cell.attrib.get("value") for cell in root.iter("mxCell")]
        self.assertIn("技术组", labels)


if __name__ == "__main__":
    unittest.main()

