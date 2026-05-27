from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Any

from .exporters import to_drawio, to_markdown, to_mermaid
from .extractors import ExtractionError, extract_text
from .generator import DeepSeekGenerator, GenerationError, local_generate


SUPPORTED_TYPES = {"mindmap", "flowchart", "orgchart", "knowledge"}
MAX_FILE_BYTES = 12 * 1024 * 1024


def generate_diagrams(payload: dict[str, Any]) -> dict[str, Any]:
    filename = Path(str(payload.get("filename") or "document.txt")).name
    diagram_type = str(payload.get("diagram_type") or "mindmap")
    if diagram_type not in SUPPORTED_TYPES:
        raise ValueError("未知的图表类型。")
    try:
        content = base64.b64decode(str(payload.get("content_base64") or ""), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("上传文件内容无效。") from exc
    if not content:
        raise ValueError("请先选择包含内容的文件。")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("文件不得超过 12 MB。")
    extracted = extract_text(filename, content).strip()
    if not extracted:
        raise ExtractionError("文件中未能提取到文本内容。")

    warnings: list[str] = []
    ai = DeepSeekGenerator()
    use_ai = bool(payload.get("use_ai", True))
    if use_ai and ai.configured:
        spec = ai.generate(extracted, filename, diagram_type)
        generated_by = f"DeepSeek ({ai.model})"
    else:
        spec = local_generate(extracted, filename, diagram_type)
        generated_by = "本地预览规则"
        if use_ai and not ai.configured:
            warnings.append("未配置 DEEPSEEK_API_KEY，已改用本地预览规则生成。")
    stem = Path(filename).stem or "diagram"
    return {
        "spec": spec.as_dict(),
        "generated_by": generated_by,
        "warnings": warnings,
        "text_preview": extracted[:1200],
        "files": {
            f"{stem}-xmind.md": to_markdown(spec),
            f"{stem}-drawio.mmd": to_mermaid(spec),
            f"{stem}.drawio": to_drawio(spec),
        },
    }

