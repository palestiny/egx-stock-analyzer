import argparse
import json
import sqlite3
from pathlib import Path

from app.infrastructure.persistence.analysis_result_serializer import (
    deserialize_analysis_result,
)


def inspect_database(database_path: str, symbol: str | None = None) -> int:
    path = Path(database_path)

    if not path.exists():
        print(f"Database not found: {path}")
        return 1

    with sqlite3.connect(path) as connection:
        if symbol:
            rows = connection.execute(
                """
                SELECT symbol, analysis_date, payload
                FROM analysis_results
                WHERE symbol = ?
                """,
                (symbol.strip().upper(),),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT symbol, analysis_date, payload
                FROM analysis_results
                ORDER BY symbol
                """
            ).fetchall()

    print(f"Database: {path}")
    print(f"Records: {len(rows)}")

    for stored_symbol, analysis_date, payload in rows:
        result = deserialize_analysis_result(payload)
        print()
        print(stored_symbol)
        print(f"  Analysis date:    {analysis_date or '—'}")
        print(f"  Technical score:  {result.technical_score.total_score}")
        print(f"  Fundamental:      {result.fundamental_score.total}")
        print(f"  Stock quality:    {result.stock_quality.total_score}")
        print(f"  Entry quality:    {result.entry_quality.total_score}")
        print(f"  Opportunity:      {result.opportunity.classification.value}")

        current_price = result.entry_context.current_price
        print(
            "  Current price:    "
            f"{current_price.value if current_price is not None else '—'}"
        )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect persisted EGX Stock Analyzer analysis results."
    )
    parser.add_argument(
        "--database",
        default="storage/analysis.db",
        help="SQLite database path.",
    )
    parser.add_argument(
        "--symbol",
        help="Optional stock symbol to inspect.",
    )
    args = parser.parse_args()

    return inspect_database(args.database, args.symbol)


if __name__ == "__main__":
    raise SystemExit(main())
