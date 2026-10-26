from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.reporting.report import AnalysisReport
from app.domain.technical_analysis.elliott import ElliottWaveCount


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, ElliottWaveCount):
        return {
            "start_index": value.start_index,
            "end_index": value.end_index,
            "candidate": _json_value(value.candidate),
            "is_rule_consistent": value.is_rule_consistent,
            "rule_violations": list(value.rule_violations),
            "warnings": list(value.warnings),
            "wave_two_invalidation_price": str(value.wave_two_invalidation_price),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


class TechnicalIndicatorHistoryResponse:
    @staticmethod
    def from_report(report: AnalysisReport, limit: int = 250) -> dict[str, object]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        evidence = report.technical_analysis.indicators
        points = () if evidence is None else evidence.points[-limit:]
        return {
            "symbol": report.stock_symbol,
            "timeframe": report.technical_analysis.timeframe.value,
            "available": evidence is not None and bool(evidence.points),
            "methodology_version": (
                evidence.methodology_version if evidence is not None else None
            ),
            "returned_points": len(points),
            "total_points": len(evidence.points) if evidence is not None else 0,
            "points": [_json_value(point) for point in points],
        }
