from pathlib import Path

from backend.app.data import load_company_records
from backend.app.db import JsonDatabase
from backend.app.services import get_company_detail, get_top_companies, search_entities


def seed_database(root: Path) -> JsonDatabase:
    db = JsonDatabase(root)
    db.replace_all(
        "companies",
        [
            {
                "stock_code": "600001",
                "name": "甲能源股份有限公司",
                "short_name": "甲能源",
                "aliases": ["甲能"],
                "province": "江西省",
                "city": "南昌市",
                "industry": "电力",
                "controller": "江西省国资委",
                "ownership": "地方国资控股",
                "is_st": False,
                "is_financial": False,
            },
            {
                "stock_code": "600002",
                "name": "乙装备股份有限公司",
                "short_name": "乙装备",
                "aliases": ["乙装"],
                "province": "广东省",
                "city": "深圳市",
                "industry": "高端装备",
                "controller": "广东省国资委",
                "ownership": "地方国资控股",
                "is_st": False,
                "is_financial": False,
            },
        ],
    )
    db.replace_all(
        "financials",
        [
            {
                "stock_code": "600001",
                "revenue": 120.5,
                "net_profit": 8.4,
                "asset_liability_ratio": 68.0,
                "roe": 6.8,
                "roi": 5.4,
                "cash_flow": 18.6,
            },
            {
                "stock_code": "600002",
                "revenue": 80.0,
                "net_profit": 3.1,
                "asset_liability_ratio": 45.0,
                "roe": 4.2,
                "cash_flow": 9.3,
            },
        ],
    )
    db.replace_all(
        "equity",
        [
            {
                "stock_code": "600001",
                "top_shareholder_ratio": 42.5,
                "pledge_ratio": 8.4,
                "audit_opinion": "标准无保留意见",
                "overdue_debt": "无逾期",
            },
            {
                "stock_code": "600002",
                "top_shareholder_ratio": 34.0,
                "pledge_ratio": 45.0,
                "audit_opinion": "带强调事项的无保留意见",
                "overdue_debt": "存在少量逾期",
            },
        ],
    )
    db.replace_all(
        "policies",
        [
            {
                "stock_code": "600001",
                "regional_fit": 88,
                "policy_signal": 76,
                "positive_reasons": ["省内平台清晰", "产业链支持度高"],
                "risk_reasons": ["煤价波动"],
            },
            {
                "stock_code": "600002",
                "regional_fit": 80,
                "policy_signal": 70,
                "positive_reasons": ["产业协同明确"],
                "risk_reasons": ["订单波动"],
            },
        ],
    )
    return db


def test_json_database_can_store_update_and_find_records(tmp_path):
    db = JsonDatabase(tmp_path)

    db.insert("companies", {"stock_code": "600001", "name": "甲能源股份有限公司"})
    db.upsert("companies", "stock_code", {"stock_code": "600001", "name": "甲能源集团"})

    assert db.find_one("companies", "stock_code", "600001")["name"] == "甲能源集团"
    assert db.all("companies") == [{"stock_code": "600001", "name": "甲能源集团"}]


def test_company_records_are_joined_from_database_collections(tmp_path):
    db = seed_database(tmp_path)

    records = load_company_records(db)

    assert records[0]["stock_code"] == "600001"
    assert records[0]["financials"]["asset_liability_ratio"] == 68.0
    assert records[0]["financials"]["roi"] == 5.4
    assert records[0]["equity"]["pledge_ratio"] == 8.4
    assert records[0]["policy"]["positive_reasons"] == ["省内平台清晰", "产业链支持度高"]


def test_services_search_database_records_and_compute_scores(tmp_path):
    db = seed_database(tmp_path)
    records = load_company_records(db)

    search = search_entities("甲能", records=records)
    detail = get_company_detail("600001", records=records)
    top = get_top_companies(limit=2, records=records)

    assert search["type"] == "company"
    assert detail["data_status"] == "json_database"
    assert detail["financials"]["revenue"] == 120.5
    assert detail["financials"]["roi"] == 5.4
    assert detail["equity"]["pledgeRatio"] == 8.4
    assert detail["module_scores"]["financial"] > 0
    assert [item["stock_code"] for item in top] == ["600001", "600002"]
