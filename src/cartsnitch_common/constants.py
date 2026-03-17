"""Constants and enums shared across CartSnitch services."""

from enum import StrEnum


class StoreSlug(StrEnum):
    """Supported retailer slugs."""

    MEIJER = "meijer"
    KROGER = "kroger"
    TARGET = "target"


class AccountStatus(StrEnum):
    """User store account link status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    ERROR = "error"


class DiscountType(StrEnum):
    """Coupon discount type."""

    PERCENT = "percent"
    FIXED = "fixed"
    BOGO = "bogo"
    BUY_X_GET_Y = "buy_x_get_y"


class PriceSource(StrEnum):
    """Source of a price observation."""

    RECEIPT = "receipt"
    CATALOG = "catalog"
    WEEKLY_AD = "weekly_ad"


class EventType(StrEnum):
    """Redis pub/sub event types."""

    RECEIPTS_INGESTED = "cartsnitch.receipts.ingested"
    PRICES_UPDATED = "cartsnitch.prices.updated"
    PRODUCTS_NORMALIZED = "cartsnitch.products.normalized"
    COUPONS_UPDATED = "cartsnitch.coupons.updated"
    ALERT_PRICE_INCREASE = "cartsnitch.alerts.price_increase"
    ALERT_SHRINKFLATION = "cartsnitch.alerts.shrinkflation"


class ProductCategory(StrEnum):
    """Top-level product categories."""

    PRODUCE = "produce"
    DAIRY = "dairy"
    MEAT = "meat"
    BAKERY = "bakery"
    FROZEN = "frozen"
    PANTRY = "pantry"
    BEVERAGES = "beverages"
    SNACKS = "snacks"
    HOUSEHOLD = "household"
    PERSONAL_CARE = "personal_care"
    OTHER = "other"


class MatchConfidence(StrEnum):
    """Confidence level for product matching."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SizeUnit(StrEnum):
    """Standardized product size units."""

    OZ = "oz"
    FL_OZ = "fl_oz"
    LB = "lb"
    G = "g"
    KG = "kg"
    ML = "ml"
    L = "l"
    CT = "ct"
    PK = "pk"
