from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile


class ExtractionError(ValueError):
    pass


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".json", ".xml", ".html"}:
        return _decode_text(content)
    if suffix == ".docx":
        return _extract_docx(content)
    if suffix == ".pptx":
        return _extract_pptx(content)
    if suffix == ".xlsx":
        return _extract_xlsx(content)
    if suffix == ".pdf":
        return _extract_pdf(content)
    raise ExtractionError("暂不支持该文件类型，请上传 TXT、MD、CSV、DOCX、PPTX、XLSX 或 PDF。")


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ExtractionError("文本编码无法识别，请将文件另存为 UTF-8 后重试。")


def _xml_text(data: bytes) -> str:
    root = ET.fromstring(data)
    paragraphs: list[str] = []
    for element in root.iter():
        if element.tag.endswith("}p"):
            text = "".join(
                child.text or ""
                for child in element.iter()
                if child.tag.endswith(("}t", "}tab", "}br"))
            ).strip()
            if text:
                paragraphs.append(text)
    if paragraphs:
        return "\n".join(paragraphs)
    return "\n".join(text.strip() for text in root.itertext() if text.strip())


def _extract_docx(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            return _xml_text(archive.read("word/document.xml"))
    except (KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise ExtractionError("无法读取 DOCX 文件，文件可能已损坏。") from exc


def _extract_pptx(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            slides = sorted(
                (
                    name for name in archive.namelist()
                    if re.match(r"ppt/slides/slide\d+\.xml$", name)
                ),
                key=_numeric_xml_part,
            )
            return "\n".join(_xml_text(archive.read(name)) for name in slides)
    except (zipfile.BadZipFile, ET.ParseError) as exc:
        raise ExtractionError("无法读取 PPTX 文件，文件可能已损坏。") from exc


def _extract_xlsx(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                strings_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = [
                    "".join(item.itertext()).strip()
                    for item in strings_root
                ]
            sheet_names = sorted(
                (
                    name for name in archive.namelist()
                    if re.match(r"xl/worksheets/sheet\d+\.xml$", name)
                ),
                key=_numeric_xml_part,
            )
            lines: list[str] = []
            for number, sheet_name in enumerate(sheet_names, start=1):
                lines.append(f"工作表 {number}")
                root = ET.fromstring(archive.read(sheet_name))
                for row in (element for element in root.iter() if element.tag.endswith("}row")):
                    values = []
                    for cell in (element for element in row if element.tag.endswith("}c")):
                        value_node = next(
                            (node for node in cell if node.tag.endswith("}v")), None
                        )
                        value = value_node.text if value_node is not None else ""
                        if cell.attrib.get("t") == "s" and value and value.isdigit():
                            value = shared[int(value)]
                        values.append(value or "")
                    if any(values):
                        lines.append(" | ".join(values))
            return "\n".join(lines)
    except (zipfile.BadZipFile, ET.ParseError, IndexError) as exc:
        raise ExtractionError("无法读取 XLSX 文件，文件可能已损坏。") from exc


def _numeric_xml_part(filename: str) -> int:
    match = re.search(r"(\d+)\.xml$", filename)
    return int(match.group(1)) if match else 0


def _extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ExtractionError(
            "当前启动服务的 Python 未安装 PDF 依赖。请停止服务后执行："
            "source .venv/bin/activate && python -m pip install -r requirements.txt "
            "&& python server.py"
        ) from exc
    try:
        reader = PdfReader(BytesIO(content))
        return _normalize_pdf_text("\n".join(page.extract_text() or "" for page in reader.pages))
    except Exception as exc:
        raise ExtractionError("无法提取 PDF 内容；扫描版 PDF 需要先进行 OCR。") from exc


def _normalize_pdf_text(text: str) -> str:
    # Many PDFs split an English word at the visual line end with a hyphen.
    text = re.sub(r"([A-Za-z])-\s*\n\s*([a-z])", r"\1\2", text)
    return re.sub(r"[ \t]+\n", "\n", text)
