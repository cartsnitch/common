"""Product matching & dedup — UPC primary, fuzzy name fallback, confidence scoring.

Wraps the Phase 1 normalization module with confidence-level classification
and batch matching for purchase ingestion.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from cartsnitch_common.constants import MatchConfidence
from cartsnitch_common.models.product import NormalizedProduct
from cartsnitch_common.normalization import (
    MatchMethod,
    MatchResult,
    extract_size_info,
    normalize_product,
)
from cartsnitch_common.schemas.purchase import PurchaseItemCreate

# Re-export for convenience
ConfidenceLevel = MatchConfidence


@dataclass(frozen=True)
class MatchOutcome:
    """Result of matching a single purchase item to a normalized product."""

    item_index: int
    match: MatchResult | None
    confidence_level: MatchConfidence
    created_new: bool = False


def classify_confidence(score: float, method: MatchMethod) -> MatchConfidence:
    """Classify a match score into high/medium/low confidence."""
    if method == MatchMethod.UPC:
        return MatchConfidence.HIGH
    # Name-based matching thresholds
    if score >= 0.8:
        return MatchConfidence.HIGH
    if score >= 0.5:
        return MatchConfidence.MEDIUM
    return MatchConfidence.LOW


def _create_product_from_item(
    session: Session,
    item: PurchaseItemCreate,
) -> NormalizedProduct:
    """Create a new NormalizedProduct from a purchase item that had no match."""
    size_info = extract_size_info(item.product_name_raw)
    product = NormalizedProduct(
        id=uuid.uuid4(),
        canonical_name=item.product_name_raw,
        size=size_info[0] if size_info else None,
        size_unit=size_info[1] if size_info else None,
        upc_variants=[item.upc] if item.upc else [],
    )
    session.add(product)
    session.flush()
    return product


class ProductMatcher:
    """Batch product matcher for purchase ingestion.

    Usage:
        matcher = ProductMatcher(session)
        outcomes = matcher.match_items(items)
    """

    def __init__(
        self,
        session: Session,
        name_threshold: float = 0.4,
        auto_create: bool = True,
    ):
        self.session = session
        self.name_threshold = name_threshold
        self.auto_create = auto_create

    def match_single(
        self, item: PurchaseItemCreate,
    ) -> tuple[NormalizedProduct | None, MatchResult | None, MatchConfidence]:
        """Match a single purchase item to a normalized product.

        Returns (product, match_result, confidence_level).
        If auto_create is True and no match found, creates a new product.
        """
        result = normalize_product(
            self.session,
            item.product_name_raw,
            upc=item.upc,
            name_threshold=self.name_threshold,
        )

        if result:
            confidence = classify_confidence(result.confidence, result.method)
            return result.product, result, confidence

        if self.auto_create:
            product = _create_product_from_item(self.session, item)
            return product, None, MatchConfidence.LOW

        return None, None, MatchConfidence.LOW

    def match_items(self, items: list[PurchaseItemCreate]) -> list[MatchOutcome]:
        """Match a batch of purchase items. Returns outcomes in order."""
        outcomes: list[MatchOutcome] = []
        for idx, item in enumerate(items):
            product, result, confidence = self.match_single(item)
            created = result is None and product is not None
            outcomes.append(
                MatchOutcome(
                    item_index=idx,
                    match=result,
                    confidence_level=confidence,
                    created_new=created,
                )
            )
        return outcomes


def match_purchase_item(
    session: Session,
    item: PurchaseItemCreate,
    name_threshold: float = 0.4,
    auto_create: bool = True,
) -> tuple[NormalizedProduct | None, MatchConfidence]:
    """Convenience function: match a single item, return (product, confidence)."""
    matcher = ProductMatcher(session, name_threshold=name_threshold, auto_create=auto_create)
    product, _, confidence = matcher.match_single(item)
    return product, confidence
