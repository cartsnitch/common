"""Data pipeline — receipt normalization, product matching, price tracking, shrinkflation."""

from cartsnitch_common.pipeline.matching import (
    ConfidenceLevel,
    ProductMatcher,
    match_purchase_item,
)
from cartsnitch_common.pipeline.price_tracking import (
    PriceDelta,
    get_price_trend,
    record_price_from_item,
)
from cartsnitch_common.pipeline.receipt import normalize_receipt, parse_meijer_item
from cartsnitch_common.pipeline.shrinkflation import detect_shrinkflation

__all__ = [
    "ConfidenceLevel",
    "PriceDelta",
    "ProductMatcher",
    "detect_shrinkflation",
    "get_price_trend",
    "match_purchase_item",
    "normalize_receipt",
    "parse_meijer_item",
    "record_price_from_item",
]
