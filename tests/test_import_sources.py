import csv
import json
from pathlib import Path

import openpyxl

from backend.app.import_sources import import_all_sources


def write_company_workbook(path: Path) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "结果明细"
    sheet.append(["代码", "简称", "公司名称", "所属行业", "所在地省份", "所在地城市"])
    sheet.append(["600001", "甲能源", "甲能源股份有限公司", "电力", "江西省", "南昌市"])
    workbook.save(path)


def write_ratio_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Stkcd", "ShortName", "Accper", "Typrep", "F010101A", "F010201A", "F011201A"])
        writer.writerow(["股票代码", "股票简称", "统计截止日期", "报表类型编码", "流动比率", "速动比率", "资产负债率"])
        writer.writerow(["没有单位", "没有单位", "没有单位", "没有单位", "没有单位", "没有单位", "没有单位"])
        writer.writerow(["600001", "甲能源", "2024-12-31", "A", "1.2", "0.9", "0.62"])


def write_roe_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ShortName", "Accper", "Typrep", "Source", "ROE"])
        writer.writerow(["600001", "甲能源", "2025/12/31", "A", "0.077348"])


def write_audit_workbook(path: Path) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "sheet1"
    sheet.append(["股票代码", "证券简称", "会计截止日期", "审计日期", "审计意见", "审计师", "境内审计事务所"])
    sheet.append(["600001", "甲能源", "2023-12-31", "2024-03-20", "保留意见", "旧审计师", "旧事务所"])
    sheet.append(["600001", "甲能源", "2024-12-31", "2025-03-20", "标准无保留意见", "张三,李四", "样本会计师事务所"])
    workbook.save(path)


def test_import_all_sources_creates_database_catalog_raw_and_derived_collections(tmp_path):
    source_dir = tmp_path / "source"
    database_dir = tmp_path / "database"
    source_dir.mkdir()
    write_company_workbook(source_dir / "A股主板非ST非金融公司所在地_2026-05-07.xlsx")
    write_ratio_csv(source_dir / "资产负债率、流动比率、速动比率.csv")
    write_roe_csv(source_dir / "ROE.csv")
    write_audit_workbook(source_dir / "审计意见.xlsx")
    (source_dir / "01_国企混改政策文件_2023-2026.md").write_text("# 政策文件\n\n支持混改。", encoding="utf-8")

    summary = import_all_sources(source_dir=source_dir, database_dir=database_dir)

    catalog = json.loads((database_dir / "source_catalog.json").read_text(encoding="utf-8"))
    companies = json.loads((database_dir / "companies.json").read_text(encoding="utf-8"))
    financials = json.loads((database_dir / "financials.json").read_text(encoding="utf-8"))
    equity = json.loads((database_dir / "equity.json").read_text(encoding="utf-8"))
    policies = json.loads((database_dir / "policy_documents.json").read_text(encoding="utf-8"))

    assert summary["source_count"] == 5
    assert len(catalog) == 5
    assert any((database_dir / raw_file).exists() for item in catalog for raw_file in item["raw_files"])
    assert companies[0]["stock_code"] == "600001"
    assert financials[0]["asset_liability_ratio"] == 62.0
    assert financials[0]["roe"] == 7.73
    assert equity[0]["audit_opinion"] == "标准无保留意见"
    assert equity[0]["audit_date"] == "2025-03-20"
    assert equity[0]["domestic_audit_firm"] == "样本会计师事务所"
    assert policies[0]["title"] == "政策文件"
