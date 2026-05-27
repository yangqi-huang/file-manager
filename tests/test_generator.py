from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from office_diagram.generator import DeepSeekGenerator, GenerationError


class _Response:
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"title": "启动会", "root": {"label": "启动会"}},
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")


class GeneratorTests(unittest.TestCase):
    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "你的 API Key"}, clear=True)
    def test_rejects_chinese_placeholder_api_key_before_http_request(self) -> None:
        with self.assertRaisesRegex(GenerationError, "示例占位文字"):
            DeepSeekGenerator().generate("正文", "会议纪要.pdf", "mindmap")

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk_your_api_key_here"}, clear=True)
    def test_rejects_ascii_placeholder_api_key_before_http_request(self) -> None:
        with self.assertRaisesRegex(GenerationError, "示例占位文字"):
            DeepSeekGenerator().generate("正文", "会议纪要.pdf", "mindmap")

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-test-key"}, clear=True)
    @patch("office_diagram.generator.urlopen", return_value=_Response())
    def test_chinese_filename_is_encoded_in_json_body(self, mocked_open: object) -> None:
        DeepSeekGenerator().generate("正文", "会议纪要.pdf", "mindmap")

        request = mocked_open.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertIn("会议纪要.pdf", body["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
