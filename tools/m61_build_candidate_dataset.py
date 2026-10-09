#!/usr/bin/env python3
"""Build a candidate M61 package from preserved source CSV artifacts.

The tool creates a CANDIDATE_ONLY package. It never declares licensing verified
and never marks a dataset accepted; run the separate COMI intake gate afterward.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import tempfile
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader
from tools.m61_vendor_csv_evidence_inspector import (
    _canonical_date,
    _canonical_number,
    inspect_csv,
)

EGX_TIMEZONE = ZoneInfo("Africa/Cairo")
MARKET_COLUMNS = (
    "stock_id",
    "timeframe",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source",
)
FINANCIAL_INPUT_COLUMNS = (
    "period_end",
    "available_at",
    "revenue",
    "net_income",
    "current_assets",
    "current_liabilities",
    "revision",
)
FINANCIAL_COLUMNS = (
    "stock_id",
    "period_end",
    "available_at",
    "revenue",
    "net_income",
    "current_assets",
    "current_liabilities",
    "source",
    "revision",
)
CORPORATE_ACTION_CONVENTIONS = (
    "raw-as-published",
    "unadjusted",
    "split-adjusted",
    "split-and-dividend-adjusted",
    "total-return-adjusted",
    "vendor-adjusted",
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _aware_datetime(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include an explicit timezone")
    return parsed


def _financial_decimal(value: str, field: str, *, optional: bool = False) -> str:
    raw = value.strip()
    if not raw and optional:
        return ""
    try:
        parsed = Decimal(raw.replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid financial {field}: {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"Financial {field} must be finite")
    return format(parsed, "f")


def _read_financial_snapshots(path: Path, stock_id: UUID, provider: str) -> list[dict[str, str]]:
    raw = path.read_bytes()
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Financial CSV must be UTF-8 or UTF-8 with BOM") from exc

    reader = csv.DictReader(io.StringIO(decoded, newline=""))
    if (
        not reader.fieldnames
        or len(reader.fieldnames) != len(FINANCIAL_INPUT_COLUMNS)
        or set(reader.fieldnames) != set(FINANCIAL_INPUT_COLUMNS)
    ):
        raise ValueError(
            "Financial CSV must use exactly these canonical columns: "
            + ", ".join(FINANCIAL_INPUT_COLUMNS)
        )

    rows: list[dict[str, str]] = []
    for index, source_row in enumerate(reader, start=2):
        if None in source_row or any(
            source_row.get(column) is None for column in FINANCIAL_INPUT_COLUMNS
        ):
            raise ValueError(
                f"Financial row {index} has missing or extra CSV fields"
            )
        try:
            period_end = date.fromisoformat((source_row["period_end"] or "").strip())
            available_at = date.fromisoformat((source_row["available_at"] or "").strip())
        except ValueError as exc:
            raise ValueError(f"Financial row {index} has an invalid ISO date") from exc
        if available_at < period_end:
            raise ValueError(
                f"Financial row {index}: available_at cannot precede period_end"
            )

        revision = (source_row["revision"] or "").strip() or "1"
        rows.append(
            {
                "stock_id": str(stock_id),
                "period_end": period_end.isoformat(),
                "available_at": available_at.isoformat(),
                "revenue": _financial_decimal(source_row["revenue"] or "", "revenue"),
                "net_income": _financial_decimal(
                    source_row["net_income"] or "", "net_income"
                ),
                "current_assets": _financial_decimal(
                    source_row["current_assets"] or "", "current_assets", optional=True
                ),
                "current_liabilities": _financial_decimal(
                    source_row["current_liabilities"] or "",
                    "current_liabilities",
                    optional=True,
                ),
                "source": provider,
                "revision": revision,
            }
        )

    if not rows:
        raise ValueError("Financial CSV contains no point-in-time snapshots")

    keys = [(row["period_end"], row["available_at"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Financial CSV has ambiguous snapshots for the same period and availability date")

    rows.sort(key=lambda row: (row["period_end"], row["available_at"], row["revision"]))
    return rows


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_candidate_package(
    *,
    market_csv: Path,
    financial_csv: Path,
    output_dir: Path,
    symbol: str,
    stock_id: str,
    source_symbol: str | None = None,
    dataset_version: str,
    market_provider: str,
    market_source_reference: str,
    market_acquired_at: str,
    market_licensing_notes: str,
    corporate_action_convention: str,
    financial_provider: str,
    financial_source_reference: str,
    financial_acquired_at: str,
    financial_licensing_notes: str,
    missing_data_findings: tuple[str, ...] = (),
    exclusions: tuple[str, ...] = (),
) -> dict:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol cannot be empty")
    try:
        resolved_stock_id = UUID(stock_id)
    except ValueError as exc:
        raise ValueError("stock_id must be a UUID") from exc
    if not dataset_version.strip():
        raise ValueError("dataset_version cannot be empty")
    if corporate_action_convention not in CORPORATE_ACTION_CONVENTIONS:
        raise ValueError("Unsupported corporate-action convention")
    for field, value in (
        ("market_provider", market_provider),
        ("market_source_reference", market_source_reference),
        ("market_licensing_notes", market_licensing_notes),
        ("financial_provider", financial_provider),
        ("financial_source_reference", financial_source_reference),
        ("financial_licensing_notes", financial_licensing_notes),
    ):
        if not value.strip():
            raise ValueError(f"{field} cannot be empty")

    market_acquired = _aware_datetime(market_acquired_at, "market_acquired_at")
    financial_acquired = _aware_datetime(financial_acquired_at, "financial_acquired_at")
    inspection = inspect_csv(
        market_csv,
        normalized_symbol,
        market_provider,
        market_source_reference,
    )
    if inspection["row_errors"]:
        raise ValueError("Market CSV contains malformed rows; inspect row_errors before packaging")
    structural_findings = [
        finding
        for finding in inspection["validation_findings"]
        if not finding.startswith("m61:")
    ]
    if structural_findings:
        raise ValueError(
            "Market CSV has structural validation findings: "
            + ", ".join(structural_findings)
        )

    market_raw = market_csv.read_bytes()
    try:
        decoded_market = market_raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Market CSV must be UTF-8 or UTF-8 with BOM") from exc
    reader = csv.DictReader(io.StringIO(decoded_market, newline=""))
    source_symbol_value = (source_symbol or normalized_symbol).strip()
    if not source_symbol_value:
        raise ValueError("source_symbol cannot be empty")
    symbol_headers = {
        "symbol", "ticker", "ticker symbol", "stock symbol", "security code",
        "instrument symbol",
    }
    normalized_headers: dict[str, list[str]] = {}
    for header in reader.fieldnames or []:
        normalized_headers.setdefault(header.strip().casefold(), []).append(header)
    matched_symbol_headers = [
        header
        for name in symbol_headers
        for header in normalized_headers.get(name, [])
    ]
    if len(matched_symbol_headers) > 1:
        raise ValueError(
            "Market CSV has ambiguous source-symbol columns: "
            + ", ".join(sorted(matched_symbol_headers))
        )
    source_symbol_header = matched_symbol_headers[0] if matched_symbol_headers else None
    mapped = inspection["columns"]["mapped"]
    market_rows: list[dict[str, str]] = []
    for row_number, source_row in enumerate(reader, start=2):
        if source_symbol_header is not None:
            observed_symbol = (source_row.get(source_symbol_header) or "").strip()
            if observed_symbol.casefold() != source_symbol_value.casefold():
                raise ValueError(
                    f"Market row {row_number} source symbol mismatch: "
                    f"expected {source_symbol_value!r}, got {observed_symbol!r}"
                )
        session_date = date.fromisoformat(_canonical_date(source_row[mapped["date"]] or ""))
        timestamp = datetime.combine(
            session_date,
            time.min,
            tzinfo=EGX_TIMEZONE,
        ).isoformat()
        market_rows.append(
            {
                "stock_id": str(resolved_stock_id),
                "timeframe": "1d",
                "timestamp": timestamp,
                "open": _canonical_number(source_row[mapped["open"]] or ""),
                "high": _canonical_number(source_row[mapped["high"]] or ""),
                "low": _canonical_number(source_row[mapped["low"]] or ""),
                "close": _canonical_number(source_row[mapped["close"]] or ""),
                "volume": _canonical_number(source_row[mapped["volume"]] or ""),
                "source": market_provider,
            }
        )
    if not market_rows:
        raise ValueError("Market CSV contains no usable rows")

    financial_raw = financial_csv.read_bytes()
    financial_rows = _read_financial_snapshots(
        financial_csv,
        resolved_stock_id,
        financial_provider,
    )
    market_hash = _sha256(market_raw)
    financial_hash = _sha256(financial_raw)
    market_dates = [datetime.fromisoformat(row["timestamp"]) for row in market_rows]
    financial_periods = [date.fromisoformat(row["period_end"]) for row in financial_rows]
    market_missing = list(dict.fromkeys(
        [*inspection["validation_findings"], *missing_data_findings]
    ))

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError("output_dir must not already exist; candidate packages are immutable")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.candidate-", dir=output_dir.parent)
    )

    try:
        raw_dir = temporary_dir / "raw"
        raw_dir.mkdir()
        shutil.copyfile(market_csv, raw_dir / "market_source.csv")
        shutil.copyfile(financial_csv, raw_dir / "financial_source.csv")
        _write_csv(temporary_dir / "market_observations.csv", MARKET_COLUMNS, market_rows)
        _write_csv(temporary_dir / "financial_snapshots.csv", FINANCIAL_COLUMNS, financial_rows)

        market_artifact_hash = _sha256((temporary_dir / "market_observations.csv").read_bytes())
        financial_artifact_hash = _sha256((temporary_dir / "financial_snapshots.csv").read_bytes())
        canonical_mapping = f"{normalized_symbol}->{resolved_stock_id}"
        market_symbol_mappings = [canonical_mapping]
        if source_symbol_value.casefold() != normalized_symbol.casefold():
            market_symbol_mappings.append(
                f"{source_symbol_value}->{resolved_stock_id}"
            )
        financial_symbol_mappings = [canonical_mapping]

        def provenance(
            provider: str,
            source_reference: str,
            acquired_at: datetime,
            licensing_notes: str,
            raw_reference: str,
            raw_hash: str,
            convention: str,
            findings: list[str],
            source_hash: str,
            symbol_mappings: list[str],
        ) -> dict:
            return {
                "provider": provider,
                "source_url": source_reference,
                "acquired_at": acquired_at.isoformat(),
                "symbol_mappings": symbol_mappings,
                "corporate_action_convention": convention,
                "missing_data_findings": findings,
                "exclusions": list(exclusions),
                "licensing_notes": licensing_notes,
                "transformation_manifest": (
                    "m61-candidate-package-builder-v1; "
                    f"input_sha256={source_hash}; canonical daily bars; "
                    "session dates normalized to Africa/Cairo; no price adjustment performed"
                ),
                "raw_source_evidence": {
                    "reference": raw_reference,
                    "sha256": raw_hash,
                    "retention": "original input bytes preserved unchanged in candidate package",
                },
            }

        manifest = {
            "dataset_id": f"egx-m61-{normalized_symbol.lower()}",
            "dataset_version": dataset_version,
            "schema_version": "3",
            "market_observations_artifact": {
                "path": "market_observations.csv",
                "sha256": market_artifact_hash,
                "row_count": len(market_rows),
                "coverage": {
                    "start": min(market_dates).isoformat(),
                    "end": max(market_dates).isoformat(),
                    "stock_count": 1,
                },
                "provenance": provenance(
                    market_provider,
                    market_source_reference,
                    market_acquired,
                    market_licensing_notes,
                    "raw/market_source.csv",
                    market_hash,
                    corporate_action_convention,
                    market_missing,
                    market_hash,
                    market_symbol_mappings,
                ),
            },
            "financial_snapshots_artifact": {
                "path": "financial_snapshots.csv",
                "sha256": financial_artifact_hash,
                "row_count": len(financial_rows),
                "coverage": {
                    "start": min(financial_periods).isoformat(),
                    "end": max(financial_periods).isoformat(),
                    "stock_count": 1,
                },
                "provenance": provenance(
                    financial_provider,
                    financial_source_reference,
                    financial_acquired,
                    financial_licensing_notes,
                    "raw/financial_source.csv",
                    financial_hash,
                    "not-applicable",
                    [],
                    financial_hash,
                    financial_symbol_mappings,
                ),
            },
        }
        (temporary_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        loader = HistoricalDatasetLoader(temporary_dir)
        loader.load_manifest()
        loader.verify_raw_source_evidence()
        loader.load_market_observations()
        loader.load_financial_snapshots()

        report = {
            "status": "CANDIDATE_ONLY",
            "acceptance_claim": False,
            "dataset_id": manifest["dataset_id"],
            "dataset_version": dataset_version,
            "symbol": normalized_symbol,
            "market_artifact": {
                "rows": len(market_rows),
                "raw_sha256": market_hash,
                "coverage": inspection["coverage"],
            },
            "financial_artifact": {
                "rows": len(financial_rows),
                "raw_sha256": financial_hash,
                "available_at_years": sorted({
                    date.fromisoformat(row["available_at"]).year for row in financial_rows
                }),
            },
            "market_validation_findings": market_missing,
            "next_step": (
                "Run tools.m61_comi_evidence_intake against this package. "
                "A candidate package is not accepted until every source, license, "
                "coverage, point-in-time, and reproducibility gate passes."
            ),
        }
        (temporary_dir / "candidate_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_dir.rename(output_dir)
        report["output_dir"] = str(output_dir)
        return report
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package real COMI CSV evidence as an immutable M61 candidate dataset."
    )
    parser.add_argument("--market-csv", type=Path, required=True)
    parser.add_argument("--financial-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--symbol", default="COMI")
    parser.add_argument("--source-symbol", help="Exact symbol as represented in the market CSV")
    parser.add_argument("--stock-id", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--market-provider", required=True)
    parser.add_argument("--market-source-reference", required=True)
    parser.add_argument("--market-acquired-at", required=True)
    parser.add_argument("--market-licensing-notes", required=True)
    parser.add_argument(
        "--corporate-action-convention",
        choices=CORPORATE_ACTION_CONVENTIONS,
        required=True,
    )
    parser.add_argument("--financial-provider", required=True)
    parser.add_argument("--financial-source-reference", required=True)
    parser.add_argument("--financial-acquired-at", required=True)
    parser.add_argument("--financial-licensing-notes", required=True)
    parser.add_argument("--missing-data-finding", action="append", default=[])
    parser.add_argument("--exclusion", action="append", default=[])
    args = parser.parse_args()

    try:
        report = build_candidate_package(
            market_csv=args.market_csv,
            financial_csv=args.financial_csv,
            output_dir=args.output_dir,
            symbol=args.symbol,
            stock_id=args.stock_id,
            source_symbol=args.source_symbol,
            dataset_version=args.dataset_version,
            market_provider=args.market_provider,
            market_source_reference=args.market_source_reference,
            market_acquired_at=args.market_acquired_at,
            market_licensing_notes=args.market_licensing_notes,
            corporate_action_convention=args.corporate_action_convention,
            financial_provider=args.financial_provider,
            financial_source_reference=args.financial_source_reference,
            financial_acquired_at=args.financial_acquired_at,
            financial_licensing_notes=args.financial_licensing_notes,
            missing_data_findings=tuple(args.missing_data_finding),
            exclusions=tuple(args.exclusion),
        )
    except (OSError, ValueError, csv.Error) as exc:
        print(json.dumps({"status": "REJECTED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
