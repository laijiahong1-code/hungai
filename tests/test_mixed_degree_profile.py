from pathlib import Path

import pytest

from backend.app.scoring.engine import ScoringEngine
from backend.app.scoring.mixed import build_mixed_scores


def test_mixed_scores_prefer_current_a_share_scored_data():
    results = build_mixed_scores(Path("missing-source-root"))

    assert len(results) == 5508
    detail = results["600183"].detail_dict()
    assert detail["score"] == pytest.approx(65.8, abs=0.01)
    assert detail["raw_score"] == pytest.approx(65.85, abs=0.01)
    assert [item["label"] for item in detail["evidence"]] == [
        "非国有资本进入程度",
        "股权结构多样性",
        "股权制衡程度",
        "股权融合程度",
        "股权开放治理程度",
    ]
    assert detail["evidence"][0]["score"] == pytest.approx(21.45, abs=0.01)


def test_scoring_engine_recalculates_total_with_new_mixed_score(tmp_path):
    from tests.test_four_module_scoring import write_source_root

    write_source_root(tmp_path)
    scored = tmp_path / "HLD_current_A_share_mixed_ownership_scored.csv"
    scored.write_text(
        "\n".join(
            [
                "InstitutionID,Symbol,ShortName,EndDate,MixedOwnershipScore,MixedOwnershipLevel,"
                "Score_NonStateCapital,Score_EquityDiversity,Score_EquityBalance,"
                "Score_EquityIntegration,Score_OpenGovernance",
                "1,600001,甲能源,2026-03-31,20.0,初步混改,1,2,3,4,10",
            ]
        ),
        encoding="utf-8-sig",
    )

    result = ScoringEngine(tmp_path).score_company("600001")

    assert result["modules"]["mixed"] == 20.0
    assert result["raw_scores"]["mixed"] == {"score": 20.0, "max": 100.0}
    assert result["totalScore"] == 84.2


def test_build_mixed_degree_profile_from_fixture_data(tmp_path):
    from backend.app.mixed_degree import build_mixed_degree_profile

    scored = tmp_path / "scored.csv"
    scored.write_text(
        "\n".join(
            [
                "Symbol,EndDate,MixedOwnershipScore,MixedOwnershipLevel,Score_NonStateCapital,"
                "Score_EquityDiversity,Score_EquityBalance,Score_EquityIntegration,"
                "Score_OpenGovernance,NSttOwnedShrhlderRatioSum,EquityStructureDiversity,"
                "OwnershipConcentration,state_owned,private_corporate,listed_company,"
                "financial_institution,foreign,natural_person,other",
                "600001,2026-03-31,86.1,高度融合混改,29.8,15.9,15.6,13.1,11.7,"
                "55.0,4,60.0,28.31,30.18,0,3.08,0,0,33.24",
            ]
        ),
        encoding="utf-8-sig",
    )
    shareholders = tmp_path / "shareholders.csv"
    shareholders.write_text(
        "\n".join(
            [
                "stock_code,end_date,rank,shareholder_name,shareholding_ratio,"
                "shareholder_nature,holder_group,holder_group_label",
                "600001,2026-03-31,1,广东德赛集团有限公司,28.31,国有法人,state_owned,国资相关",
                "600001,2026-03-31,2,香港中央结算有限公司,3.08,机构账户,foreign,机构/互联互通",
                "600001,2026-03-31,3,其他前十大股东,33.24,机构/公众股东,other,其他市场主体",
            ]
        ),
        encoding="utf-8-sig",
    )

    profile = build_mixed_degree_profile("600001", scored, shareholders)

    assert profile["score"] == pytest.approx(86.1)
    assert profile["level"] == "高度融合混改"
    assert len(profile["scoreItems"]) == 5
    assert [holder["rank"] for holder in profile["shareholders"]] == [1, 2, 3]
    assert sum(group["percentage"] for group in profile["holderGroups"]) == pytest.approx(100.0, abs=0.02)
    assert "国资参与" in profile["signalTags"]
    assert "股东多元" in profile["signalTags"]


def test_build_mixed_degree_profile_handles_missing_shareholder_rows(tmp_path):
    from backend.app.mixed_degree import build_mixed_degree_profile

    scored = tmp_path / "scored.csv"
    scored.write_text(
        "Symbol,EndDate,MixedOwnershipScore,MixedOwnershipLevel,Score_NonStateCapital,"
        "Score_EquityDiversity,Score_EquityBalance,Score_EquityIntegration,Score_OpenGovernance\n"
        "600001,2026-03-31,40,中度混改,10,10,10,5,5\n",
        encoding="utf-8-sig",
    )

    profile = build_mixed_degree_profile("600001", scored, tmp_path / "missing.csv")

    assert profile["shareholders"] == []
    assert profile["holderGroups"] == []
    assert "暂无股东结构明细" in profile["structureNotes"]
