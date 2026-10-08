from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.research.dataset import ExecutionModel, ResearchBar, ResearchCostConfig, ResearchDataQuality, SameBarAmbiguityPolicy, validate_research_bars


@dataclass(frozen=True)
class EntryFill:
    decision_timestamp: datetime
    fill_timestamp: datetime
    side: str
    reference_price: Decimal
    fill_price: Decimal
    commission: Decimal


@dataclass(frozen=True)
class ExitEvaluation:
    exit_timestamp: datetime
    exit_price: Decimal
    reason: str
    gross_return: Decimal
    net_return: Decimal
    commission: Decimal


def next_open_entry(bars: tuple[ResearchBar, ...], decision_index: int, *, side: str, costs: ResearchCostConfig, execution_model: ExecutionModel = ExecutionModel.NEXT_OPEN) -> EntryFill | None:
    validate_research_bars(bars)
    if execution_model is not ExecutionModel.NEXT_OPEN: raise ValueError("unsupported execution model")
    if side not in ("LONG", "SHORT"): raise ValueError("side must be LONG or SHORT")
    if decision_index < 0 or decision_index >= len(bars): raise IndexError("decision index out of range")
    decision = bars[decision_index]
    if decision_index + 1 >= len(bars): return None
    fill_bar = bars[decision_index + 1]
    if fill_bar.source_timestamp <= decision.source_timestamp: raise ValueError("next-open fill must occur after decision timestamp")
    reference = fill_bar.open
    price = reference * (Decimal("1") + costs.slippage_rate if side == "LONG" else Decimal("1") - costs.slippage_rate)
    return EntryFill(decision.source_timestamp, fill_bar.source_timestamp, side, reference, price, price * costs.commission_rate)


def evaluate_exit_bar(bar: ResearchBar, *, side: str, target: Decimal, invalidation: Decimal, entry_price: Decimal, costs: ResearchCostConfig, ambiguity_policy: SameBarAmbiguityPolicy = SameBarAmbiguityPolicy.INVALIDATION_FIRST) -> ExitEvaluation | None:
    if bar.quality is not ResearchDataQuality.VALID: raise ValueError("research-ineligible data quality")
    if side not in ("LONG", "SHORT"): raise ValueError("side must be LONG or SHORT")
    if min(target, invalidation, entry_price) <= 0: raise ValueError("target, invalidation, and entry price must be positive")
    if side == "LONG": target_hit, stop_hit = bar.high >= target, bar.low <= invalidation
    else: target_hit, stop_hit = bar.low <= target, bar.high >= invalidation
    if not target_hit and not stop_hit: return None
    if target_hit and stop_hit and ambiguity_policy is not SameBarAmbiguityPolicy.INVALIDATION_FIRST: raise ValueError("unsupported same-bar ambiguity policy")
    if stop_hit:
        reason = "INVALIDATION"
        reference_exit = bar.open if (bar.open <= invalidation if side == "LONG" else bar.open >= invalidation) else invalidation
    else:
        reason = "TARGET"
        reference_exit = bar.open if (bar.open >= target if side == "LONG" else bar.open <= target) else target
    exit_price = reference_exit * (Decimal("1") - costs.slippage_rate if side == "LONG" else Decimal("1") + costs.slippage_rate)
    gross = (exit_price - entry_price) / entry_price if side == "LONG" else (entry_price - exit_price) / entry_price
    commission = exit_price * costs.commission_rate
    net = gross - costs.commission_rate - commission / entry_price
    return ExitEvaluation(bar.source_timestamp, exit_price, reason, gross, net, commission)
