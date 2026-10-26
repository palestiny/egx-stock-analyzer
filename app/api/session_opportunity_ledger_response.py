from app.domain.reporting.session_opportunity_ledger import SessionOpportunityLedgerReport


class SessionOpportunityLedgerResponse:
    @staticmethod
    def from_report(report: SessionOpportunityLedgerReport) -> dict[str, object]:
        return {
            "session_date": report.session_date.isoformat(),
            "generated_at": report.generated_at.isoformat(),
            "exchange_timezone": report.exchange_timezone,
            "methodology_version": report.methodology_version,
            "total_count": report.total_count,
            "unresolved_count": report.unresolved_count,
            "resolved_proxy_count": report.resolved_proxy_count,
            "status_counts": dict(report.status_counts),
            "opportunities": [
                {
                    "signal_id": str(item.signal_id),
                    "symbol": item.symbol,
                    "publication_time": item.publication_time.isoformat(),
                    "original_entry_lower": str(item.original_entry_lower),
                    "original_entry_upper": str(item.original_entry_upper),
                    "original_invalidation": str(item.original_invalidation),
                    "original_targets": [
                        {"label": label, "price": str(price)}
                        for label, price in item.original_targets
                    ],
                    "current_status": item.current_status.value,
                    "current_evidence": list(item.current_evidence),
                    "market_proxy_outcome": (
                        item.market_proxy_outcome.value
                        if item.market_proxy_outcome is not None else None
                    ),
                    "market_proxy_return": (
                        str(item.market_proxy_return)
                        if item.market_proxy_return is not None else None
                    ),
                    "market_proxy_r": (
                        str(item.market_proxy_r)
                        if item.market_proxy_r is not None else None
                    ),
                    "outcome_observed_at": (
                        item.outcome_observed_at.isoformat()
                        if item.outcome_observed_at is not None else None
                    ),
                }
                for item in report.opportunities
            ],
        }
