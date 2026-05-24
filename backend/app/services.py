from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

from .data import BACKEND_ROOT, PROVINCE_ALIASES, default_database, load_company_records
from .import_sources import latest_audit_by_stock, latest_roe_by_stock
from .mixed_degree import mixed_degree_profiles_by_stock
from .mixed_status import company_reform_profile, load_status_lookup
from .scoring import get_scoring_result
from .top_shareholders import (
    TOP_SHAREHOLDER_COLLECTION,
    apply_top_shareholder_to_equity,
    load_default_top_shareholder_map,
)


SCORE_COLLECTION = "company_scores"
PROVINCE_SCORE_COLLECTION = "province_company_scores"


MODULE_LABELS = {
    "finance": "财务引资潜力",
    "equity": "治理合规资质",
    "region": "区域国资适配",
    "mixed": "混改程度评分",
}

MODULE_WEIGHTS = {
    "finance": 0.40,
    "equity": 0.25,
    "region": 0.20,
    "mixed": 0.15,
}


def _resolve_records(
    records: Iterable[dict] | None = None, companies: Iterable[dict] | None = None
) -> list[dict]:
    if records is not None:
        return list(records)
    if companies is not None:
        return list(companies)
    return load_company_records()


def _materialized_database():
    database = default_database()
    if not all(
        hasattr(database, method)
        for method in ("has_collection", "find_query", "count_documents", "distinct")
    ):
        return None
    if not database.has_collection(SCORE_COLLECTION):
        return None
    return database


def _can_use_materialized(
    records: Iterable[dict] | None = None, companies: Iterable[dict] | None = None
) -> bool:
    return records is None and companies is None


def _active_query(extra: dict | None = None) -> dict:
    query = {"is_st": {"$ne": True}, "is_financial": {"$ne": True}}
    if extra:
        query.update(extra)
    return query


def _clean_scored_doc(record: dict) -> dict:
    public = record.copy()
    public.pop("_id", None)
    public.pop("_search_text", None)
    return public


def _company_list_summary(record: dict) -> dict:
    public = _clean_scored_doc(record)
    return {
        key: public.get(key)
        for key in [
            "code",
            "stock_code",
            "name",
            "shortName",
            "short_name",
            "industry",
            "stateAttribute",
            "totalScore",
            "score",
        ]
    }


def _score_sort() -> list[tuple[str, int]]:
    return [("score", -1), ("stock_code", 1)]


def _query_text(value: str) -> str:
    return value.strip().lower()


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_score(value: object) -> float:
    return round(min(100.0, max(0.0, _number(value))), 1)


def _financial_score(record: dict) -> float:
    financials = record.get("financials", {})
    debt = _number(financials.get("asset_liability_ratio"))
    roe = _number(financials.get("roe"))
    cash_flow = _number(financials.get("cash_flow"))
    net_profit = _number(financials.get("net_profit"))

    debt_component = _clamp_score(debt)
    profit_component = 85.0 if net_profit < 0 else _clamp_score(70 - roe * 2)
    cash_component = 85.0 if cash_flow < 0 else _clamp_score(70 - min(cash_flow, 80) * 0.5)
    return round(debt_component * 0.45 + profit_component * 0.30 + cash_component * 0.25, 1)


def _equity_score(record: dict) -> float:
    equity = record.get("equity", {})
    top_shareholder = _number(equity.get("top_shareholder_ratio"))
    pledge = _number(equity.get("pledge_ratio"))
    audit_opinion = str(equity.get("audit_opinion", ""))
    overdue_debt = str(equity.get("overdue_debt", ""))

    shareholder_balance = _clamp_score(100 - abs(top_shareholder - 40) * 1.2)
    pledge_health = _clamp_score(90 - pledge * 0.7)
    penalty = 0.0
    if audit_opinion and audit_opinion != "标准无保留意见":
        penalty += 15.0
    if overdue_debt and overdue_debt != "无逾期":
        penalty += 15.0
    return _clamp_score(shareholder_balance * 0.45 + pledge_health * 0.55 - penalty)


def _policy_number(record: dict, key: str) -> float:
    return _clamp_score(record.get("policy", {}).get(key, 0))


def _module_scores(record: dict) -> dict[str, float]:
    return get_scoring_result(record.get("stock_code", ""))["module_scores"]


def _total_score(record: dict) -> float:
    return round(float(get_scoring_result(record.get("stock_code", ""))["totalScore"]), 1)


def _active_records(records: Iterable[dict]) -> list[dict]:
    return [
        record
        for record in records
        if not record.get("is_st") and not record.get("is_financial")
    ]


def _score_key(record: dict) -> tuple[float, str]:
    return (-_total_score(record), record.get("stock_code", ""))


def _public_company(record: dict) -> dict:
    scoring = get_scoring_result(record.get("stock_code", ""))
    modules = scoring["modules"]
    score = scoring["totalScore"]
    financials = record.get("financials", {})
    equity = apply_top_shareholder_to_equity(
        record.get("equity", {}),
        _top_shareholder_supplements_by_stock().get(str(record.get("stock_code", ""))),
    )
    policy = record.get("policy", {})
    positive_reasons = policy.get("positive_reasons", [])
    risk_reasons = policy.get("risk_reasons", [])

    return {
        "stock_code": record["stock_code"],
        "code": record["stock_code"],
        "name": record["name"],
        "short_name": record["short_name"],
        "shortName": record["short_name"],
        "province": record["province"],
        "city": record["city"],
        "industry": record["industry"],
        "controller": record["controller"],
        "ownership": record["ownership"],
        "stateAttribute": record["ownership"],
        "score": score,
        "totalScore": score,
        "module_scores": scoring["module_scores"],
        "modules": modules,
        "module_details": scoring["module_details"],
        "raw_scores": scoring["raw_scores"],
        "governanceTrend": scoring.get("governanceTrend", []),
        "potentialLevel": scoring["potentialLevel"],
        "reformProfile": company_reform_profile(
            record.get("stock_code", ""),
            score,
            _reform_status_lookup_by_stock(),
        ),
        "mixedDegreeProfile": _mixed_degree_profiles_by_stock().get(str(record.get("stock_code", "")).zfill(6), {}),
        "vetoReasons": scoring["vetoReasons"],
        "positive_reasons": positive_reasons,
        "highlights": positive_reasons,
        "risk_reasons": risk_reasons,
        "risks": risk_reasons,
        "financials": {
            "revenue": financials.get("revenue", 0),
            "netProfit": financials.get("net_profit", 0),
            "assetLiabilityRatio": financials.get("asset_liability_ratio", 0),
            "roe": financials.get("roe", 0),
            "roeAccper": financials.get("roe_accper", ""),
            "roi": financials.get("roi", 0),
            "cashFlow": financials.get("cash_flow", 0),
            "net_profit": financials.get("net_profit", 0),
            "asset_liability_ratio": financials.get("asset_liability_ratio", 0),
            "roe_accper": financials.get("roe_accper", ""),
            "return_on_investment": financials.get("roi", 0),
            "cash_flow": financials.get("cash_flow", 0),
        },
        "equity": {
            "topShareholderName": equity.get("top_shareholder_name", ""),
            "topShareholderRatio": equity.get("top_shareholder_ratio", 0),
            "topShareholderDate": equity.get("top_shareholder_date", ""),
            "topShareholderShares": equity.get("top_shareholder_shares"),
            "topShareholderShareClass": equity.get("top_shareholder_share_class", ""),
            "pledgeRatio": equity.get("pledge_ratio", 0),
            "auditOpinion": equity.get("audit_opinion", ""),
            "auditAccountingDate": equity.get("audit_accounting_date", ""),
            "auditDate": equity.get("audit_date", ""),
            "auditor": equity.get("auditor", ""),
            "domesticAuditFirm": equity.get("domestic_audit_firm", ""),
            "overseasAuditFirm": equity.get("overseas_audit_firm", ""),
            "overdueDebt": equity.get("overdue_debt", ""),
            "top_shareholder_name": equity.get("top_shareholder_name", ""),
            "top_shareholder_ratio": equity.get("top_shareholder_ratio", 0),
            "top_shareholder_date": equity.get("top_shareholder_date", ""),
            "top_shareholder_shares": equity.get("top_shareholder_shares"),
            "top_shareholder_share_class": equity.get("top_shareholder_share_class", ""),
            "pledge_ratio": equity.get("pledge_ratio", 0),
            "audit_opinion": equity.get("audit_opinion", ""),
            "audit_accounting_date": equity.get("audit_accounting_date", ""),
            "audit_date": equity.get("audit_date", ""),
            "auditor": equity.get("auditor", ""),
            "domestic_audit_firm": equity.get("domestic_audit_firm", ""),
            "overseas_audit_firm": equity.get("overseas_audit_firm", ""),
            "overdue_debt": equity.get("overdue_debt", ""),
        },
        "is_st": record.get("is_st", False),
        "is_financial": record.get("is_financial", False),
    }


def _missing_text(value: object) -> bool:
    text = str(value if value is not None else "").strip()
    return text == "" or text in {"待补充", "暂未入库", "None", "nan", "NaN"}


@lru_cache(maxsize=1)
def _audit_supplements_by_stock() -> dict[str, dict[str, str]]:
    return latest_audit_by_stock(BACKEND_ROOT)


@lru_cache(maxsize=1)
def _roe_supplements_by_stock() -> dict[str, dict[str, object]]:
    return latest_roe_by_stock(BACKEND_ROOT)


@lru_cache(maxsize=1)
def _top_shareholder_supplements_by_stock() -> dict[str, dict[str, object]]:
    return load_default_top_shareholder_map()


@lru_cache(maxsize=1)
def _reform_status_lookup_by_stock() -> dict[str, dict[str, object]]:
    return load_status_lookup()


@lru_cache(maxsize=1)
def _mixed_degree_profiles_by_stock() -> dict[str, dict[str, object]]:
    return mixed_degree_profiles_by_stock()


def _seed_top_shareholder_collection(database: object) -> bool:
    if not hasattr(database, "replace_all"):
        return False
    records = list(_top_shareholder_supplements_by_stock().values())
    if not records:
        return False
    try:
        database.replace_all(TOP_SHAREHOLDER_COLLECTION, records)
    except Exception:
        return False
    return True


def ensure_top_shareholder_collection_seeded() -> bool:
    try:
        database = default_database()
        if not hasattr(database, "has_collection"):
            return False
        if database.has_collection(TOP_SHAREHOLDER_COLLECTION):
            return False
        return _seed_top_shareholder_collection(database)
    except Exception:
        return False


def _top_shareholder_from_database(stock_code: str) -> dict[str, object] | None:
    try:
        database = default_database()
        if not hasattr(database, "has_collection"):
            return None
        if not database.has_collection(TOP_SHAREHOLDER_COLLECTION):
            if not _seed_top_shareholder_collection(database):
                return None
        if hasattr(database, "find_one"):
            return database.find_one(TOP_SHAREHOLDER_COLLECTION, "stock_code", stock_code)
        if hasattr(database, "find_query"):
            rows = database.find_query(
                TOP_SHAREHOLDER_COLLECTION,
                {"stock_code": stock_code},
                limit=1,
            )
            return rows[0] if rows else None
    except Exception:
        return None
    return None


def _apply_top_shareholder_supplement(detail: dict) -> dict:
    stock_code = str(detail.get("stock_code") or detail.get("code") or "")
    shareholder = _top_shareholder_from_database(stock_code)
    if shareholder is None:
        shareholder = _top_shareholder_supplements_by_stock().get(stock_code)
    if not shareholder:
        return detail
    detail["equity"] = apply_top_shareholder_to_equity(
        detail.get("equity", {}),
        shareholder,
    )
    return detail


def _apply_reform_profile_supplement(detail: dict) -> dict:
    stock_code = str(detail.get("stock_code") or detail.get("code") or "")
    total_score = detail.get("totalScore", detail.get("score", 0))
    detail["reformProfile"] = company_reform_profile(
        stock_code,
        total_score,
        _reform_status_lookup_by_stock(),
    )
    return detail


def _apply_mixed_degree_profile_supplement(detail: dict) -> dict:
    stock_code = str(detail.get("stock_code") or detail.get("code") or "").zfill(6)
    if not detail.get("mixedDegreeProfile"):
        detail["mixedDegreeProfile"] = _mixed_degree_profiles_by_stock().get(stock_code, {})
    return detail


def _apply_audit_supplement(detail: dict) -> dict:
    stock_code = str(detail.get("stock_code") or detail.get("code") or "")
    audit = _audit_supplements_by_stock().get(stock_code)
    if not audit:
        return detail

    equity = detail.setdefault("equity", {})
    fields = [
        ("auditOpinion", "audit_opinion"),
        ("auditAccountingDate", "audit_accounting_date"),
        ("auditDate", "audit_date"),
        ("auditor", "auditor"),
        ("domesticAuditFirm", "domestic_audit_firm"),
        ("overseasAuditFirm", "overseas_audit_firm"),
    ]
    for public_key, source_key in fields:
        if _missing_text(equity.get(public_key)):
            equity[public_key] = audit.get(source_key, "")
        if _missing_text(equity.get(source_key)):
            equity[source_key] = audit.get(source_key, "")
    return detail


def _apply_roe_supplement(detail: dict) -> dict:
    stock_code = str(detail.get("stock_code") or detail.get("code") or "")
    roe_row = _roe_supplements_by_stock().get(stock_code)
    if not roe_row:
        return detail
    financials = detail.setdefault("financials", {})
    financials["roe"] = roe_row.get("roe", 0)
    financials["roeAccper"] = roe_row.get("roe_accper", "")
    financials["roe_accper"] = roe_row.get("roe_accper", "")
    return detail


def _apply_detail_supplements(detail: dict) -> dict:
    detail = _apply_reform_profile_supplement(detail)
    detail = _apply_mixed_degree_profile_supplement(detail)
    detail = _apply_top_shareholder_supplement(detail)
    detail = _apply_roe_supplement(detail)
    return _apply_audit_supplement(detail)


def build_company_score_documents(records: Iterable[dict]) -> list[dict]:
    documents = []
    for record in _active_records(records):
        document = _public_company(record)
        search_terms = [
            record.get("stock_code", ""),
            record.get("name", ""),
            record.get("short_name", ""),
            record.get("province", ""),
            record.get("city", ""),
            record.get("industry", ""),
            record.get("controller", ""),
            *record.get("aliases", []),
        ]
        document["_search_text"] = " ".join(str(term) for term in search_terms if term)
        documents.append(document)
    return documents


def build_province_score_documents(score_documents: Iterable[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for document in score_documents:
        province = document.get("province")
        if not province:
            continue
        grouped.setdefault(province, []).append(_company_list_summary(document))
    return [
        {
            "province": province,
            "companies": sorted(companies, key=lambda item: (-item["score"], item["stock_code"])),
        }
        for province, companies in sorted(grouped.items())
    ]


def get_top_companies(
    limit: int = 10,
    records: Iterable[dict] | None = None,
    companies: Iterable[dict] | None = None,
) -> list[dict]:
    if _can_use_materialized(records, companies):
        database = _materialized_database()
        if database is not None:
            return [
                _clean_scored_doc(record)
                for record in database.find_query(
                    SCORE_COLLECTION,
                    _active_query(),
                    sort=_score_sort(),
                    limit=limit,
                )
            ]

    ranked = sorted(_active_records(_resolve_records(records, companies)), key=_score_key)
    return [_public_company(record) for record in ranked[:limit]]


def get_province_companies(
    province: str,
    records: Iterable[dict] | None = None,
    companies: Iterable[dict] | None = None,
) -> list[dict]:
    normalized = normalize_province(province)
    if _can_use_materialized(records, companies):
        database = _materialized_database()
        if database is not None:
            if database.has_collection(PROVINCE_SCORE_COLLECTION):
                documents = database.find_query(
                    PROVINCE_SCORE_COLLECTION,
                    {"province": normalized},
                    limit=1,
                )
                return documents[0].get("companies", []) if documents else []
            return [
                _clean_scored_doc(record)
                for record in database.find_query(
                    SCORE_COLLECTION,
                    _active_query({"province": normalized}),
                    sort=_score_sort(),
                )
            ]

    ranked = [
        record
        for record in _active_records(_resolve_records(records, companies))
        if record.get("province") == normalized
    ]
    return [_public_company(record) for record in sorted(ranked, key=_score_key)]


def get_all_provinces(
    records: Iterable[dict] | None = None, companies: Iterable[dict] | None = None
) -> list[str]:
    if _can_use_materialized(records, companies):
        database = _materialized_database()
        if database is not None:
            return sorted(
                province
                for province in database.distinct(SCORE_COLLECTION, "province", _active_query())
                if province
            )

    return sorted(
        {record["province"] for record in _active_records(_resolve_records(records, companies))}
    )


def get_company_detail(
    stock_code: str,
    records: Iterable[dict] | None = None,
    companies: Iterable[dict] | None = None,
) -> dict:
    if _can_use_materialized(records, companies):
        database = _materialized_database()
        if database is not None:
            record = database.find_query(
                SCORE_COLLECTION,
                _active_query({"stock_code": stock_code}),
                limit=1,
            )
            if not record:
                raise KeyError(stock_code)
            detail = _clean_scored_doc(record[0])
            rank_query = _active_query(
                {
                    "$or": [
                        {"score": {"$gt": detail["score"]}},
                        {"score": detail["score"], "stock_code": {"$lt": stock_code}},
                    ]
                }
            )
            province_rank_query = _active_query(
                {
                    "province": detail["province"],
                    "$or": [
                        {"score": {"$gt": detail["score"]}},
                        {"score": detail["score"], "stock_code": {"$lt": stock_code}},
                    ],
                }
            )
            detail["national_rank"] = (
                database.count_documents(SCORE_COLLECTION, rank_query) + 1
            )
            detail["province_rank"] = (
                database.count_documents(SCORE_COLLECTION, province_rank_query) + 1
            )
            detail["module_labels"] = MODULE_LABELS
            detail["module_weights"] = MODULE_WEIGHTS
            detail["data_status"] = "mongodb"
            return _apply_detail_supplements(detail)

    active = sorted(_active_records(_resolve_records(records, companies)), key=_score_key)
    by_code = {record["stock_code"]: record for record in active}
    record = by_code.get(stock_code)
    if record is None:
        raise KeyError(stock_code)

    province_ranked = [
        item for item in active if item.get("province") == record.get("province")
    ]
    detail = _public_company(record)
    detail["national_rank"] = active.index(record) + 1
    detail["province_rank"] = province_ranked.index(record) + 1
    detail["module_labels"] = MODULE_LABELS
    detail["module_weights"] = MODULE_WEIGHTS
    detail["data_status"] = "json_database"
    return _apply_detail_supplements(detail)


def normalize_province(query: str) -> str | None:
    text = query.strip()
    if text in PROVINCE_ALIASES:
        return PROVINCE_ALIASES[text]
    for alias, province in PROVINCE_ALIASES.items():
        if alias and alias in text:
            return province
    return None


def _company_search_score(query: str, record: dict) -> int:
    fields = [
        record.get("stock_code", ""),
        record.get("name", ""),
        record.get("short_name", ""),
        *record.get("aliases", []),
    ]
    lowered = _query_text(query)
    for field in fields:
        if lowered == _query_text(field):
            return 100
    for field in fields:
        if lowered and lowered in _query_text(field):
            return 70
    return 0


def search_entities(
    query: str,
    records: Iterable[dict] | None = None,
    companies: Iterable[dict] | None = None,
) -> dict:
    text = query.strip()
    if not text:
        return {"type": "empty", "companies": []}

    if _can_use_materialized(records, companies):
        database = _materialized_database()
        if database is not None:
            exact_query = _active_query(
                {
                    "$or": [
                        {"stock_code": text},
                        {"name": text},
                        {"short_name": text},
                        {"aliases": text},
                    ]
                }
            )
            exact_matches = database.find_query(
                SCORE_COLLECTION, exact_query, sort=_score_sort(), limit=9
            )
            if len(exact_matches) == 1:
                return {"type": "company", "company": _clean_scored_doc(exact_matches[0])}
            if len(exact_matches) > 1:
                return {
                    "type": "candidates",
                    "companies": [_clean_scored_doc(record) for record in exact_matches[:8]],
                }

            province = normalize_province(text)
            if province:
                if database.has_collection(PROVINCE_SCORE_COLLECTION):
                    documents = database.find_query(
                        PROVINCE_SCORE_COLLECTION,
                        {"province": province},
                        limit=1,
                    )
                    count = len(documents[0].get("companies", [])) if documents else 0
                    return {"type": "province", "province": province, "count": count}
                return {
                    "type": "province",
                    "province": province,
                    "count": database.count_documents(
                        SCORE_COLLECTION, _active_query({"province": province})
                    ),
                }

            candidates = database.find_query(
                SCORE_COLLECTION,
                _active_query({"_search_text": {"$regex": re.escape(text), "$options": "i"}}),
                sort=_score_sort(),
                limit=8,
            )
            if not candidates:
                return {"type": "none", "companies": []}
            if len(candidates) == 1:
                return {"type": "company", "company": _clean_scored_doc(candidates[0])}
            return {
                "type": "candidates",
                "companies": [_clean_scored_doc(record) for record in candidates],
            }

    current_records = _resolve_records(records, companies)
    matches = []
    for record in _active_records(current_records):
        score = _company_search_score(text, record)
        if score:
            matches.append((score, record))

    matches.sort(key=lambda item: (-item[0], item[1].get("short_name", "")))
    exact_matches = [record for score, record in matches if score == 100]
    if len(exact_matches) == 1:
        return {"type": "company", "company": _public_company(exact_matches[0])}
    if len(exact_matches) > 1:
        exact_matches.sort(key=_score_key)
        return {
            "type": "candidates",
            "companies": [_public_company(record) for record in exact_matches[:8]],
        }

    province = normalize_province(text)
    if province:
        return {
            "type": "province",
            "province": province,
            "count": len(get_province_companies(province, records=current_records)),
        }

    if not matches:
        return {"type": "none", "companies": []}

    candidates = [record for _, record in matches]
    candidates.sort(key=_score_key)
    if len(candidates) == 1:
        return {"type": "company", "company": _public_company(candidates[0])}
    return {
        "type": "candidates",
        "companies": [_public_company(record) for record in candidates[:8]],
    }
