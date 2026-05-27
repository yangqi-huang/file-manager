from __future__ import annotations

import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import DiagramSpec, Node, clean_label


class GenerationError(RuntimeError):
    pass


DIAGRAM_GUIDANCE = {
    "mindmap": "提炼核心主题，按主题、要点、细节形成层级。",
    "flowchart": "识别步骤、判断条件与结果，按实际流程顺序组织节点。",
    "orgchart": "识别组织、岗位、职责或隶属关系，按上下级组织节点。",
    "knowledge": "按概念、分类、事实和结论建立知识树。",
}


class DeepSeekGenerator:
    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.base_url = os.getenv(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions"
        )
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, text: str, filename: str, diagram_type: str) -> DiagramSpec:
        if not self.configured:
            raise GenerationError("尚未配置 DEEPSEEK_API_KEY。")
        if not self.api_key.isascii() or self.api_key in {
            "your_api_key_here",
            "sk_your_api_key_here",
        }:
            raise GenerationError(
                "DEEPSEEK_API_KEY 必须填写真实密钥，不能使用示例占位文字。"
            )
        prompt = _prompt(text, filename, diagram_type)
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是办公文档结构化助手。只返回合法 JSON，不使用 Markdown 代码块。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            self.base_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(_strip_code_fence(content))
            return DiagramSpec.from_dict(parsed, diagram_type)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:240]
            raise GenerationError(f"DeepSeek 请求失败（HTTP {exc.code}）：{detail}") from exc
        except (URLError, TimeoutError) as exc:
            raise GenerationError(f"无法连接 DeepSeek API：{exc}") from exc
        except (KeyError, json.JSONDecodeError) as exc:
            raise GenerationError("DeepSeek 返回内容无法解析为结构图数据。") from exc


def local_generate(text: str, filename: str, diagram_type: str) -> DiagramSpec:
    title = clean_label(Path(filename).stem, "文档结构图")
    root = Node(title)
    if any(re.match(r"^\s*#{1,6}\s+", line) for line in text.splitlines()):
        _append_markdown_nodes(root, text)
    else:
        _append_plain_nodes(root, text)
    if not root.children:
        root.children.append(Node("未提取到有效文本"))
    return DiagramSpec(title=title, diagram_type=diagram_type, root=root)


def _append_markdown_nodes(root: Node, text: str) -> None:
    heading_stack: list[tuple[int, Node]] = [(0, root)]
    for raw_line in text.splitlines()[:80]:
        line = raw_line.strip()
        if not line:
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            depth = len(heading.group(1))
            node = Node(clean_label(heading.group(2)))
            while heading_stack[-1][0] >= depth:
                heading_stack.pop()
            heading_stack[-1][1].children.append(node)
            heading_stack.append((depth, node))
            continue
        bullet = re.match(r"^(?:[-*+]|\d+[.)、])\s+(.+?)\s*$", line)
        label = bullet.group(1) if bullet else line
        heading_stack[-1][1].children.append(Node(clean_label(label)))


def _append_plain_nodes(root: Node, text: str) -> None:
    meaningful = [
        re.sub(r"^[*\-\d.\s、]+", "", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]
    current: Node | None = None
    for line in meaningful[:35]:
        if _looks_like_heading(line) or current is None:
            current = Node(clean_label(line))
            root.children.append(current)
        else:
            current.children.append(Node(clean_label(line)))


def _looks_like_heading(line: str) -> bool:
    return (
        len(line) <= 28
        and (line.endswith(("：", ":")) or not any(mark in line for mark in "，。；;"))
    )


def _prompt(text: str, filename: str, diagram_type: str) -> str:
    clipped = text[:60000]
    return f"""根据以下文档生成{diagram_type}结构图数据。
任务要求：{DIAGRAM_GUIDANCE.get(diagram_type, DIAGRAM_GUIDANCE["mindmap"])}
输出 JSON 格式必须严格为：
{{
  "title": "图表标题",
  "root": {{
    "label": "中心/起始节点",
    "note": "可选简短说明",
    "children": [{{"label": "节点", "children": []}}]
  }}
}}
要求：节点名称简洁；最多 4 层、每层最多 12 个节点；不编造原文没有的信息。
文件名：{filename}
文档正文：
{clipped}"""


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped
