import pytest

from backend.app.streamlit_view import (
    company_report_summary,
    company_table_rows,
    module_detail,
    module_cards,
    module_score_rows,
    pop_route_history,
    push_route_history,
    reason_items,
    route_snapshot,
    score_band,
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
            "roi": 2.7,
            "cashFlow": 5.6,
        },
        "equity": {
            "topShareholderRatio": 40,
            "pledgeRatio": 12,
            "auditOpinion": "标准无保留意见",
            "auditAccountingDate": "2024-12-31",
            "auditDate": "2025-03-20",
            "auditor": "张三,李四",
            "domesticAuditFirm": "样本会计师事务所",
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


def test_score_band_maps_scores_to_report_statuses():
    assert score_band(85)["label"] == "优势项"
    assert score_band(75)["label"] == "支撑项"
    assert score_band(65)["label"] == "观察项"
    assert score_band(55)["label"] == "风险项"


def test_company_report_summary_names_best_and_weakest_modules():
    summary = company_report_summary(sample_company())

    assert "甲能源综合得分82.4" in summary
    assert "优势项" in summary
    assert "属地适配贡献最强" in summary
    assert "财务压力仍需重点观察" in summary


def test_module_cards_include_status_and_explanatory_copy():
    cards = module_cards(sample_company())

    assert len(cards) == 4
    assert cards[0]["key"] == "finance"
    assert cards[0]["band_label"] == "支撑项"
    assert "盈利、负债率、现金流" in cards[0]["summary"]
    assert cards[2]["key"] == "region"
    assert cards[2]["band_label"] == "优势项"


def test_reason_items_returns_empty_fallback():
    assert reason_items([], "暂无风险提示") == ["暂无风险提示"]


def test_module_detail_builds_finance_secondary_page_model():
    detail = module_detail(sample_company(), "finance")

    assert detail["title"] == "财务压力二级页"
    assert detail["score"] == 72.0
    assert detail["weight"] == "30%"
    assert detail["band_label"] == "支撑项"
    assert "财务压力得分72.0" in detail["report_summary"]
    assert "盈利、负债率、现金流" in detail["report_summary"]
    assert {"指标": "资产负债率", "数值": "74.5%"} in detail["rows"]
    assert {"指标": "ROI", "数值": "2.7%"} in detail["rows"]
    assert detail["notes"] == ["资产负债率偏高"]


def test_module_detail_builds_equity_audit_rows():
    detail = module_detail(sample_company(), "equity")

    assert {"指标": "审计意见", "数值": "标准无保留意见"} in detail["rows"]
    assert {"指标": "审计日期", "数值": "2025-03-20"} in detail["rows"]
    assert {"指标": "境内审计事务所", "数值": "样本会计师事务所"} in detail["rows"]
    assert {"指标": "签字审计师", "数值": "张三,李四"} in detail["rows"]


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
