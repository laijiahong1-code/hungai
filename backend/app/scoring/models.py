from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


MODULE_CONFIG = {
    "finance": {"label": "财务引资潜力", "weight": 0.40, "raw_max": 50.0},
    "equity": {"label": "治理合规资质", "weight": 0.25, "raw_max": 25.0},
    "region": {"label": "区域国资适配", "weight": 0.20, "raw_max": 20.0},
    "mixed": {"label": "混改程度评分", "weight": 0.15, "raw_max": 100.0},
}

MODULE_LABELS = {key: value["label"] for key, value in MODULE_CONFIG.items()}
MODULE_WEIGHTS = {key: value["weight"] for key, value in MODULE_CONFIG.items()}


@dataclass(frozen=True)
class Evidence:
    label: str
    value: str
    score: float
    max: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "score": round(float(self.score), 2),
            "max": round(float(self.max), 2),
        }


@dataclass(frozen=True)
class ModuleResult:
    key: str
    raw_score: float = 0.0
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def raw_max(self) -> float:
        return float(MODULE_CONFIG[self.key]["raw_max"])

    @property
    def label(self) -> str:
        return str(MODULE_CONFIG[self.key]["label"])

    @property
    def weight(self) -> float:
        return float(MODULE_CONFIG[self.key]["weight"])

    @property
    def score(self) -> float:
        if self.raw_max <= 0:
            return 0.0
        return round(max(0.0, min(100.0, self.raw_score / self.raw_max * 100.0)), 1)

    def raw_score_rounded(self) -> float:
        return round(float(self.raw_score), 2)

    def raw_score_dict(self) -> dict[str, float]:
        return {"score": self.raw_score_rounded(), "max": round(self.raw_max, 2)}

    def detail_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "weight": self.weight,
            "score": self.score,
            "raw_score": self.raw_score_rounded(),
            "raw_max": round(self.raw_max, 2),
            "evidence": [item.to_dict() for item in self.evidence],
        }

    @classmethod
    def zero(cls, key: str) -> "ModuleResult":
        return cls(
            key=key,
            raw_score=0.0,
            evidence=[
                Evidence("数据状态", "原始数据未匹配", 0.0, float(MODULE_CONFIG[key]["raw_max"])),
            ],
        )
