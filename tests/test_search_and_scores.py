from backend.app.data import SAMPLE_COMPANIES
from backend.app.services import (
    get_company_detail,
    get_all_provinces,
    get_province_companies,
    get_top_companies,
    search_entities,
)


def company_with_province_alias_in_name():
    return [
        {
            "stock_code": "600001",
            "name": "上海能源股份有限公司",
            "short_name": "上海能源",
            "aliases": ["上海能源"],
            "province": "上海市",
            "city": "上海市",
            "industry": "能源",
            "controller": "待补充",
            "ownership": "国有控股",
            "is_st": False,
            "is_financial": False,
            "financials": {},
            "equity": {},
            "policy": {},
        },
        {
            "stock_code": "600002",
            "name": "上海样本制造股份有限公司",
            "short_name": "上海样本",
            "aliases": [],
            "province": "上海市",
            "city": "上海市",
            "industry": "制造业",
            "controller": "待补充",
            "ownership": "国有控股",
            "is_st": False,
            "is_financial": False,
            "financials": {},
            "equity": {},
            "policy": {},
        },
    ]


def test_top_companies_excludes_st_and_financial_and_sorts_by_score():
    results = get_top_companies(limit=20, companies=SAMPLE_COMPANIES)

    assert all(not company["is_st"] for company in results)
    assert all(not company["is_financial"] for company in results)
    assert [company["score"] for company in results] == sorted(
        [company["score"] for company in results], reverse=True
    )


def test_search_identifies_company_by_stock_code_and_name():
    by_code = search_entities("600519", companies=SAMPLE_COMPANIES)
    by_name = search_entities("白云机场", companies=SAMPLE_COMPANIES)

    assert by_code["type"] == "company"
    assert by_code["company"]["stock_code"] == "600519"
    assert by_name["type"] == "company"
    assert by_name["company"]["stock_code"] == "600004"


def test_search_prioritizes_exact_company_before_province_alias():
    result = search_entities("上海能源", companies=company_with_province_alias_in_name())

    assert result["type"] == "company"
    assert result["company"]["stock_code"] == "600001"


def test_search_falls_back_to_province_when_no_exact_company_match():
    result = search_entities("上海", companies=company_with_province_alias_in_name())

    assert result["type"] == "province"
    assert result["province"] == "上海市"
    assert result["count"] == 2


def test_search_identifies_province_before_fuzzy_company_candidates():
    result = search_entities("江西", companies=SAMPLE_COMPANIES)

    assert result["type"] == "province"
    assert result["province"] == "江西省"
    assert result["count"] >= 2


def test_search_returns_ranked_candidates_for_ambiguous_terms():
    result = search_entities("能源", companies=SAMPLE_COMPANIES)

    assert result["type"] == "candidates"
    assert len(result["companies"]) >= 2
    assert [company["score"] for company in result["companies"]] == sorted(
        [company["score"] for company in result["companies"]], reverse=True
    )


def test_province_companies_are_filtered_and_ranked():
    results = get_province_companies("江西省", companies=SAMPLE_COMPANIES)

    assert len(results) >= 2
    assert all(company["province"] == "江西省" for company in results)
    assert all(not company["is_st"] and not company["is_financial"] for company in results)
    assert [company["score"] for company in results] == sorted(
        [company["score"] for company in results], reverse=True
    )


def test_company_detail_contains_rank_scores_and_reason_panels():
    detail = get_company_detail("600004", companies=SAMPLE_COMPANIES)

    assert detail["stock_code"] == "600004"
    assert detail["national_rank"] > 0
    assert detail["province_rank"] > 0
    assert set(detail["module_scores"]) == {"financial", "equity", "regional", "policy"}
    assert detail["positive_reasons"]
    assert detail["risk_reasons"]


def test_all_provinces_only_includes_active_company_pool():
    provinces = get_all_provinces(companies=SAMPLE_COMPANIES)

    assert "江西省" in provinces
    assert provinces == sorted(provinces)
    assert "北京市" in provinces
