"""Receipt normalization — parse raw Meijer scraper output into purchase records.

Maps raw receipt fields, cleans product names, extracts quantities/units.
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from cartsnitch_common.schemas.purchase import PurchaseCreate, PurchaseItemCreate


def _clean_product_name(raw: str) -> str:
    """Clean raw product name from scraper output."""
    cleaned = raw.strip()
    # Remove leading/trailing non-alphanumeric chars
    cleaned = re.sub(r"^\W+|\W+$", "", cleaned)
    # Collapse internal whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _safe_decimal(
    value: str | float | int | Decimal | None,
    default: Decimal = Decimal("0"),
) -> Decimal:
    """Safely convert a value to Decimal."""
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def parse_meijer_item(raw_item: dict) -> PurchaseItemCreate:
    """Parse a single Meijer scraper line item into a PurchaseItemCreate.

    Expected raw_item keys (from Meijer scraper):
      - description / name: product name
      - upc / upcCode: UPC barcode
      - quantity / qty: number of units
      - unitPrice / price: per-unit price
      - extendedPrice / totalPrice: line total
      - regularPrice: shelf price before discounts
      - salePrice: sale price if applicable
      - couponAmount / couponDiscount: coupon savings
      - loyaltyAmount / loyaltyDiscount: loyalty savings
      - category / department: raw category
    """
    name = raw_item.get("description") or raw_item.get("name") or ""
    cleaned_name = _clean_product_name(name)

    upc = raw_item.get("upc") or raw_item.get("upcCode")
    if upc:
        upc = str(upc).strip().lstrip("0") or str(upc).strip()

    qty = _safe_decimal(
        raw_item.get("quantity") or raw_item.get("qty"),
        default=Decimal("1"),
    )

    unit_price = _safe_decimal(raw_item.get("unitPrice") or raw_item.get("price"))
    extended = _safe_decimal(raw_item.get("extendedPrice") or raw_item.get("totalPrice"))
    if extended == Decimal("0") and unit_price > 0:
        extended = unit_price * qty

    regular = raw_item.get("regularPrice")
    sale = raw_item.get("salePrice")
    coupon = raw_item.get("couponAmount") or raw_item.get("couponDiscount")
    loyalty = raw_item.get("loyaltyAmount") or raw_item.get("loyaltyDiscount")
    category = raw_item.get("category") or raw_item.get("department")

    return PurchaseItemCreate(
        product_name_raw=cleaned_name,
        upc=upc,
        quantity=qty,
        unit_price=unit_price,
        extended_price=extended,
        regular_price=_safe_decimal(regular) if regular is not None else None,
        sale_price=_safe_decimal(sale) if sale is not None else None,
        coupon_discount=_safe_decimal(coupon) if coupon is not None else None,
        loyalty_discount=_safe_decimal(loyalty) if loyalty is not None else None,
        category_raw=str(category).strip() if category else None,
    )


def normalize_receipt(
    raw_receipt: dict,
    user_id: str,
    store_id: str,
) -> PurchaseCreate:
    """Parse a complete Meijer raw receipt into a PurchaseCreate.

    Expected raw_receipt keys:
      - receiptId / receipt_id / id: unique receipt identifier
      - date / purchaseDate / purchase_date: purchase date (YYYY-MM-DD or similar)
      - total / totalAmount: receipt total
      - subtotal: pre-tax subtotal
      - tax / taxAmount: tax amount
      - savings / totalSavings: total discount savings
      - items: list of raw line item dicts
    """
    import uuid

    receipt_id = str(
        raw_receipt.get("receiptId")
        or raw_receipt.get("receipt_id")
        or raw_receipt.get("id")
        or uuid.uuid4()
    )

    raw_date = (
        raw_receipt.get("date")
        or raw_receipt.get("purchaseDate")
        or raw_receipt.get("purchase_date")
    )
    if isinstance(raw_date, str):
        purchase_date = date.fromisoformat(raw_date[:10])
    elif isinstance(raw_date, date):
        purchase_date = raw_date
    else:
        purchase_date = date.today()

    total = _safe_decimal(raw_receipt.get("total") or raw_receipt.get("totalAmount"))
    subtotal = raw_receipt.get("subtotal")
    tax = raw_receipt.get("tax") or raw_receipt.get("taxAmount")
    savings = raw_receipt.get("savings") or raw_receipt.get("totalSavings")

    raw_items = raw_receipt.get("items") or []
    items = [parse_meijer_item(item) for item in raw_items]

    return PurchaseCreate(
        user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
        store_id=uuid.UUID(store_id) if isinstance(store_id, str) else store_id,
        receipt_id=receipt_id,
        purchase_date=purchase_date,
        total=total,
        subtotal=_safe_decimal(subtotal) if subtotal is not None else None,
        tax=_safe_decimal(tax) if tax is not None else None,
        savings_total=_safe_decimal(savings) if savings is not None else None,
        raw_data=raw_receipt,
        items=items,
    )
