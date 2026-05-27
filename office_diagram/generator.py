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

DETAIL_PROFILES = {
    "concise": (
        "简洁：仅保留主要主题与关键结论，通常使用 2-3 层、总节点数约 8-18 个。"
    ),
    "standard": (
        "标准：覆盖文档中所有明确章节及每章核心要点，通常使用 3-4 层、"
        "总节点数约 15-35 个。"
    ),
    "detailed": (
        "详细：覆盖文档中所有明确章节，并尽量保留事项、步骤、责任、日期、"
        "指标、风险和结论等可成节点的信息；使用 3-4 层，总节点数通常为 25-60 个。"
    ),
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

    def generate(
        self, text: str, filename: str, diagram_type: str, detail_level: str = "detailed"
    ) -> DiagramSpec:
        if not self.configured:
            raise GenerationError("尚未配置 DEEPSEEK_API_KEY。")
        if not self.api_key.isascii() or self.api_key in {
            "your_api_key_here",
            "sk_your_api_key_here",
        }:
            raise GenerationError(
                "DEEPSEEK_API_KEY 必须填写真实密钥，不能使用示例占位文字。"
            )
        prompt = _prompt(text, filename, diagram_type, detail_level)
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是稳定、可复现的办公文档结构化助手。严格依据给定的固定提取规则，"
                            "不随意改变详略程度。只返回合法 JSON，不使用 Markdown 代码块。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "thinking": {"type": "disabled"},
                "temperature": 0,
                "max_tokens": 8192,
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


def _prompt(text: str, filename: str, diagram_type: str, detail_level: str) -> str:
    clipped = text[:60000]
    detail_profile = DETAIL_PROFILES.get(detail_level, DETAIL_PROFILES["detailed"])
    return f"""根据以下文档生成{diagram_type}结构图数据。
任务要求：{DIAGRAM_GUIDANCE.get(diagram_type, DIAGRAM_GUIDANCE["mindmap"])}
细节程度：{detail_profile}
输出语言：所有标题、节点和说明统一使用简体中文，便于中文用户阅读。
固定提取规则：
1. 按原文出现顺序组织一级和二级主题；有明确标题时优先沿用标题，不随机改写分类方式。
2. 每次都覆盖原文中明确出现的章节；在所选细节程度下，不得随机忽略某一章节或要点类别。
3. 对并列事项采用相同粒度：同一章节中若保留一种事项，则同类事项应一并保留。
4. 流程图按发生顺序排列；组织图按隶属关系排列；思维导图和知识树按原文章节顺序排列。
5. 节点文字应忠实于原文，不补充推测内容，不因追求简洁而删除关键名词、日期或责任信息。
6. 无论原文是英文、日文、韩文或其他语言，均准确翻译为简体中文输出；产品名、机构名、API、标准编号、缩写等必要专有名词可采用“中文（原文）”形式保留。
7. 翻译前先理解语义，不把同一句话的中间部分当作独立主题；PDF 中孤立换行应按语义恢复连续短语后再归类。
输出 JSON 格式必须严格为：
{{
  "title": "图表标题",
  "root": {{
    "label": "中心/起始节点",
    "note": "可选简短说明",
    "children": [{{"label": "节点", "children": []}}]
  }}
}}
要求：最多 4 层、每层最多 15 个节点；如原文信息超过容量，优先保留标题、行动、决策、时间、责任、指标和风险。
文件名：{filename}
文档正文：
{clipped}"""


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped
