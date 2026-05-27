from __future__ import annotations

import base64
import unittest
from unittest.mock import patch

from office_diagram.service import generate_diagrams


class ServiceTests(unittest.TestCase):
    def test_local_mode_produces_all_downloads(self) -> None:
        payload = {
            "filename": "启动会.md",
            "diagram_type": "mindmap",
            "use_ai": False,
            "content_base64": base64.b64encode(
                "# 启动会\n## 分工\n技术组负责开发".encode("utf-8")
            ).decode("ascii"),
        }

        result = generate_diagrams(payload)

        self.assertEqual(result["generated_by"], "本地预览规则")
        self.assertIn("启动会-xmind.md", result["files"])
        self.assertIn("启动会-drawio.mmd", result["files"])
        self.assertIn("启动会.drawio", result["files"])
        self.assertIn("#### 技术组负责开发", result["files"]["启动会-xmind.md"])

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_falls_back_with_warning(self) -> None:
        payload = {
            "filename": "brief.txt",
            "diagram_type": "flowchart",
            "use_ai": True,
            "content_base64": base64.b64encode(b"submit\napprove\nfinish").decode("ascii"),
        }

        result = generate_diagrams(payload)

        self.assertTrue(result["warnings"])
        self.assertIn("flowchart TD", result["files"]["brief-drawio.mmd"])

    def test_rejects_unknown_diagram_type(self) -> None:
        with self.assertRaises(ValueError):
            generate_diagrams({"diagram_type": "unknown"})

    def test_local_mode_keeps_long_node_text_in_exports(self) -> None:
        text = "这是一个需要完整展示而不能在图形节点中被省略的较长工作事项描述" * 3
        payload = {
            "filename": "长文本.txt",
            "diagram_type": "mindmap",
            "use_ai": False,
            "content_base64": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        }

        result = generate_diagrams(payload)

        self.assertIn(text, result["files"]["长文本-xmind.md"])
        self.assertIn(text, result["spec"]["root"]["children"][0]["label"])


if __name__ == "__main__":
    unittest.main()
