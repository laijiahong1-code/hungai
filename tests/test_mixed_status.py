from __future__ import annotations

import pytest

from backend.app.mixed_status import (
    company_reform_profile,
    load_status_dashboard,
    load_status_lookup,
)
import streamlit_app


def test_load_status_dashboard_counts_and_thresholds():
    dashboard = load_status_dashboard()

    assert dashboard["total"] == 1810
    assert [
        (item["label"], item["count"], item["percent_label"])
        for item in dashboard["status_slices"]
    ] == [
        ("尚未发生混改", 858, "47.4%"),
        ("正在进行混改", 780, "43.1%"),
        ("已经完成混改", 172, "9.5%"),
    ]
    assert dashboard["completion_threshold"] == pytest.approx(85.14, abs=0.01)
    assert dashboard["mixed_score_median"] == pytest.approx(74.25, abs=0.01)


def test_load_status_dashboard_builds_histogram_and_metric_averages():
    dashboard = load_status_dashboard()

    assert len(dashboard["score_histogram"]) == 12
    assert sum(bin_["count"] for bin_ in dashboard["score_histogram"]) == 952

    by_status = {
        row["status"]: {metric["key"]: metric["value"] for metric in row["metrics"]}
        for row in dashboard["metric_averages"]
    }
    assert by_status["尚未发生混改"]["NSttOwnedShrhlderRatioSum"] == pytest.approx(5.02, abs=0.01)
    assert by_status["正在进行混改"]["MixedOwnershipScore"] == pytest.approx(69.90, abs=0.01)
    assert by_status["已经完成混改"]["MixedOwnershipScore"] == pytest.approx(89.31, abs=0.01)
    assert by_status["已经完成混改"]["EquityStructureDiversity"] == pytest.approx(4.34, abs=0.01)


def test_load_status_dashboard_uses_fixed_annual_summary_percentages():
    dashboard = load_status_dashboard()

    assert dashboard["annual_trends"] == [
        {"year": 2022, "尚未发生混改": 42.7, "正在进行混改": 46.2, "已经完成混改": 11.1},
        {"year": 2023, "尚未发生混改": 45.7, "正在进行混改": 43.8, "已经完成混改": 10.6},
        {"year": 2024, "尚未发生混改": 46.8, "正在进行混改": 43.9, "已经完成混改": 9.2},
        {"year": 2025, "尚未发生混改": 49.4, "正在进行混改": 43.9, "已经完成混改": 6.8},
    ]


def test_mixed_status_dashboard_html_contains_expected_homepage_content():
    dashboard = load_status_dashboard()
    html = streamlit_app.mixed_status_dashboard_html(dashboard)

    assert "国企混改状态观察" in html
    assert "1810" in html
    assert "尚未发生混改" in html
    assert "正在进行混改" in html
    assert "已经完成混改" in html
    assert "858 家 · 47.4%" in html
    assert "780 家 · 43.1%" in html
    assert "172 家 · 9.5%" in html
    assert "完成阈值 85.14" in html


def test_status_lookup_identifies_state_owned_company_reform_status():
    lookup = load_status_lookup()

    profile = company_reform_profile("600183", total_score=87.7, status_lookup=lookup)

    assert profile["isStateOwned"] is True
    assert profile["stateOwnedLabel"] == "是"
    assert profile["mixedStatusLabel"] == "正在进行混改"
    assert profile["source"] == "status_csv"


def test_company_reform_profile_treats_missing_company_as_private_potential():
    profile = company_reform_profile("300750", total_score=60.0, status_lookup={})

    assert profile == {
        "isStateOwned": False,
        "stateOwnedLabel": "否",
        "mixedStatusLabel": "潜在混改企业",
        "source": "private_score_threshold",
    }


def test_company_reform_profile_private_threshold_is_strictly_above_50():
    profile = company_reform_profile("300750", total_score=50.0, status_lookup={})

    assert profile["isStateOwned"] is False
    assert profile["stateOwnedLabel"] == "否"
    assert profile["mixedStatusLabel"] == "尚未发生混改"
    assert profile["source"] == "private_score_threshold"
