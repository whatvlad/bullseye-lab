from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from memebot.core.config import Settings
from memebot.models.common import (
    DataAvailability,
    DataConfidence,
    ProviderProvenance,
)
from memebot.models.market import MarketValidationState
from memebot.models.risk import RiskEvidence, RiskResult

from .models import LocalRiskContext, OnChainRiskFacts


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    top1_hard_reject_percent: Decimal
    top5_warning_percent: Decimal
    top10_warning_percent: Decimal
    creator_hard_reject_percent: Decimal
    largest_buyer_warning_percent: Decimal
    synchronized_buyers_warning_count: int

    @classmethod
    def from_settings(cls, settings: Settings) -> RiskPolicy:
        return cls(
            top1_hard_reject_percent=settings.risk_top1_hard_reject_percent,
            top5_warning_percent=settings.risk_top5_warning_percent,
            top10_warning_percent=settings.risk_top10_warning_percent,
            creator_hard_reject_percent=settings.risk_creator_hard_reject_percent,
            largest_buyer_warning_percent=settings.risk_largest_buyer_warning_percent,
            synchronized_buyers_warning_count=(settings.risk_synchronized_buyers_warning_count),
        )


class RiskAssessor:
    """Apply deterministic rules; missing evidence is never treated as zero risk."""

    def __init__(self, policy: RiskPolicy) -> None:
        self._policy = policy

    def assess(self, context: LocalRiskContext, facts: OnChainRiskFacts) -> RiskResult:
        evidence: list[RiskEvidence] = []
        hard_rejects: list[str] = []
        warnings: list[str] = []
        critical_unknowns: list[str] = []
        risk_points = Decimal(0)

        onchain = ProviderProvenance(
            provider="solana_rpc",
            observed_at=facts.observed_at,
            confidence=DataConfidence.EXACT_ONCHAIN,
            source_reference=(
                f"slot:{facts.source_slot}" if facts.source_slot is not None else None
            ),
        )
        local = ProviderProvenance(
            provider="bullseye_registry",
            observed_at=context.observed_at,
            confidence=DataConfidence.HIGH,
            source_reference=(
                f"slot:{context.source_slot}" if context.source_slot is not None else None
            ),
        )

        if facts.mint_state is None:
            critical_unknowns.append("mint_security")
            evidence.append(_unknown("mint_security", "mint", facts.mint_error, onchain))
        else:
            mint = facts.mint_state
            evidence.append(
                _known(
                    "mint_supply_raw",
                    "mint",
                    "SPL total supply in raw token units",
                    mint.supply,
                    "info",
                    onchain,
                )
            )
            evidence.append(
                _known(
                    "mint_initialized",
                    "mint",
                    "SPL mint initialization state",
                    mint.initialized,
                    "info" if mint.initialized else "hard_reject",
                    onchain,
                )
            )
            if not mint.initialized:
                hard_rejects.append("mint_not_initialized")
                risk_points += Decimal(30)
            mint_authority_enabled = mint.mint_authority is not None
            evidence.append(
                _known(
                    "mint_authority_enabled",
                    "mint",
                    "Mint authority is still enabled",
                    mint_authority_enabled,
                    "hard_reject" if mint_authority_enabled else "info",
                    onchain,
                )
            )
            if mint_authority_enabled:
                hard_rejects.append("mint_authority_enabled")
                risk_points += Decimal(25)
            freeze_authority_enabled = mint.freeze_authority is not None
            evidence.append(
                _known(
                    "freeze_authority_enabled",
                    "mint",
                    "Freeze authority is still enabled",
                    freeze_authority_enabled,
                    "hard_reject" if freeze_authority_enabled else "info",
                    onchain,
                )
            )
            if freeze_authority_enabled:
                hard_rejects.append("freeze_authority_enabled")
                risk_points += Decimal(25)

        effective_validation = context.validation_state
        if (
            effective_validation
            in {
                MarketValidationState.DISCOVERED,
                MarketValidationState.VALIDATING,
                MarketValidationState.INSUFFICIENT_DATA,
            }
            and facts.liquidity_error is None
        ):
            # A third-party discovery event begins as insufficient. Successfully
            # decoding the market account and its reserves over independent RPC
            # is the deterministic validation required by the risk gate.
            effective_validation = MarketValidationState.VERIFIED_MARKET_DATA
        validation_rejected = effective_validation == MarketValidationState.REJECTED
        validation_unknown = effective_validation in {
            MarketValidationState.DISCOVERED,
            MarketValidationState.VALIDATING,
            MarketValidationState.INSUFFICIENT_DATA,
        }
        if validation_unknown:
            critical_unknowns.append("market_validation")
        evidence.append(
            _known(
                "market_validation_state",
                "market",
                "Current deterministic market validation state",
                effective_validation.value,
                "hard_reject"
                if validation_rejected
                else ("unknown" if validation_unknown else "info"),
                local,
            )
        )
        if validation_rejected:
            hard_rejects.append("market_validation_rejected")
            risk_points += Decimal(30)

        if facts.holder_error is not None:
            critical_unknowns.append("holder_distribution")
            evidence.append(_unknown("holder_distribution", "holders", facts.holder_error, onchain))
        else:
            risk_points += self._holder_evidence(facts, evidence, hard_rejects, warnings, onchain)

        if facts.creator_holding_error is not None:
            critical_unknowns.append("creator_holding")
            evidence.append(
                _unknown(
                    "creator_holding",
                    "creator",
                    facts.creator_holding_error,
                    onchain,
                )
            )
        else:
            creator_share = _required(facts.creator_holding_percent)
            creator_reject = creator_share >= self._policy.creator_hard_reject_percent
            evidence.append(
                _known(
                    "creator_holding_percent",
                    "creator",
                    "Creator share of circulating supply",
                    creator_share,
                    "hard_reject" if creator_reject else "info",
                    onchain,
                    self._policy.creator_hard_reject_percent,
                )
            )
            if creator_reject:
                hard_rejects.append("creator_holding_above_limit")
            risk_points += min(
                Decimal(15),
                creator_share / self._policy.creator_hard_reject_percent * Decimal(15),
            )

        if facts.liquidity_error is not None:
            critical_unknowns.append("liquidity")
            evidence.append(
                _unknown("effective_liquidity", "liquidity", facts.liquidity_error, onchain)
            )
        else:
            liquidity = _required(facts.available_quote_reserves_raw)
            no_liquidity = liquidity <= 0
            evidence.append(
                _known(
                    "effective_quote_reserves_raw",
                    "liquidity",
                    "Market quote reserves including protocol virtual reserves",
                    liquidity,
                    "hard_reject" if no_liquidity else "info",
                    onchain,
                    Decimal(0),
                )
            )
            if no_liquidity:
                hard_rejects.append("effective_liquidity_zero")
                risk_points += Decimal(30)

        risk_points += self._local_signals(context, evidence, warnings, local)
        evidence.extend(
            [
                _unknown(
                    "wallet_funding_graph",
                    "wallet_cluster",
                    "not_available_from_standard_rpc_snapshot",
                    onchain,
                ),
                _unknown(
                    "bundled_supply_percent",
                    "wallet_cluster",
                    "transaction_funding_attribution_not_implemented",
                    onchain,
                ),
            ]
        )

        critical = tuple(dict.fromkeys(critical_unknowns))
        hard = tuple(dict.fromkeys(hard_rejects))
        warning_codes = tuple(dict.fromkeys(warnings))
        available_count = sum(item.availability == DataAvailability.AVAILABLE for item in evidence)
        completeness = (Decimal(available_count) * Decimal(100) / Decimal(len(evidence))).quantize(
            Decimal("0.01")
        )
        allowed: bool | None = False if hard else (None if critical else True)
        score = None if critical else min(Decimal(100), risk_points.quantize(Decimal("0.01")))
        return RiskResult(
            allowed=allowed,
            risk_score=score,
            data_completeness_percent=completeness,
            critical_unknowns=critical,
            hard_reject_reasons=hard,
            warnings=warning_codes,
            evidence=tuple(evidence),
        )

    def _holder_evidence(
        self,
        facts: OnChainRiskFacts,
        evidence: list[RiskEvidence],
        hard_rejects: list[str],
        warnings: list[str],
        provenance: ProviderProvenance,
    ) -> Decimal:
        top1 = _required(facts.top1_holder_percent)
        top5 = _required(facts.top5_holder_percent)
        top10 = _required(facts.top10_holder_percent)
        top1_reject = top1 >= self._policy.top1_hard_reject_percent
        top5_warning = top5 >= self._policy.top5_warning_percent
        top10_warning = top10 >= self._policy.top10_warning_percent
        evidence.extend(
            [
                _known(
                    "top1_holder_percent",
                    "holders",
                    "Largest holder share",
                    top1,
                    "hard_reject" if top1_reject else "info",
                    provenance,
                    self._policy.top1_hard_reject_percent,
                ),
                _known(
                    "top5_holder_percent",
                    "holders",
                    "Top five holder share",
                    top5,
                    "warning" if top5_warning else "info",
                    provenance,
                    self._policy.top5_warning_percent,
                ),
                _known(
                    "top10_holder_percent",
                    "holders",
                    "Top ten holder share",
                    top10,
                    "warning" if top10_warning else "info",
                    provenance,
                    self._policy.top10_warning_percent,
                ),
                _known(
                    "excluded_market_token_accounts",
                    "holders",
                    "Market-controlled token accounts excluded",
                    facts.excluded_market_token_accounts,
                    "info",
                    provenance,
                ),
            ]
        )
        if top1_reject:
            hard_rejects.append("top1_holder_above_limit")
        if top5_warning:
            warnings.append("top5_holder_concentration")
        if top10_warning:
            warnings.append("top10_holder_concentration")
        return (
            min(
                Decimal(25),
                top1 / self._policy.top1_hard_reject_percent * Decimal(25),
            )
            + (Decimal(5) if top5_warning else Decimal(0))
            + (Decimal(5) if top10_warning else Decimal(0))
        )

    def _local_signals(
        self,
        context: LocalRiskContext,
        evidence: list[RiskEvidence],
        warnings: list[str],
        provenance: ProviderProvenance,
    ) -> Decimal:
        points = Decimal(0)
        evidence.extend(
            [
                _known(
                    "creator_launch_count",
                    "creator",
                    "Observed launches by creator",
                    context.creator_launches,
                    "info",
                    provenance,
                ),
                _known(
                    "creator_graduation_count",
                    "creator",
                    "Observed graduations by creator",
                    context.creator_graduations,
                    "info",
                    provenance,
                ),
                _known(
                    "creator_rejection_count",
                    "creator",
                    "Observed rejected markets by creator",
                    context.creator_rejections,
                    "warning" if context.creator_rejections else "info",
                    provenance,
                ),
                _known(
                    "early_unique_buyers",
                    "wallet_cluster",
                    "Unique wallets in first 200 observed buys",
                    context.early_unique_buyers,
                    "info",
                    provenance,
                ),
            ]
        )
        if context.creator_rejections:
            warnings.append("creator_has_rejected_markets")
            points += Decimal(5)
        if context.largest_early_buyer_share_percent is None:
            evidence.append(
                _unknown(
                    "largest_early_buyer_share",
                    "wallet_cluster",
                    "no_observed_buy_volume",
                    provenance,
                )
            )
        else:
            large_buyer = (
                context.largest_early_buyer_share_percent
                >= self._policy.largest_buyer_warning_percent
            )
            evidence.append(
                _known(
                    "largest_early_buyer_share_percent",
                    "wallet_cluster",
                    "Largest early buyer share of observed buy volume",
                    context.largest_early_buyer_share_percent,
                    "warning" if large_buyer else "info",
                    provenance,
                    self._policy.largest_buyer_warning_percent,
                )
            )
            if large_buyer:
                warnings.append("largest_early_buyer_concentration")
                points += Decimal(5)
        synchronized = (
            context.largest_synchronized_buyer_group
            >= self._policy.synchronized_buyers_warning_count
        )
        evidence.append(
            _known(
                "same_slot_buyer_group",
                "wallet_cluster",
                "Largest group of distinct buyers in one slot",
                context.largest_synchronized_buyer_group,
                "warning" if synchronized else "info",
                provenance,
                Decimal(self._policy.synchronized_buyers_warning_count),
            )
        )
        if synchronized:
            warnings.append("same_slot_buyer_cluster")
            points += Decimal(5)
        return points


def _known(
    code: str,
    category: str,
    message: str,
    value: bool | int | Decimal | str,
    severity: Literal["info", "warning", "hard_reject", "unknown"],
    provenance: ProviderProvenance,
    threshold: Decimal | None = None,
) -> RiskEvidence:
    return RiskEvidence(
        code=code,
        category=category,
        message=message,
        value=value,
        severity=severity,
        threshold=threshold,
        provenance=provenance,
    )


def _unknown(
    code: str,
    category: str,
    reason: str | None,
    provenance: ProviderProvenance,
) -> RiskEvidence:
    return RiskEvidence(
        code=code,
        category=category,
        message=reason or "unknown",
        availability=DataAvailability.UNKNOWN,
        severity="unknown",
        provenance=provenance.model_copy(update={"confidence": DataConfidence.UNKNOWN}),
    )


def _required[ValueT](value: ValueT | None) -> ValueT:
    if value is None:
        raise ValueError("risk fact unexpectedly missing without an error code")
    return value
