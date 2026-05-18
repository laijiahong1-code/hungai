from backend.app import services


def active_record():
    return {
        "stock_code": "600001",
        "name": "甲能源集团",
        "short_name": "甲能源",
        "aliases": ["甲能源A"],
        "province": "江西省",
        "city": "南昌市",
        "industry": "能源",
        "controller": "地方国资委",
        "ownership": "国有控股",
        "is_st": False,
        "is_financial": False,
        "financials": {},
        "equity": {},
        "policy": {"positive_reasons": ["区域政策匹配"], "risk_reasons": ["暂无"]},
    }


def fake_scoring(stock_code: str) -> dict:
    assert stock_code == "600001"
    return {
        "modules": {"finance": 90.0, "equity": 80.0, "region": 70.0, "mixed": 60.0},
        "module_scores": {"finance": 90.0, "equity": 80.0, "region": 70.0, "mixed": 60.0},
        "raw_scores": {
            "finance": {"score": 45.0, "max": 50.0},
            "equity": {"score": 20.0, "max": 25.0},
            "region": {"score": 14.0, "max": 20.0},
            "mixed": {"score": 60.0, "max": 100.0},
        },
        "module_details": {
            "finance": {"label": "财务引资潜力", "evidence": []},
            "equity": {"label": "治理合规资质", "evidence": []},
            "region": {"label": "区域国资适配", "evidence": []},
            "mixed": {"label": "混改程度评分", "evidence": []},
        },
        "totalScore": 78.0,
        "potentialLevel": "中高潜力",
        "vetoReasons": [],
    }


def test_company_detail_uses_four_module_scoring_contract(monkeypatch):
    monkeypatch.setattr(services, "get_scoring_result", fake_scoring)

    detail = services.get_company_detail("600001", companies=[active_record()])

    assert detail["modules"] == {"finance": 90.0, "equity": 80.0, "region": 70.0, "mixed": 60.0}
    assert detail["module_scores"] == {"finance": 90.0, "equity": 80.0, "region": 70.0, "mixed": 60.0}
    assert detail["raw_scores"]["finance"] == {"score": 45.0, "max": 50.0}
    assert detail["totalScore"] == 78.0
    assert detail["score"] == 78.0
    assert detail["potentialLevel"] == "中高潜力"
    assert detail["vetoReasons"] == []
    assert "policy" not in detail["modules"]
