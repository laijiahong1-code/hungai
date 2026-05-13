import json
from types import SimpleNamespace

from backend.app.server import MixedReformHandler


class CapturingHandler(MixedReformHandler):
    def __init__(self):
        self.status = None
        self.headers = {}
        self.body = b""

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, keyword, value):
        self.headers[keyword] = value

    def end_headers(self):
        pass

    @property
    def wfile(self):
        return SimpleNamespace(write=self._write)

    def _write(self, raw):
        self.body += raw


def payload_for(path: str) -> dict:
    handler = CapturingHandler()
    handler.path = path
    handler.do_GET()
    assert handler.status == 200
    assert handler.headers["Content-Type"].startswith("application/json")
    return json.loads(handler.body.decode("utf-8"))


def test_api_home_top_companies_smoke():
    payload = payload_for("/api/home/top-companies?limit=3")

    assert "companies" in payload
    assert len(payload["companies"]) <= 3
    assert {"stock_code", "short_name", "score", "module_scores"} <= set(payload["companies"][0])


def test_api_search_smoke():
    payload = payload_for("/api/search?q=江西")

    assert payload["type"] in {"province", "company", "candidates", "none", "empty"}


def test_api_provinces_smoke():
    payload = payload_for("/api/provinces")

    assert isinstance(payload["provinces"], list)
