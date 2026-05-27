from __future__ import annotations

from io import BytesIO
import builtins
import unittest
from unittest.mock import patch
import zipfile

from office_diagram.extractors import ExtractionError, extract_text


class ExtractorTests(unittest.TestCase):
    def test_extracts_markdown_text(self) -> None:
        content = "# 项目目标\n\n- 完成上线".encode("utf-8")

        result = extract_text("会议.md", content)

        self.assertIn("项目目标", result)

    def test_extracts_docx_paragraphs_without_dependency(self) -> None:
        docx = BytesIO()
        xml = (
            '<w:document xmlns:w="urn:test"><w:body>'
            '<w:p><w:r><w:t>启动会</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>确认分工</w:t></w:r></w:p>'
            "</w:body></w:document>"
        )
        with zipfile.ZipFile(docx, "w") as archive:
            archive.writestr("word/document.xml", xml)

        result = extract_text("minutes.docx", docx.getvalue())

        self.assertEqual(result, "启动会\n确认分工")

    def test_rejects_unsupported_file(self) -> None:
        with self.assertRaises(ExtractionError):
            extract_text("image.png", b"content")

    def test_pdf_dependency_error_points_to_virtual_environment(self) -> None:
        original_import = builtins.__import__

        def missing_pypdf(name: str, *args: object, **kwargs: object) -> object:
            if name == "pypdf":
                raise ImportError("not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=missing_pypdf):
            with self.assertRaisesRegex(ExtractionError, r"source \.venv/bin/activate"):
                extract_text("report.pdf", b"%PDF")


if __name__ == "__main__":
    unittest.main()
