from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader
from tools.m61_build_candidate_dataset import build_candidate_package

STOCK_ID = "00000000-0000-0000-0000-000000000001"
MARKET_HEADERS = "Date,Open,High,Low,Close,Volume\n"
FINANCIAL_HEADERS = (
    "period_end,available_at,revenue,net_income,current_assets,"
    "current_liabilities,revision\n"
)


def _inputs(tmp_path: Path, market_body: str | None = None) -> tuple[Path, Path]:
    market = tmp_path / "COMI-market.csv"
    market.write_text(
        market_body
        or (
            MARKET_HEADERS
            + "2019-01-02,10,11,9,10,1000\n"
            + "2021-01-04,10,12,9,11,1200\n"
            + "2025-12-31,11,13,10,12,1500\n"
        ),
        encoding="utf-8",
    )
    financial = tmp_path / "COMI-financial.csv"
    financial.write_text(
        FINANCIAL_HEADERS
        + "2020-12-31,2021-03-01,1000,100,500,200,1\n"
        + "2021-12-31,2022-03-01,1100,110,550,220,1\n"
        + "2022-12-31,2023-03-01,1200,120,600,240,1\n"
        + "2023-12-31,2024-03-01,1300,130,650,260,1\n"
        + "2024-12-31,2025-03-01,1400,140,700,280,1\n",
        encoding="utf-8",
    )
    return market, financial


def _build(market: Path, financial: Path, output: Path) -> dict:
    return build_candidate_package(
        market_csv=market,
        financial_csv=financial,
        output_dir=output,
        symbol="comi",
        stock_id=STOCK_ID,
        dataset_version="candidate-2026-10-09-001",
        market_provider="Test Vendor",
        market_source_reference="https://example.invalid/market-delivery",
        market_acquired_at="2026-10-09T00:00:00+03:00",
        market_licensing_notes=(
            "status=unverified; evidence_reference=unknown; "
            "permitted_uses=; redistribution=prohibited"
        ),
        corporate_action_convention="raw-as-published",
        financial_provider="Test Financial Source",
        financial_source_reference="https://example.invalid/financial-delivery",
        financial_acquired_at="2026-10-09T00:00:00+03:00",
        financial_licensing_notes=(
            "status=unverified; evidence_reference=unknown; "
            "permitted_uses=; redistribution=prohibited"
        ),
    )


def test_builder_creates_candidate_and_preserves_source_bytes(tmp_path: Path) -> None:
    market, financial = _inputs(tmp_path)
    market_bytes = market.read_bytes()
    financial_bytes = financial.read_bytes()
    output = tmp_path / "candidate-package"

    report = _build(market, financial, output)

    assert report["status"] == "CANDIDATE_ONLY"
    assert report["acceptance_claim"] is False
    assert report["symbol"] == "COMI"
    assert report["market_artifact"]["raw_sha256"] == hashlib.sha256(market_bytes).hexdigest()
    assert report["financial_artifact"]["raw_sha256"] == hashlib.sha256(financial_bytes).hexdigest()
    assert (output / "raw" / "market_source.csv").read_bytes() == market_bytes
    assert (output / "raw" / "financial_source.csv").read_bytes() == financial_bytes
    assert (output / "candidate_report.json").is_file()

    loader = HistoricalDatasetLoader(output)
    manifest = loader.load_manifest()
    loader.verify_raw_source_evidence()
    assert manifest.dataset_id == "egx-m61-comi"
    assert len(loader.load_market_observations()) == 3
    assert len(loader.load_financial_snapshots()) == 5
    assert any(
        finding.startswith("m61:insufficient_warmup=")
        for finding in report["market_validation_findings"]
    )


def test_builder_rejects_invalid_market_data_without_creating_package(tmp_path: Path) -> None:
    market, financial = _inputs(
        tmp_path,
        MARKET_HEADERS + "2021-01-04,12,11,13,10,-1\n",
    )
    output = tmp_path / "rejected-package"

    with pytest.raises(ValueError, match="structural validation findings"):
        _build(market, financial, output)

    assert not output.exists()


def test_builder_rejects_financial_snapshot_available_before_period_end(tmp_path: Path) -> None:
    market, financial = _inputs(tmp_path)
    content = financial.read_text(encoding="utf-8").replace(
        "2020-12-31,2021-03-01",
        "2020-12-31,2020-12-30",
        1,
    )
    financial.write_text(content, encoding="utf-8")
    output = tmp_path / "rejected-package"

    with pytest.raises(ValueError, match="available_at cannot precede period_end"):
        _build(market, financial, output)

    assert not output.exists()


def test_builder_refuses_to_overwrite_an_existing_candidate(tmp_path: Path) -> None:
    market, financial = _inputs(tmp_path)
    output = tmp_path / "existing-package"
    output.mkdir()

    with pytest.raises(ValueError, match="must not already exist"):
        _build(market, financial, output)



def test_builder_rejects_extra_financial_csv_values(tmp_path: Path) -> None:
    market, financial = _inputs(tmp_path)
    content = financial.read_text(encoding="utf-8")
    content = content.replace(
        "2020-12-31,2021-03-01,1000,100,500,200,1",
        "2020-12-31,2021-03-01,1000,100,500,200,1,unexpected",
        1,
    )
    financial.write_text(content, encoding="utf-8")
    output = tmp_path / "rejected-package"

    with pytest.raises(ValueError, match="missing or extra CSV fields"):
        _build(market, financial, output)

    assert not output.exists()


def test_builder_rejects_duplicate_financial_headers(tmp_path: Path) -> None:
    market, financial = _inputs(tmp_path)
    content = financial.read_text(encoding="utf-8").replace(
        "period_end,available_at",
        "period_end,period_end",
        1,
    )
    financial.write_text(content, encoding="utf-8")
    output = tmp_path / "rejected-package"

    with pytest.raises(ValueError, match="exactly these canonical columns"):
        _build(market, financial, output)

    assert not output.exists()


def test_builder_rejects_market_rows_for_a_different_source_symbol(tmp_path: Path) -> None:
    market, financial = _inputs(
        tmp_path,
        "Ticker,Date,Open,High,Low,Close,Volume\n"
        "EGAL,2021-01-04,10,12,9,11,1200\n",
    )
    output = tmp_path / "wrong-symbol-package"

    with pytest.raises(ValueError, match="source symbol mismatch"):
        _build(market, financial, output)

    assert not output.exists()


def test_builder_accepts_explicit_provider_symbol_alias(tmp_path: Path) -> None:
    market, financial = _inputs(
        tmp_path,
        "Ticker,Date,Open,High,Low,Close,Volume\n"
        "COMI.CA,2021-01-04,10,12,9,11,1200\n",
    )
    output = tmp_path / "provider-symbol-package"
    kwargs = {
        "market_csv": market,
        "financial_csv": financial,
        "output_dir": output,
        "symbol": "COMI",
        "stock_id": STOCK_ID,
        "source_symbol": "COMI.CA",
        "dataset_version": "candidate-2026-10-09-002",
        "market_provider": "Test Vendor",
        "market_source_reference": "https://example.invalid/market-delivery",
        "market_acquired_at": "2026-10-09T00:00:00+03:00",
        "market_licensing_notes": "status=unverified; evidence_reference=unknown; permitted_uses=; redistribution=prohibited",
        "corporate_action_convention": "raw-as-published",
        "financial_provider": "Test Financial Source",
        "financial_source_reference": "https://example.invalid/financial-delivery",
        "financial_acquired_at": "2026-10-09T00:00:00+03:00",
        "financial_licensing_notes": "status=unverified; evidence_reference=unknown; permitted_uses=; redistribution=prohibited",
    }

    report = build_candidate_package(**kwargs)

    assert report["status"] == "CANDIDATE_ONLY"
    assert report["symbol"] == "COMI"
    assert (output / "market_observations.csv").is_file()
    manifest = HistoricalDatasetLoader(output).load_manifest()
    assert "COMI.CA->" + STOCK_ID in manifest.market_observations.provenance.symbol_mappings
    assert manifest.financial_snapshots.provenance.symbol_mappings == ("COMI->" + STOCK_ID,)


def test_builder_rejects_duplicate_source_symbol_headers(tmp_path: Path) -> None:
    market, financial = _inputs(
        tmp_path,
        "Ticker,Ticker,Date,Open,High,Low,Close,Volume\n"
        "COMI,COMI,2021-01-04,10,12,9,11,1200\n",
    )
    output = tmp_path / "ambiguous-symbol-package"

    with pytest.raises(ValueError, match="CSV has duplicate headers"):
        _build(market, financial, output)

    assert not output.exists()


def test_builder_deduplicates_case_insensitive_canonical_symbol_alias(tmp_path: Path) -> None:
    market, financial = _inputs(tmp_path)
    output = tmp_path / "canonical-symbol-package"
    kwargs = {
        "market_csv": market,
        "financial_csv": financial,
        "output_dir": output,
        "symbol": "COMI",
        "stock_id": STOCK_ID,
        "source_symbol": "comi",
        "dataset_version": "candidate-2026-10-09-003",
        "market_provider": "Test Vendor",
        "market_source_reference": "https://example.invalid/market-delivery",
        "market_acquired_at": "2026-10-09T00:00:00+03:00",
        "market_licensing_notes": "status=unverified; evidence_reference=unknown; permitted_uses=; redistribution=prohibited",
        "corporate_action_convention": "raw-as-published",
        "financial_provider": "Test Financial Source",
        "financial_source_reference": "https://example.invalid/financial-delivery",
        "financial_acquired_at": "2026-10-09T00:00:00+03:00",
        "financial_licensing_notes": "status=unverified; evidence_reference=unknown; permitted_uses=; redistribution=prohibited",
    }

    report = build_candidate_package(**kwargs)

    assert report["status"] == "CANDIDATE_ONLY"
    manifest = HistoricalDatasetLoader(output).load_manifest()
    assert manifest.market_observations.provenance.symbol_mappings == (
        "COMI->" + STOCK_ID,
    )



def test_builder_rejects_malformed_financial_csv_quoting(tmp_path: Path) -> None:
    market, financial = _inputs(tmp_path)
    content = financial.read_text(encoding="utf-8")
    content = content.replace(
        "2020-12-31,2021-03-01,1000,100,500,200,1",
        '2020-12-31,2021-03-01,"1000,100,500,200,1',
        1,
    )
    financial.write_text(content, encoding="utf-8")
    output = tmp_path / "malformed-financial-package"

    with pytest.raises(ValueError, match="malformed quoting"):
        _build(market, financial, output)

    assert not output.exists()


def test_builder_rejects_financial_csv_row_with_missing_fields(tmp_path: Path) -> None:
    market, financial = _inputs(tmp_path)
    content = financial.read_text(encoding="utf-8")
    content = content.replace(
        "2020-12-31,2021-03-01,1000,100,500,200,1",
        "2020-12-31,2021-03-01,1000,100,500,200",
        1,
    )
    financial.write_text(content, encoding="utf-8")
    output = tmp_path / "missing-financial-field-package"

    with pytest.raises(ValueError, match="missing or extra CSV fields"):
        _build(market, financial, output)

    assert not output.exists()
