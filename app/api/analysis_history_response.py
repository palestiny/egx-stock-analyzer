from dataclasses import asdict, dataclass
from uuid import UUID

from app.api.analysis_report_response import AnalysisReportResponse
from app.application.analysis.result_store import AnalysisResultRecord
from app.domain.reporting.report import AnalysisReport


@dataclass(frozen=True)
class AnalysisHistoryItemResponse:
    snapshot_id: UUID
    report: AnalysisReportResponse

    @classmethod
    def from_record_and_report(
        cls,
        record: AnalysisResultRecord,
        report: AnalysisReport,
    ) -> "AnalysisHistoryItemResponse":
        return cls(
            snapshot_id=record.snapshot_id,
            report=AnalysisReportResponse.from_report(report),
        )


@dataclass(frozen=True)
class AnalysisHistoryResponse:
    symbol: str
    items: tuple[AnalysisHistoryItemResponse, ...]

    @classmethod
    def from_items(
        cls,
        symbol: str,
        items: tuple[tuple[AnalysisResultRecord, AnalysisReport], ...],
    ) -> "AnalysisHistoryResponse":
        return cls(
            symbol=symbol,
            items=tuple(
                AnalysisHistoryItemResponse.from_record_and_report(record, report)
                for record, report in items
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
