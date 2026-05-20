from backend.app import services


def sample_record(stock_code="600001", score_seed=80):
    return {
        "stock_code": stock_code,
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
        "financials": {
            "asset_liability_ratio": score_seed,
            "roe": 3,
            "cash_flow": 2,
            "net_profit": 1,
        },
        "equity": {
            "top_shareholder_ratio": 42,
            "pledge_ratio": 10,
            "audit_opinion": "标准无保留意见",
            "overdue_debt": "无逾期",
        },
        "policy": {
            "regional_fit": 75,
            "policy_signal": 70,
            "positive_reasons": ["符合地方产业方向"],
            "risk_reasons": ["负债率偏高"],
        },
    }


def test_build_company_score_documents_are_public_and_searchable():
    docs = services.build_company_score_documents([sample_record()])

    assert docs[0]["stock_code"] == "600001"
    assert docs[0]["score"] > 0
    assert docs[0]["module_scores"].keys() == {"finance", "equity", "region", "mixed"}
    assert docs[0]["raw_scores"].keys() == {"finance", "equity", "region", "mixed"}
    assert docs[0]["vetoReasons"] == []
    assert "甲能源A" in docs[0]["_search_text"]


def test_build_province_score_documents_group_companies_by_province():
    score_docs = services.build_company_score_documents(
        [
            sample_record("600001", score_seed=80),
            sample_record("600002", score_seed=30),
        ]
    )

    province_docs = services.build_province_score_documents(score_docs)

    assert province_docs[0]["province"] == "江西省"
    assert [company["stock_code"] for company in province_docs[0]["companies"]] == [
        company["stock_code"]
        for company in sorted(score_docs, key=lambda item: (-item["score"], item["stock_code"]))
    ]
    assert "financials" not in province_docs[0]["companies"][0]
    assert {"code", "shortName", "name", "industry", "stateAttribute", "totalScore"} <= set(
        province_docs[0]["companies"][0]
    )


def test_top_companies_can_use_materialized_mongo_collection(monkeypatch):
    docs = services.build_company_score_documents(
        [
            sample_record("600001", score_seed=80),
            sample_record("600002", score_seed=30),
        ]
    )

    class FakeDatabase:
        def has_collection(self, collection):
            return collection == "company_scores"

        def find_query(self, collection, query=None, sort=None, limit=0, projection=None):
            assert collection == "company_scores"
            result = list(docs)
            result.sort(key=lambda item: (-item["score"], item["stock_code"]))
            return result[:limit] if limit else result

        def count_documents(self, collection, query=None):
            return len(docs)

        def distinct(self, collection, key, query=None):
            return sorted({doc[key] for doc in docs})

    monkeypatch.setattr(services, "default_database", lambda: FakeDatabase())
    monkeypatch.setattr(
        services,
        "load_company_records",
        lambda: (_ for _ in ()).throw(AssertionError("should not full-load records")),
    )

    results = services.get_top_companies(limit=1)

    assert len(results) == 1
    assert results[0]["stock_code"] in {"600001", "600002"}


def test_company_detail_supplements_materialized_audit_fields(monkeypatch):
    docs = services.build_company_score_documents([sample_record()])
    docs[0]["equity"]["auditOpinion"] = "待补充"
    docs[0]["equity"]["audit_opinion"] = "待补充"

    class FakeDatabase:
        def has_collection(self, collection):
            return collection == "company_scores"

        def find_query(self, collection, query=None, sort=None, limit=0, projection=None):
            assert collection == "company_scores"
            return docs[:limit] if limit else docs

        def count_documents(self, collection, query=None):
            return 0

        def distinct(self, collection, key, query=None):
            return ["江西省"]

    monkeypatch.setattr(services, "default_database", lambda: FakeDatabase())
    monkeypatch.setattr(
        services,
        "_audit_supplements_by_stock",
        lambda: {
            "600001": {
                "audit_opinion": "标准无保留意见",
                "audit_accounting_date": "2025-12-31",
                "audit_date": "2026-03-20",
                "auditor": "张三,李四",
                "domestic_audit_firm": "样本会计师事务所",
                "overseas_audit_firm": "",
            }
        },
    )

    detail = services.get_company_detail("600001")

    assert detail["equity"]["auditOpinion"] == "标准无保留意见"
    assert detail["equity"]["auditDate"] == "2026-03-20"
    assert detail["equity"]["domesticAuditFirm"] == "样本会计师事务所"


def test_company_detail_supplements_materialized_top_shareholder_fields(monkeypatch):
    docs = services.build_company_score_documents([sample_record()])
    docs[0]["equity"]["topShareholderRatio"] = 40.0
    docs[0]["equity"]["top_shareholder_ratio"] = 40.0

    top_shareholder = {
        "stock_code": "600001",
        "top_shareholder_name": "江西省国有资本运营控股集团有限公司",
        "top_shareholder_ratio": 52.36,
        "top_shareholder_date": "2025-03-31",
        "top_shareholder_shares": 123456789.0,
        "top_shareholder_rank": 1,
        "top_shareholder_share_class": "A股流通股",
    }

    class FakeDatabase:
        def has_collection(self, collection):
            return collection in {"company_scores", "top_shareholders"}

        def find_query(self, collection, query=None, sort=None, limit=0, projection=None):
            if collection == "company_scores":
                return docs[:limit] if limit else docs
            if collection == "top_shareholders":
                return [top_shareholder]
            raise AssertionError(collection)

        def find_one(self, collection, key, value):
            assert collection == "top_shareholders"
            assert key == "stock_code"
            assert value == "600001"
            return top_shareholder

        def count_documents(self, collection, query=None):
            return 0

        def distinct(self, collection, key, query=None):
            return ["江西省"]

    monkeypatch.setattr(services, "default_database", lambda: FakeDatabase())

    detail = services.get_company_detail("600001")

    assert detail["equity"]["topShareholderRatio"] == 52.36
    assert detail["equity"]["topShareholderName"] == "江西省国有资本运营控股集团有限公司"
    assert detail["equity"]["top_shareholder_date"] == "2025-03-31"


def test_company_detail_seeds_top_shareholder_collection_when_mongo_missing(monkeypatch):
    docs = services.build_company_score_documents([sample_record()])
    top_shareholder = {
        "stock_code": "600001",
        "top_shareholder_name": "江西省国有资本运营控股集团有限公司",
        "top_shareholder_ratio": 52.36,
        "top_shareholder_date": "2025-03-31",
        "top_shareholder_shares": 123456789.0,
        "top_shareholder_rank": 1,
        "top_shareholder_share_class": "A股流通股",
    }

    class FakeDatabase:
        def __init__(self):
            self.collections = {"company_scores": docs}
            self.uploaded_count = 0

        def has_collection(self, collection):
            return collection in self.collections

        def replace_all(self, collection, records):
            self.collections[collection] = records
            self.uploaded_count = len(records)

        def find_query(self, collection, query=None, sort=None, limit=0, projection=None):
            records = self.collections[collection]
            return records[:limit] if limit else records

        def find_one(self, collection, key, value):
            for record in self.collections.get(collection, []):
                if record.get(key) == value:
                    return record
            return None

        def count_documents(self, collection, query=None):
            return 0

        def distinct(self, collection, key, query=None):
            return ["江西省"]

    fake_database = FakeDatabase()
    monkeypatch.setattr(services, "default_database", lambda: fake_database)
    monkeypatch.setattr(
        services,
        "_top_shareholder_supplements_by_stock",
        lambda: {"600001": top_shareholder},
    )

    detail = services.get_company_detail("600001")

    assert fake_database.uploaded_count == 1
    assert detail["equity"]["topShareholderRatio"] == 52.36
    assert detail["equity"]["topShareholderName"] == "江西省国有资本运营控股集团有限公司"
