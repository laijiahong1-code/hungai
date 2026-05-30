import pandas as pd

from scripts.generate_region_heatmap import aggregate_industry_scores, province_short_name


def test_province_short_name_maps_full_names_for_china_map():
    assert province_short_name("广东省") == "广东"
    assert province_short_name("内蒙古自治区") == "内蒙古"
    assert province_short_name("新疆维吾尔自治区") == "新疆"
    assert province_short_name("北京市") == "北京"


def test_aggregate_industry_scores_groups_by_province_mean():
    frame = pd.DataFrame(
        [
            {"所在地省份": "广东省", "产业匹配度得分": 4},
            {"所在地省份": "广东省", "产业匹配度得分": 2},
            {"所在地省份": "北京市", "产业匹配度得分": 0},
        ]
    )

    assert aggregate_industry_scores(frame) == [("北京", 0.0), ("广东", 3.0)]
