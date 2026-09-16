from uuid import uuid4

import pytest

from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.scoring import TechnicalScorer
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus


def test_all_positive_evidence_produces_plus_three():
    result = TechnicalScorer.score(
        trend=TrendEvidence(TrendStatus.UPTREND),
        momentum=MomentumEvidence(MomentumStatus.POSITIVE),
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE),
    )

    assert result.total_score == 3


def test_all_neutral_evidence_produces_zero():
    result = TechnicalScorer.score(
        trend=TrendEvidence(TrendStatus.SIDEWAYS),
        momentum=MomentumEvidence(MomentumStatus.NEUTRAL),
        volume=VolumeEvidence(VolumeStatus.EQUAL_TO_AVERAGE),
    )

    assert result.total_score == 0


def test_all_negative_evidence_produces_minus_three():
    result = TechnicalScorer.score(
        trend=TrendEvidence(TrendStatus.DOWNTREND),
        momentum=MomentumEvidence(MomentumStatus.NEGATIVE),
        volume=VolumeEvidence(VolumeStatus.BELOW_AVERAGE),
    )

    assert result.total_score == -3


def test_undefined_and_insufficient_evidence_contribute_zero():
    result = TechnicalScorer.score(
        trend=TrendEvidence(TrendStatus.INSUFFICIENT_DATA),
        momentum=MomentumEvidence(MomentumStatus.UNDEFINED),
        volume=VolumeEvidence(VolumeStatus.INSUFFICIENT_DATA),
    )

    assert result.total_score == 0


def test_score_preserves_explainable_contributions():
    result = TechnicalScorer.score(
        trend=TrendEvidence(TrendStatus.UPTREND),
        momentum=MomentumEvidence(MomentumStatus.NEGATIVE),
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE),
    )

    assert result.trend_points == 1
    assert result.momentum_points == -1
    assert result.volume_points == 1
    assert result.total_score == 1


def test_score_is_immutable():
    result = TechnicalScorer.score(
        trend=TrendEvidence(TrendStatus.UPTREND),
        momentum=MomentumEvidence(MomentumStatus.NEUTRAL),
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE),
    )

    with pytest.raises(AttributeError):
        result.total_score = 99


def test_scoring_is_deterministic():
    trend = TrendEvidence(TrendStatus.UPTREND)
    momentum = MomentumEvidence(MomentumStatus.POSITIVE)
    volume = VolumeEvidence(VolumeStatus.BELOW_AVERAGE)

    first = TechnicalScorer.score(trend, momentum, volume)
    second = TechnicalScorer.score(trend, momentum, volume)

    assert first == second
