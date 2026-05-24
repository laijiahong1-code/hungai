from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ..data import get_setting
from .finance import build_finance_scores
from .governance import build_governance_scores, build_governance_trends
from .mixed import build_mixed_scores
from .models import MODULE_CONFIG, MODULE_WEIGHTS, ModuleResult
from .region import build_region_scores


DEFAULT_SOURCE_ROOT = r"C:\Users\赖宏\Desktop\公司混改系统"


class ScoringEngine:
    def __init__(self, source_root: Path | str | None = None):
        self.source_root = Path(source_root or configured_source_root())
        self._loaded = False
        self._scores: dict[str, dict[str, ModuleResult]] = {}
        self._governance_trends: dict[str, list[dict]] = {}

    def score_company(self, stock_code: str) -> dict:
        code = str(stock_code).zfill(6)
        scores = self._load_scores()
        module_results = {
            key: scores.get(key, {}).get(code, ModuleResult.zero(key))
            for key in MODULE_CONFIG
        }
        modules = {key: result.score for key, result in module_results.items()}
        total_score = round(sum(modules[key] * MODULE_WEIGHTS[key] for key in MODULE_CONFIG), 1)
        return {
            "modules": modules,
            "module_scores": modules.copy(),
            "module_details": {key: result.detail_dict() for key, result in module_results.items()},
            "raw_scores": {key: result.raw_score_dict() for key, result in module_results.items()},
            "governanceTrend": [item.copy() for item in self._governance_trends.get(code, [])],
            "totalScore": total_score,
            "potentialLevel": potential_level(total_score),
            "vetoReasons": [],
        }

    def _load_scores(self) -> dict[str, dict[str, ModuleResult]]:
        if self._loaded:
            return self._scores
        if not self.source_root.exists():
            self._scores = {"mixed": build_mixed_scores(self.source_root)}
            self._governance_trends = {}
        else:
            self._scores = {
                "finance": build_finance_scores(self.source_root),
                "equity": build_governance_scores(self.source_root),
                "region": build_region_scores(self.source_root),
                "mixed": build_mixed_scores(self.source_root),
            }
            self._governance_trends = build_governance_trends(self.source_root)
        self._loaded = True
        return self._scores


def configured_source_root() -> str:
    return get_setting("MIXED_REFORM_SOURCE_ROOT", DEFAULT_SOURCE_ROOT)


def potential_level(score: float) -> str:
    if score >= 80:
        return "高潜力"
    if score >= 70:
        return "中高潜力"
    if score >= 60:
        return "观察潜力"
    return "低潜力"


@lru_cache(maxsize=4)
def get_scoring_engine(source_root: str | None = None) -> ScoringEngine:
    return ScoringEngine(source_root)


def get_scoring_result(stock_code: str, source_root: str | None = None) -> dict:
    return get_scoring_engine(source_root).score_company(stock_code)
