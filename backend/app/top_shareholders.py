from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TOP_SHAREHOLDER_CSV = PROJECT_ROOT / "data" / "top_shareholders_2025.csv"
TOP_SHAREHOLDER_COLLECTION = "top_shareholders"

FIELD_ALIASES = {
    "stock_code": ["stock_code", "股票代码", "Symbol", "Stkcd", "证券代码"],
    "top_shareholder_date": ["top_shareholder_date", "截止日期", "EndDate", "Accper"],
    "top_shareholder_name": ["top_shareholder_name", "股东名称", "ShareholderName"],
    "top_shareholder_rank": ["top_shareholder_rank", "股东排名", "Rank"],
    "top_shareholder_shares": ["top_shareholder_shares", "持股数量", "SharesHeld"],
    "top_shareholder_ratio": ["top_shareholder_ratio", "持股比例", "ShareholdingRatio"],
    "top_shareholder_share_class": ["top_shareholder_share_class", "股份性质", "ShareClass"],
}


def normalize_stock_code(value: object) -> str:
    if _is_missing(value):
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            return ""
        return str(int(value)).zfill(6)

    text = str(value).strip()
    numeric = re.fullmatch(r"\d+(?:\.0+)?", text)
    if numeric:
        return text.split(".", 1)[0].zfill(6)

    six_digits = re.search(r"\d{6}", text)
    if six_digits:
        return six_digits.group(0)
    digits = re.sub(r"\D+", "", text)
    return digits.zfill(6) if digits else ""


def load_top_shareholders_from_excel(path: Path | str) -> list[dict[str, Any]]:
    frame = pd.read_excel(Path(path), sheet_name=0, dtype=str)
    return _records_from_frame(frame)


def load_top_shareholders_from_csv(path: Path | str = DEFAULT_TOP_SHAREHOLDER_CSV) -> list[dict[str, Any]]:
    frame = pd.read_csv(Path(path), dtype=str)
    return _records_from_frame(frame)


@lru_cache(maxsize=1)
def load_default_top_shareholder_map() -> dict[str, dict[str, Any]]:
    if not DEFAULT_TOP_SHAREHOLDER_CSV.exists():
        return {}
    return top_shareholders_by_stock(load_top_shareholders_from_csv(DEFAULT_TOP_SHAREHOLDER_CSV))


def top_shareholders_by_stock(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(record["stock_code"]): record
        for record in records
        if str(record.get("stock_code", "")).strip()
    }


def apply_top_shareholder_to_equity(
    equity: dict[str, Any] | None,
    shareholder: dict[str, Any] | None,
) -> dict[str, Any]:
    updated = dict(equity or {})
    if not shareholder:
        return updated

    name = shareholder.get("top_shareholder_name", "")
    ratio = shareholder.get("top_shareholder_ratio")
    date = shareholder.get("top_shareholder_date", "")
    shares = shareholder.get("top_shareholder_shares")
    share_class = shareholder.get("top_shareholder_share_class", "")

    updated.update(
        {
            "top_shareholder_name": name,
            "topShareholderName": name,
            "top_shareholder_ratio": ratio,
            "topShareholderRatio": ratio,
            "top_shareholder_date": date,
            "topShareholderDate": date,
            "top_shareholder_shares": shares,
            "topShareholderShares": shares,
            "top_shareholder_share_class": share_class,
            "topShareholderShareClass": share_class,
        }
    )
    return updated


def _records_from_frame(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        record = _record_from_row(row)
        if record["stock_code"]:
            records.append(record)
    return records


def _record_from_row(row: pd.Series) -> dict[str, Any]:
    return {
        "stock_code": normalize_stock_code(_first(row, "stock_code")),
        "top_shareholder_name": _text(_first(row, "top_shareholder_name")),
        "top_shareholder_ratio": _float(_first(row, "top_shareholder_ratio")),
        "top_shareholder_shares": _float(_first(row, "top_shareholder_shares")),
        "top_shareholder_date": _date_text(_first(row, "top_shareholder_date")),
        "top_shareholder_rank": _int(_first(row, "top_shareholder_rank")),
        "top_shareholder_share_class": _text(_first(row, "top_shareholder_share_class")),
    }


def _first(row: pd.Series, canonical: str) -> object:
    for column in FIELD_ALIASES[canonical]:
        if column in row:
            value = row[column]
            if not _is_missing(value):
                return value
    return None


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _text(value: object) -> str:
    return "" if _is_missing(value) else str(value).strip()


def _float(value: object) -> float | None:
    if _is_missing(value):
        return None
    text = str(value).replace(",", "").strip()
    if not text:
        return None
    return float(text)


def _int(value: object) -> int | None:
    numeric = _float(value)
    return int(numeric) if numeric is not None else None


def _date_text(value: object) -> str:
    if _is_missing(value):
        return ""
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return str(value).strip()
    return parsed.strftime("%Y-%m-%d")
