"""Tests for receipt normalization pipeline."""

import uuid
from datetime import date
from decimal import Decimal

from cartsnitch_common.pipeline.receipt import (
    _clean_product_name,
    _safe_decimal,
    normalize_receipt,
    parse_meijer_item,
)


class TestCleanProductName:
    def test_strips_whitespace(self):
        assert _clean_product_name("  Milk  ") == "Milk"

    def test_removes_leading_punctuation(self):
        assert _clean_product_name("---Milk---") == "Milk"

    def test_collapses_internal_whitespace(self):
        assert _clean_product_name("Whole   Milk   Gallon") == "Whole Milk Gallon"

    def test_empty_string(self):
        assert _clean_product_name("") == ""


class TestSafeDecimal:
    def test_string_input(self):
        assert _safe_decimal("3.99") == Decimal("3.99")

    def test_float_input(self):
        assert _safe_decimal(3.99) == Decimal("3.99")

    def test_int_input(self):
        assert _safe_decimal(4) == Decimal("4")

    def test_none_returns_default(self):
        assert _safe_decimal(None) == Decimal("0")

    def test_none_custom_default(self):
        assert _safe_decimal(None, Decimal("1")) == Decimal("1")

    def test_invalid_returns_default(self):
        assert _safe_decimal("not-a-number") == Decimal("0")

    def test_decimal_passthrough(self):
        assert _safe_decimal(Decimal("5.50")) == Decimal("5.50")


class TestParseMeijerItem:
    def test_basic_item(self):
        raw = {
            "description": "Kroger Whole Milk 1 Gallon",
            "upc": "0041250000001",
            "quantity": 1,
            "unitPrice": "3.99",
            "extendedPrice": "3.99",
            "category": "DAIRY",
        }
        item = parse_meijer_item(raw)
        assert item.product_name_raw == "Kroger Whole Milk 1 Gallon"
        assert item.upc == "41250000001"  # leading zeros stripped
        assert item.quantity == Decimal("1")
        assert item.unit_price == Decimal("3.99")
        assert item.extended_price == Decimal("3.99")
        assert item.category_raw == "DAIRY"

    def test_alternate_field_names(self):
        raw = {
            "name": "Eggs Large 12 ct",
            "upcCode": "012345",
            "qty": 2,
            "price": "4.50",
            "totalPrice": "9.00",
            "department": "EGGS",
        }
        item = parse_meijer_item(raw)
        assert item.product_name_raw == "Eggs Large 12 ct"
        assert item.upc == "12345"
        assert item.quantity == Decimal("2")
        assert item.unit_price == Decimal("4.50")
        assert item.extended_price == Decimal("9.00")
        assert item.category_raw == "EGGS"

    def test_calculates_extended_from_unit_price(self):
        raw = {
            "description": "Bananas",
            "unitPrice": "0.59",
            "quantity": 3,
        }
        item = parse_meijer_item(raw)
        assert item.extended_price == Decimal("1.77")

    def test_discounts_parsed(self):
        raw = {
            "description": "Cereal",
            "unitPrice": "4.99",
            "extendedPrice": "4.99",
            "regularPrice": "5.99",
            "salePrice": "4.99",
            "couponAmount": "1.00",
            "loyaltyAmount": "0.50",
        }
        item = parse_meijer_item(raw)
        assert item.regular_price == Decimal("5.99")
        assert item.sale_price == Decimal("4.99")
        assert item.coupon_discount == Decimal("1.00")
        assert item.loyalty_discount == Decimal("0.50")

    def test_alternate_discount_names(self):
        raw = {
            "description": "Bread",
            "unitPrice": "2.99",
            "extendedPrice": "2.99",
            "couponDiscount": "0.75",
            "loyaltyDiscount": "0.25",
        }
        item = parse_meijer_item(raw)
        assert item.coupon_discount == Decimal("0.75")
        assert item.loyalty_discount == Decimal("0.25")

    def test_missing_fields_default_gracefully(self):
        raw = {"description": "Mystery Item"}
        item = parse_meijer_item(raw)
        assert item.product_name_raw == "Mystery Item"
        assert item.upc is None
        assert item.quantity == Decimal("1")
        assert item.unit_price == Decimal("0")
        assert item.regular_price is None
        assert item.category_raw is None

    def test_no_upc_returns_none(self):
        raw = {"description": "Loose Bananas", "unitPrice": "1.00", "extendedPrice": "1.00"}
        item = parse_meijer_item(raw)
        assert item.upc is None


class TestNormalizeReceipt:
    def test_full_receipt(self):
        user_id = str(uuid.uuid4())
        store_id = str(uuid.uuid4())
        raw = {
            "receiptId": "REC-001",
            "date": "2026-03-15",
            "total": "25.47",
            "subtotal": "23.00",
            "tax": "2.47",
            "savings": "3.00",
            "items": [
                {"description": "Milk", "unitPrice": "3.99", "extendedPrice": "3.99"},
                {"description": "Bread", "unitPrice": "2.50", "extendedPrice": "2.50"},
            ],
        }
        purchase = normalize_receipt(raw, user_id, store_id)
        assert purchase.receipt_id == "REC-001"
        assert purchase.purchase_date == date(2026, 3, 15)
        assert purchase.total == Decimal("25.47")
        assert purchase.subtotal == Decimal("23.00")
        assert purchase.tax == Decimal("2.47")
        assert purchase.savings_total == Decimal("3.00")
        assert len(purchase.items) == 2
        assert purchase.items[0].product_name_raw == "Milk"
        assert purchase.raw_data == raw

    def test_alternate_receipt_fields(self):
        user_id = str(uuid.uuid4())
        store_id = str(uuid.uuid4())
        raw = {
            "receipt_id": "REC-002",
            "purchaseDate": "2026-03-14",
            "totalAmount": "10.00",
            "taxAmount": "0.75",
            "totalSavings": "1.50",
            "items": [],
        }
        purchase = normalize_receipt(raw, user_id, store_id)
        assert purchase.receipt_id == "REC-002"
        assert purchase.purchase_date == date(2026, 3, 14)
        assert purchase.total == Decimal("10.00")
        assert purchase.tax == Decimal("0.75")
        assert purchase.savings_total == Decimal("1.50")

    def test_missing_date_defaults_to_today(self):
        user_id = str(uuid.uuid4())
        store_id = str(uuid.uuid4())
        raw = {"total": "5.00", "items": []}
        purchase = normalize_receipt(raw, user_id, store_id)
        assert purchase.purchase_date == date.today()

    def test_generates_receipt_id_if_missing(self):
        user_id = str(uuid.uuid4())
        store_id = str(uuid.uuid4())
        raw = {"total": "5.00", "date": "2026-03-15", "items": []}
        purchase = normalize_receipt(raw, user_id, store_id)
        assert purchase.receipt_id  # Should be a generated UUID string

    def test_date_object_passthrough(self):
        user_id = str(uuid.uuid4())
        store_id = str(uuid.uuid4())
        raw = {"date": date(2026, 1, 1), "total": "5.00", "items": []}
        purchase = normalize_receipt(raw, user_id, store_id)
        assert purchase.purchase_date == date(2026, 1, 1)
