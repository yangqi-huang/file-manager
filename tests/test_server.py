from __future__ import annotations

import base64
import json
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from server import DiagramHandler, ThreadingHTTPServer


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), DiagramHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_serves_web_application(self) -> None:
        with urlopen(f"{self.url}/", timeout=3) as response:
            page = response.read().decode("utf-8")

        self.assertIn("AI 办公结构图助手", page)
        self.assertIn("体验示例文档", page)

    def test_generation_endpoint(self) -> None:
        payload = json.dumps(
            {
                "filename": "项目.md",
                "diagram_type": "mindmap",
                "use_ai": False,
                "content_base64": base64.b64encode("# 项目\n## 目标".encode()).decode(),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            f"{self.url}/api/generate",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        with urlopen(request, timeout=3) as response:
            result = json.loads(response.read().decode("utf-8"))

        self.assertIn("项目.drawio", result["files"])


if __name__ == "__main__":
    unittest.main()
