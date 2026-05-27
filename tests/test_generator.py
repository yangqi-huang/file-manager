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
    def test_request_uses_stable_parameters_and_utf8_filename(self, mocked_open: object) -> None:
        DeepSeekGenerator().generate("正文", "会议纪要.pdf", "mindmap")

        request = mocked_open.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body["max_tokens"], 8192)
        self.assertIn("固定提取规则", body["messages"][1]["content"])
        self.assertIn("详细", body["messages"][1]["content"])
        self.assertIn("会议纪要.pdf", body["messages"][1]["content"])

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-test-key"}, clear=True)
    @patch("office_diagram.generator.urlopen", return_value=_Response())
    def test_selected_detail_level_is_in_prompt(self, mocked_open: object) -> None:
        DeepSeekGenerator().generate("正文", "会议纪要.pdf", "mindmap", "concise")

        request = mocked_open.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertIn("简洁", body["messages"][1]["content"])

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-test-key"}, clear=True)
    @patch("office_diagram.generator.urlopen", return_value=_Response())
    def test_english_source_requires_simplified_chinese_translation(
        self, mocked_open: object
    ) -> None:
        DeepSeekGenerator().generate(
            "Customer information workflow and incident resolution steps",
            "briefing.pdf",
            "mindmap",
        )

        request = mocked_open.call_args.args[0]
        prompt = json.loads(request.data.decode("utf-8"))["messages"][1]["content"]
        self.assertIn("统一使用简体中文", prompt)
        self.assertIn("准确翻译为简体中文", prompt)
        self.assertIn("中文（原文）", prompt)

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-test-key"}, clear=True)
    @patch("office_diagram.generator.urlopen", return_value=_Response())
    def test_japanese_source_requires_simplified_chinese_translation(
        self, mocked_open: object
    ) -> None:
        DeepSeekGenerator().generate(
            "顧客対応プロセスとリスク管理について説明します。",
            "報告書.pdf",
            "mindmap",
        )

        request = mocked_open.call_args.args[0]
        prompt = json.loads(request.data.decode("utf-8"))["messages"][1]["content"]
        self.assertIn("日文", prompt)
        self.assertIn("准确翻译为简体中文", prompt)


if __name__ == "__main__":
    unittest.main()
