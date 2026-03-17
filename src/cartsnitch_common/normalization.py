"""Product normalization — Phase 1: UPC matching + fuzzy name matching.

Matches products across retailers by:
1. Exact UPC match (highest confidence)
2. Fuzzy name matching via token-based Jaccard similarity (lower confidence)
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from cartsnitch_common.models.product import NormalizedProduct


class MatchMethod(StrEnum):
    """How a product match was determined."""

    UPC = "upc"
    NAME = "name"


@dataclass(frozen=True)
class MatchResult:
    """Result of a product normalization attempt."""

    product: NormalizedProduct
    confidence: float
    method: MatchMethod


# Noise words stripped during name cleaning
_NOISE_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "with",
        "in",
        "for",
        "to",
        "brand",
        "original",
        "classic",
        "new",
        "improved",
    }
)

# Regex for extracting size info (e.g., "16 oz", "1.5 lb", "12 ct")
_SIZE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(oz|fl\s*oz|lb|lbs|g|kg|ml|l|ct|pk|count|pack)\b",
    re.IGNORECASE,
)


def clean_name(name: str) -> str:
    """Normalize a product name for comparison.

    - Lowercase
    - Remove size info (e.g., "16 oz")
    - Strip noise words
    - Collapse whitespace
    """
    cleaned = name.lower()
    cleaned = _SIZE_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    tokens = cleaned.split()
    tokens = [t for t in tokens if t not in _NOISE_WORDS]
    return " ".join(tokens)


def extract_size_info(name: str) -> tuple[str, str] | None:
    """Extract (size, unit) from a product name, if present."""
    match = _SIZE_PATTERN.search(name)
    if match:
        return match.group(1), match.group(2).lower().replace(" ", "_")
    return None


def jaccard_similarity(a: str, b: str) -> float:
    """Token-based Jaccard similarity between two cleaned names."""
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def match_by_upc(session: Session, upc: str) -> MatchResult | None:
    """Find a normalized product by exact UPC match.

    Loads products with upc_variants and checks membership in Python
    for cross-database compatibility (works on both PostgreSQL and SQLite).
    """
    # TODO: Use PostgreSQL JSON containment query (@>) for production.
    # Current approach loads all products into memory — acceptable for tests
    # and small datasets, but will not scale.
    stmt = select(NormalizedProduct).where(NormalizedProduct.upc_variants.is_not(None))
    products = session.execute(stmt).scalars().all()
    for product in products:
        if product.upc_variants and upc in product.upc_variants:
            return MatchResult(product=product, confidence=1.0, method=MatchMethod.UPC)
    return None


def match_by_name(
    session: Session,
    name: str,
    threshold: float = 0.5,
) -> MatchResult | None:
    """Find the best normalized product by fuzzy name matching.

    Loads all normalized products and computes Jaccard similarity.
    Returns the best match above the threshold, or None.
    """
    # TODO: Use pg_trgm similarity index for production.
    # Current approach loads all products into memory — acceptable for tests
    # and small datasets, but will not scale.
    cleaned = clean_name(name)
    stmt = select(NormalizedProduct)
    products = session.execute(stmt).scalars().all()

    best_match: NormalizedProduct | None = None
    best_score = 0.0

    for product in products:
        score = jaccard_similarity(cleaned, clean_name(product.canonical_name))
        if score > best_score and score >= threshold:
            best_score = score
            best_match = product

    if best_match:
        return MatchResult(product=best_match, confidence=best_score, method=MatchMethod.NAME)
    return None


def normalize_product(
    session: Session,
    name: str,
    upc: str | None = None,
    name_threshold: float = 0.5,
) -> MatchResult | None:
    """Full normalization pipeline: UPC first, then fuzzy name fallback."""
    if upc:
        result = match_by_upc(session, upc)
        if result:
            return result
    return match_by_name(session, name, threshold=name_threshold)
