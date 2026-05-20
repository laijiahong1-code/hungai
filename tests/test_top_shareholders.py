from pathlib import Path

import pandas as pd

from backend.app.top_shareholders import (
    apply_top_shareholder_to_equity,
    load_top_shareholders_from_csv,
    load_top_shareholders_from_excel,
    top_shareholders_by_stock,
)


def test_load_top_shareholders_from_csv_normalizes_stock_code_and_fields(tmp_path):
    csv_path = tmp_path / "top_shareholders.csv"
    csv_path.write_text(
        "\n".join(
            [
                "stock_code,top_shareholder_name,top_shareholder_ratio,top_shareholder_shares,top_shareholder_date,top_shareholder_rank,top_shareholder_share_class",
                "1,中国平安保险(集团)股份有限公司-集团本级-自有资金,49.56,5200000000,2025-03-31,1,A股流通股",
            ]
        ),
        encoding="utf-8",
    )

    records = load_top_shareholders_from_csv(csv_path)

    assert records == [
        {
            "stock_code": "000001",
            "top_shareholder_name": "中国平安保险(集团)股份有限公司-集团本级-自有资金",
            "top_shareholder_ratio": 49.56,
            "top_shareholder_shares": 5200000000.0,
            "top_shareholder_date": "2025-03-31",
            "top_shareholder_rank": 1,
            "top_shareholder_share_class": "A股流通股",
        }
    ]


def test_load_top_shareholders_from_excel_uses_first_sheet_columns(tmp_path):
    workbook = tmp_path / "top_shareholders.xlsx"
    pd.DataFrame(
        [
            {
                "股票代码": "000002",
                "截止日期": "2025-03-31",
                "股东名称": "深圳市地铁集团有限公司",
                "股东排名": 1,
                "持股数量": 3300000000,
                "持股比例": 27.18,
                "股份性质": "A股流通股",
            }
        ]
    ).to_excel(workbook, index=False)

    records = load_top_shareholders_from_excel(workbook)

    assert records[0]["stock_code"] == "000002"
    assert records[0]["top_shareholder_name"] == "深圳市地铁集团有限公司"
    assert records[0]["top_shareholder_ratio"] == 27.18


def test_top_shareholders_by_stock_and_equity_overlay():
    records = [
        {
            "stock_code": "000002",
            "top_shareholder_name": "深圳市地铁集团有限公司",
            "top_shareholder_ratio": 27.18,
            "top_shareholder_date": "2025-03-31",
            "top_shareholder_shares": 3300000000.0,
            "top_shareholder_rank": 1,
            "top_shareholder_share_class": "A股流通股",
        }
    ]

    by_stock = top_shareholders_by_stock(records)
    equity = apply_top_shareholder_to_equity(
        {"top_shareholder_ratio": 40.0, "pledge_ratio": 12.0},
        by_stock["000002"],
    )

    assert equity["top_shareholder_ratio"] == 27.18
    assert equity["topShareholderRatio"] == 27.18
    assert equity["top_shareholder_name"] == "深圳市地铁集团有限公司"
    assert equity["topShareholderName"] == "深圳市地铁集团有限公司"
    assert equity["topShareholderDate"] == "2025-03-31"
