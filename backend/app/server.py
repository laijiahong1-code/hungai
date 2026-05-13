from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .services import (
    get_company_detail,
    get_all_provinces,
    get_province_companies,
    get_top_companies,
    search_entities,
)


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "china-reform-score-main" / "china-reform-score-main" / "dist"

CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".gif": "image/gif",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


class MixedReformHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api_get(parsed)
            return

        static_path = (FRONTEND_DIR / parsed.path.lstrip("/")).resolve()
        if static_path.is_file() and FRONTEND_DIR in static_path.parents:
            self._send_file(static_path, self._content_type(static_path))
            return

        index_path = FRONTEND_DIR / "index.html"
        if index_path.is_file():
            self._send_file(index_path, "text/html; charset=utf-8")
            return

        self._send_json(
            {
                "error": "frontend_build_missing",
                "message": "React build not found. Run npm run build in china-reform-score-main/china-reform-score-main.",
            },
            status=503,
        )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/import/excel":
            self._send_json(
                {
                    "status": "placeholder",
                    "message": "Excel 导入接口已预留。真实数据和评分规则补充后接入。",
                },
                status=202,
            )
            return
        self.send_error(404, "Not found")

    def _handle_api_get(self, parsed) -> None:
        query = parse_qs(parsed.query)
        path = parsed.path
        try:
            if path == "/api/home/top-companies":
                limit = int(query.get("limit", ["10"])[0])
                self._send_json({"companies": get_top_companies(limit=limit)})
                return
            if path == "/api/search":
                text = query.get("q", [""])[0]
                self._send_json(search_entities(text))
                return
            if path == "/api/provinces":
                self._send_json({"provinces": get_all_provinces()})
                return
            if path.startswith("/api/companies/"):
                stock_code = unquote(path.rsplit("/", 1)[-1])
                self._send_json(get_company_detail(stock_code))
                return
            if path.startswith("/api/provinces/") and path.endswith("/companies"):
                parts = path.split("/")
                province = unquote(parts[3])
                self._send_json({"province": province, "companies": get_province_companies(province)})
                return
            self.send_error(404, "Not found")
        except KeyError:
            self._send_json({"error": "company_not_found"}, status=404)
        except ValueError:
            self._send_json({"error": "bad_request"}, status=400)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path, content_type: str) -> None:
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _content_type(self, path: Path) -> str:
        return CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), MixedReformHandler)
    print(f"Serving 混改潜力评分系统 at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
