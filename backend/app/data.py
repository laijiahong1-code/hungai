from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
import os
from typing import Any

from .db import JsonDatabase, MongoDatabase


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATABASE_ROOT = BACKEND_ROOT / "database"
DEFAULT_SOURCE_ROOT = Path(r"C:\Users\赖宏\Desktop\公司混改系统")

_DEFAULT_DATABASE: JsonDatabase | MongoDatabase | None = None
_DEFAULT_DATABASE_CONFIG: tuple[str, str, str] | None = None


PROVINCE_ALIASES = {
    "北京": "北京市",
    "北京市": "北京市",
    "上海": "上海市",
    "上海市": "上海市",
    "重庆": "重庆市",
    "重庆市": "重庆市",
    "天津": "天津市",
    "天津市": "天津市",
    "江西": "江西省",
    "江西省": "江西省",
    "山东": "山东省",
    "山东省": "山东省",
    "广东": "广东省",
    "广东省": "广东省",
    "河北": "河北省",
    "河北省": "河北省",
    "云南": "云南省",
    "云南省": "云南省",
    "贵州": "贵州省",
    "贵州省": "贵州省",
    "新疆": "新疆维吾尔自治区",
    "新疆维吾尔自治区": "新疆维吾尔自治区",
}


def default_database() -> JsonDatabase | MongoDatabase:
    global _DEFAULT_DATABASE, _DEFAULT_DATABASE_CONFIG
    mongodb_uri = get_setting("MONGODB_URI")
    database_name = get_setting("MONGODB_DATABASE", "mixed_reform")
    local_root = json_database_root()
    config = (mongodb_uri, database_name, str(local_root))
    if _DEFAULT_DATABASE is not None and _DEFAULT_DATABASE_CONFIG == config:
        return _DEFAULT_DATABASE

    if mongodb_uri:
        _DEFAULT_DATABASE = MongoDatabase(
            uri=mongodb_uri,
            database_name=database_name,
        )
    else:
        _DEFAULT_DATABASE = JsonDatabase(local_root)
    _DEFAULT_DATABASE_CONFIG = config
    return _DEFAULT_DATABASE


def get_setting(name: str, default: str = "") -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    try:
        import streamlit as st
    except Exception:
        return default
    try:
        secret_value = st.secrets.get(name, default)
    except Exception:
        return default
    return str(secret_value).strip() if secret_value else default


def json_database_root() -> Path:
    if (DATABASE_ROOT / "companies.json").exists():
        return DATABASE_ROOT
    source_root = Path(get_setting("MIXED_REFORM_SOURCE_ROOT", str(DEFAULT_SOURCE_ROOT)))
    fallback = source_root / "backend" / "database"
    if (fallback / "companies.json").exists():
        return fallback
    return DATABASE_ROOT


def _by_stock_code(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record.get("stock_code", "")): record for record in records}


def load_company_records(db: JsonDatabase | None = None) -> list[dict[str, Any]]:
    database = db or default_database()
    companies = database.all("companies")
    financials = _by_stock_code(database.all("financials"))
    equity = _by_stock_code(database.all("equity"))
    policies = _by_stock_code(database.all("policies"))

    records = []
    for company in companies:
        stock_code = str(company.get("stock_code", ""))
        records.append(
            {
                **company,
                "aliases": company.get("aliases", []),
                "is_st": bool(company.get("is_st", False)),
                "is_financial": bool(company.get("is_financial", False)),
                "financials": financials.get(stock_code, {}),
                "equity": equity.get(stock_code, {}),
                "policy": policies.get(stock_code, {}),
            }
        )
    return records


class LazyCompanyRecords(Sequence):
    """Compatibility wrapper that avoids loading a database during module import."""

    def __init__(self):
        self._records: list[dict[str, Any]] | None = None

    def _load(self) -> list[dict[str, Any]]:
        if self._records is None:
            self._records = load_company_records()
        return self._records

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self._load())

    def __len__(self) -> int:
        return len(self._load())

    def __getitem__(self, index):
        return self._load()[index]


# Compatibility name used by existing service tests. This is now lazy so the
# HTTP server can start before any remote database query is needed.
SAMPLE_COMPANIES = LazyCompanyRecords()
