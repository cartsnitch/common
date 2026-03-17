"""Tests for product normalization module."""

import uuid
from datetime import UTC, datetime

from cartsnitch_common.models.product import NormalizedProduct
from cartsnitch_common.normalization import (
    MatchMethod,
    clean_name,
    extract_size_info,
    jaccard_similarity,
    match_by_name,
    match_by_upc,
    normalize_product,
)


class TestCleanName:
    def test_lowercase(self):
        assert clean_name("Kroger WHOLE MILK") == "kroger whole milk"

    def test_removes_size_info(self):
        assert "oz" not in clean_name("Milk 16 oz Whole")

    def test_removes_noise_words(self):
        cleaned = clean_name("The Original Brand Milk")
        assert "the" not in cleaned.split()
        assert "original" not in cleaned.split()
        assert "brand" not in cleaned.split()

    def test_collapses_whitespace(self):
        assert "  " not in clean_name("Milk   Whole   Gallon")

    def test_removes_punctuation(self):
        cleaned = clean_name("Meijer's Best (Organic) Milk!")
        assert "'" not in cleaned
        assert "(" not in cleaned


class TestExtractSizeInfo:
    def test_extracts_oz(self):
        result = extract_size_info("Cereal 18 oz box")
        assert result == ("18", "oz")

    def test_extracts_fl_oz(self):
        result = extract_size_info("Juice 64 fl oz")
        assert result == ("64", "fl_oz")

    def test_extracts_lb(self):
        result = extract_size_info("Ground Beef 1.5 lb")
        assert result == ("1.5", "lb")

    def test_extracts_ct(self):
        result = extract_size_info("Eggs Large 12 ct")
        assert result == ("12", "ct")

    def test_no_size_returns_none(self):
        assert extract_size_info("Bananas") is None


class TestJaccardSimilarity:
    def test_identical_strings(self):
        assert jaccard_similarity("whole milk gallon", "whole milk gallon") == 1.0

    def test_completely_different(self):
        assert jaccard_similarity("apple juice", "ground beef") == 0.0

    def test_partial_overlap(self):
        score = jaccard_similarity("kroger whole milk", "meijer whole milk")
        assert 0.4 < score < 0.8  # "whole" and "milk" overlap

    def test_empty_strings(self):
        assert jaccard_similarity("", "") == 0.0
        assert jaccard_similarity("milk", "") == 0.0


class TestMatchByUPC:
    def test_match_found(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Whole Milk, Gallon",
            upc_variants=["0041250000001", "0041250000002"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.commit()
        # SQLite doesn't support JSONB containment — this will raise
        # In production (PostgreSQL), this would work
        result = match_by_upc(session, "0041250000001")
        assert result is not None
        assert result.method == MatchMethod.UPC
        assert result.confidence == 1.0

    def test_no_match(self, session):
        result = match_by_upc(session, "9999999999999")
        assert result is None


class TestMatchByName:
    def test_exact_name_match(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Whole Milk, Gallon",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.commit()
        result = match_by_name(session, "Whole Milk Gallon")
        assert result is not None
        assert result.method == MatchMethod.NAME
        assert result.confidence > 0.5

    def test_fuzzy_match(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Kroger Whole Milk, 1 Gallon",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.commit()
        result = match_by_name(session, "Meijer Whole Milk 1 Gallon", threshold=0.3)
        assert result is not None
        assert result.confidence > 0.3

    def test_no_match_below_threshold(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Ground Beef 80/20",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.commit()
        result = match_by_name(session, "Apple Juice 64 oz", threshold=0.5)
        assert result is None


class TestNormalizeProduct:
    def test_name_fallback(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Large Eggs, 12 count",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.commit()
        result = normalize_product(session, "Large Eggs 12 ct", upc=None)
        assert result is not None
        assert result.method == MatchMethod.NAME

    def test_no_match(self, session):
        result = normalize_product(session, "Nonexistent Product XYZ", upc=None)
        assert result is None
