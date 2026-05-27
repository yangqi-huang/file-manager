from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

from office_diagram.extractors import ExtractionError
from office_diagram.generator import GenerationError
from office_diagram.service import generate_diagrams


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


class DiagramHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path not in STATIC_FILES:
            self._json({"error": "页面不存在。"}, HTTPStatus.NOT_FOUND)
            return
        filename, content_type = STATIC_FILES[path]
        try:
            content = (STATIC_DIR / filename).read_bytes()
        except FileNotFoundError:
            self._json({"error": "静态资源不存在。"}, HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/generate":
            self._json({"error": "接口不存在。"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 18 * 1024 * 1024:
                raise ValueError("请求内容过大。")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = generate_diagrams(payload)
            self._json(result, HTTPStatus.OK)
        except (ValueError, ExtractionError, GenerationError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._json({"error": "请求格式不是有效 JSON。"}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            print(f"Unexpected server error: {exc}", file=sys.stderr)
            self._json({"error": "服务器处理失败，请检查终端日志。"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[office-diagram] {self.address_string()} {fmt % args}")

    def _json(self, payload: dict[str, object], status: HTTPStatus) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    host = "127.0.0.1"
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer((host, port), DiagramHandler)
    print(f"AI 办公结构图工具已启动：http://{host}:{port}")
    print("按 Ctrl+C 停止服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("\n服务已停止。")


if __name__ == "__main__":
    main()
