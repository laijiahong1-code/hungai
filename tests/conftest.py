import pytest


@pytest.fixture(autouse=True)
def deterministic_service_scoring(monkeypatch):
    from backend.app import services

    def fake_scoring(stock_code: str) -> dict:
        code = str(stock_code or "0")
        seed = int(code[-2:]) if code[-2:].isdigit() else 0
        finance = round(60.0 + seed % 25, 1)
        equity = round(65.0 + seed % 20, 1)
        region = round(70.0 + seed % 15, 1)
        mixed = round(55.0 + seed % 30, 1)
        modules = {"finance": finance, "equity": equity, "region": region, "mixed": mixed}
        total = round(finance * 0.40 + equity * 0.25 + region * 0.20 + mixed * 0.15, 1)
        return {
            "modules": modules,
            "module_scores": modules.copy(),
            "module_details": {
                key: {"label": label, "evidence": []}
                for key, label in services.MODULE_LABELS.items()
            },
            "raw_scores": {
                "finance": {"score": round(finance / 2, 2), "max": 50.0},
                "equity": {"score": round(equity / 4, 2), "max": 25.0},
                "region": {"score": round(region / 5, 2), "max": 20.0},
                "mixed": {"score": mixed, "max": 100.0},
            },
            "totalScore": total,
            "potentialLevel": "高潜力" if total >= 80 else "中高潜力" if total >= 70 else "观察潜力" if total >= 60 else "低潜力",
            "vetoReasons": [],
        }

    monkeypatch.setattr(services, "get_scoring_result", fake_scoring)
