from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from .scoring.common import stock_code


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MIXED_SCORE_CSV = PROJECT_ROOT / "data" / "HLD_current_A_share_mixed_ownership_scored.csv"
DEFAULT_MIXED_SHAREHOLDER_CSV = PROJECT_ROOT / "data" / "mixed_shareholders_current_top10.csv"

SCORE_ITEMS = [
    {
        "label": "非国有资本进入程度",
        "field": "Score_NonStateCapital",
        "max": 30.0,
        "description": "非国有资本参与与穿透比例",
    },
    {
        "label": "股权结构多样性",
        "field": "Score_EquityDiversity",
        "max": 20.0,
        "description": "股东类型覆盖与结构多元性",
    },
    {
        "label": "股权制衡程度",
        "field": "Score_EquityBalance",
        "max": 20.0,
        "description": "外部股东对第一大股东的制衡关系",
    },
    {
        "label": "股权融合程度",
        "field": "Score_EquityIntegration",
        "max": 15.0,
        "description": "国资与社会资本融合深度",
    },
    {
        "label": "股权开放治理程度",
        "field": "Score_OpenGovernance",
        "max": 15.0,
        "description": "适度集中与开放治理特征",
    },
]

DISPLAY_GROUPS = [
    ("state_owned", "国资相关", "#2563eb"),
    ("marketized", "市场化股东", "#0faaa5"),
    ("institution", "机构/互联互通", "#7c5ce7"),
    ("other_market", "其他市场主体", "#fb5a1e"),
]

RAW_TO_DISPLAY_GROUP = {
    "state_owned": "state_owned",
    "private_corporate": "marketized",
    "listed_company": "marketized",
    "financial_institution": "institution",
    "foreign": "institution",
    "natural_person": "other_market",
    "other": "other_market",
}


def build_mixed_degree_profile(
    code: str,
    score_path: Path | str | None = None,
    shareholder_path: Path | str | None = None,
) -> dict[str, Any]:
    normalized = stock_code(code)
    if not normalized:
        return {}
    score_rows = load_mixed_degree_rows(str(score_path or DEFAULT_MIXED_SCORE_CSV))
    row = score_rows.get(normalized)
    if not row:
        return {}
    shareholder_rows = load_mixed_shareholder_rows(str(shareholder_path or DEFAULT_MIXED_SHAREHOLDER_CSV))
    shareholders = shareholder_rows.get(normalized, [])
    holder_groups = build_holder_groups(shareholders)
    notes = build_structure_notes(row, shareholders, holder_groups)
    tags = build_signal_tags(row, holder_groups)
    return {
        "score": round(safe_float(row.get("MixedOwnershipScore")), 2),
        "level": str(row.get("MixedOwnershipLevel") or ""),
        "endDate": str(row.get("EndDate") or ""),
        "scoreItems": build_score_items(row),
        "structureMetrics": build_structure_metrics(row),
        "shareholders": shareholders,
        "holderGroups": holder_groups,
        "structureNotes": notes,
        "signalTags": tags,
    }


def mixed_degree_profiles_by_stock(
    score_path: Path | str | None = None,
    shareholder_path: Path | str | None = None,
) -> dict[str, dict[str, Any]]:
    score_rows = load_mixed_degree_rows(str(score_path or DEFAULT_MIXED_SCORE_CSV))
    shareholder_rows = load_mixed_shareholder_rows(str(shareholder_path or DEFAULT_MIXED_SHAREHOLDER_CSV))
    profiles = {}
    for code, row in score_rows.items():
        shareholders = shareholder_rows.get(code, [])
        holder_groups = build_holder_groups(shareholders)
        profiles[code] = {
            "score": round(safe_float(row.get("MixedOwnershipScore")), 2),
            "level": str(row.get("MixedOwnershipLevel") or ""),
            "endDate": str(row.get("EndDate") or ""),
            "scoreItems": build_score_items(row),
            "structureMetrics": build_structure_metrics(row),
            "shareholders": shareholders,
            "holderGroups": holder_groups,
            "structureNotes": build_structure_notes(row, shareholders, holder_groups),
            "signalTags": build_signal_tags(row, holder_groups),
        }
    return profiles


@lru_cache(maxsize=4)
def load_mixed_degree_rows(path_text: str) -> dict[str, dict[str, Any]]:
    path = Path(path_text)
    if not path.exists():
        return {}
    try:
        frame = pd.read_csv(path, dtype={"Symbol": str}, low_memory=False)
    except Exception:
        return {}
    if "Symbol" not in frame.columns:
        return {}
    frame["_stock_code"] = frame["Symbol"].apply(stock_code)
    if "EndDate" in frame.columns:
        frame = frame.sort_values(["_stock_code", "EndDate"])
    rows = {}
    for code, group in frame.groupby("_stock_code"):
        if not code:
            continue
        rows[code] = group.iloc[-1].to_dict()
    return rows


@lru_cache(maxsize=4)
def load_mixed_shareholder_rows(path_text: str) -> dict[str, list[dict[str, Any]]]:
    path = Path(path_text)
    if not path.exists():
        return {}
    try:
        frame = pd.read_csv(path, dtype={"stock_code": str}, low_memory=False)
    except Exception:
        return {}
    if "stock_code" not in frame.columns:
        return {}
    frame["_stock_code"] = frame["stock_code"].apply(stock_code)
    if "rank" in frame.columns:
        frame["rank"] = pd.to_numeric(frame["rank"], errors="coerce")
    if "shareholding_ratio" in frame.columns:
        frame["shareholding_ratio"] = pd.to_numeric(frame["shareholding_ratio"], errors="coerce")
    result: dict[str, list[dict[str, Any]]] = {}
    for code, group in frame.sort_values(["_stock_code", "rank"]).groupby("_stock_code"):
        if not code:
            continue
        shareholders = []
        for item in group.head(10).to_dict(orient="records"):
            shareholders.append(
                {
                    "rank": int(safe_float(item.get("rank"))),
                    "name": str(item.get("shareholder_name") or ""),
                    "ratio": round(safe_float(item.get("shareholding_ratio")), 2),
                    "nature": str(item.get("shareholder_nature") or ""),
                    "category": str(item.get("category") or ""),
                    "holderGroup": str(item.get("holder_group") or ""),
                    "holderGroupLabel": str(item.get("holder_group_label") or ""),
                }
            )
        result[code] = shareholders
    return result


def build_score_items(row: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for item in SCORE_ITEMS:
        max_score = float(item["max"])
        score = round(safe_float(row.get(str(item["field"]))), 2)
        percent = round(score / max_score * 100, 1) if max_score else 0.0
        items.append(
            {
                "label": item["label"],
                "score": score,
                "max": max_score,
                "percent": percent,
                "description": item["description"],
            }
        )
    return items


def build_structure_metrics(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "nonStateRatio": round(safe_float(row.get("NSttOwnedShrhlderRatioSum")), 2),
        "diversity": round(safe_float(row.get("EquityStructureDiversity")), 2),
        "ownershipConcentration": round(safe_float(row.get("OwnershipConcentration")), 2),
        "top1Ratio": round(safe_float(row.get("Top1ShareholderRatio")), 2),
        "equityBalance": round(safe_float(row.get("EquityBalance")), 2),
        "equityIntegration": round(safe_float(row.get("EquityIntegration")), 2),
    }


def build_holder_groups(shareholders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not shareholders:
        return []
    totals = {key: 0.0 for key, _, _ in DISPLAY_GROUPS}
    for shareholder in shareholders:
        raw_group = shareholder.get("holderGroup")
        display_key = RAW_TO_DISPLAY_GROUP.get(str(raw_group), "other_market")
        totals[display_key] = totals.get(display_key, 0.0) + safe_float(shareholder.get("ratio"))
    total_ratio = sum(totals.values())
    if total_ratio <= 0:
        return []
    groups = []
    for key, label, color in DISPLAY_GROUPS:
        ratio = totals.get(key, 0.0)
        groups.append(
            {
                "key": key,
                "label": label,
                "ratio": round(ratio, 2),
                "percentage": round(ratio / total_ratio * 100, 2),
                "color": color,
            }
        )
    return groups


def build_structure_notes(
    row: dict[str, Any],
    shareholders: list[dict[str, Any]],
    holder_groups: list[dict[str, Any]],
) -> list[str]:
    if not shareholders:
        return ["暂无股东结构明细"]
    notes = []
    top1_ratio = safe_float(row.get("Top1ShareholderRatio"))
    concentration = safe_float(row.get("OwnershipConcentration"))
    non_state_ratio = safe_float(row.get("NSttOwnedShrhlderRatioSum"))
    diversity = safe_float(row.get("EquityStructureDiversity"))
    balance = safe_float(row.get("EquityBalance"))
    if concentration >= 50 or top1_ratio >= 30:
        notes.append("前十大股东持股集中度较高，股权结构整体较稳定。")
    elif concentration > 0:
        notes.append("前十大股东持股分布相对分散，治理结构更依赖多方协同。")
    if non_state_ratio >= 10:
        notes.append("非国有资本参与明显，外部资本已形成一定进入基础。")
    if diversity >= 3:
        notes.append("股东类型较多元，有助于形成多主体治理结构。")
    if balance >= 0.7:
        notes.append("外部股东对第一大股东形成一定制衡。")
    if not notes and holder_groups:
        notes.append("股东结构信号较弱，建议结合后续公告持续观察。")
    return notes


def build_signal_tags(row: dict[str, Any], holder_groups: list[dict[str, Any]]) -> list[str]:
    tags = []
    group_ratio = {item["key"]: safe_float(item.get("ratio")) for item in holder_groups}
    if group_ratio.get("state_owned", 0) > 0 or safe_float(row.get("state_owned")) > 0:
        tags.append("国资参与")
    if safe_float(row.get("EquityStructureDiversity")) >= 3:
        tags.append("股东多元")
    if safe_float(row.get("NSttOwnedShrhlderRatioSum")) >= 10:
        tags.append("市场化参与")
    if safe_float(row.get("OwnershipConcentration")) >= 40:
        tags.append("结构稳定")
    if not tags:
        tags.append("持续观察")
    return tags


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
