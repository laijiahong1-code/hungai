import pytest

from backend.app.streamlit_view import (
    company_table_rows,
    module_detail,
    module_score_rows,
    pop_route_history,
    push_route_history,
    reason_items,
    route_snapshot,
)


def sample_company():
    return {
        "code": "600001",
        "stock_code": "600001",
        "shortName": "甲能源",
        "name": "甲能源集团股份有限公司",
        "province": "江西省",
        "industry": "能源",
        "stateAttribute": "国有控股",
        "score": 82.4,
        "totalScore": 82.4,
        "modules": {"finance": 72.0, "equity": 81.0, "region": 90.0, "policy": 86.0},
        "financials": {
            "revenue": 120.5,
            "netProfit": -3.2,
            "assetLiabilityRatio": 74.5,
            "roe": -1.2,
            "cashFlow": 5.6,
        },
        "equity": {
            "topShareholderRatio": 40,
            "pledgeRatio": 12,
            "auditOpinion": "标准无保留意见",
            "overdueDebt": "无逾期",
        },
        "highlights": ["区域政策匹配"],
        "risks": ["资产负债率偏高"],
    }


def test_company_table_rows_keep_streamlit_table_fields_small():
    rows = company_table_rows([sample_company()])

    assert rows == [
        {
            "排名": 1,
            "代码": "600001",
            "公司简称": "甲能源",
            "省份": "江西省",
            "行业": "能源",
            "属性": "国有控股",
            "总分": 82.4,
        }
    ]


def test_module_score_rows_include_labels_weights_and_scores():
    rows = module_score_rows(sample_company())

    assert rows[0] == {"模块": "财务压力", "权重": "30%", "得分": 72.0}
    assert rows[-1] == {"模块": "政策案例", "权重": "20%", "得分": 86.0}


def test_reason_items_returns_empty_fallback():
    assert reason_items([], "暂无风险提示") == ["暂无风险提示"]


def test_module_detail_builds_finance_secondary_page_model():
    detail = module_detail(sample_company(), "finance")

    assert detail["title"] == "财务压力二级页"
    assert detail["score"] == 72.0
    assert detail["weight"] == "30%"
    assert {"指标": "资产负债率", "数值": "74.5%"} in detail["rows"]
    assert detail["notes"] == ["资产负债率偏高"]


def test_module_detail_rejects_unknown_module():
    with pytest.raises(KeyError):
        module_detail(sample_company(), "unknown")


def test_route_history_pushes_current_route_before_navigation():
    current = {
        "page": "company",
        "selected_company_code": "600001",
        "selected_province": "江西省",
        "selected_module": "finance",
    }
    next_route = {**current, "page": "module", "selected_module": "equity"}

    history = push_route_history([], current, next_route)

    assert history == [current]


def test_route_history_does_not_duplicate_same_route():
    current = {
        "page": "company",
        "selected_company_code": "600001",
        "selected_province": "江西省",
        "selected_module": "finance",
    }

    history = push_route_history([], current, current.copy())

    assert history == []


def test_route_history_pops_previous_route():
    first = {"page": "home", "selected_company_code": "", "selected_province": "", "selected_module": "finance"}
    second = {"page": "company", "selected_company_code": "600001", "selected_province": "江西省", "selected_module": "finance"}

    previous, remaining = pop_route_history([first, second])

    assert previous == second
    assert remaining == [first]


def test_route_snapshot_keeps_only_navigation_keys():
    state = {
        "page": "module",
        "selected_company_code": "600001",
        "selected_province": "江西省",
        "selected_module": "policy",
        "other": "ignore",
    }

    assert route_snapshot(state) == {
        "page": "module",
        "selected_company_code": "600001",
        "selected_province": "江西省",
        "selected_module": "policy",
    }
