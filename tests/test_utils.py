"""
Tests for SonoBot text utilities.
"""

import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import normalize_text, normalize_search_key, extract_keywords, extract_product_keywords, has_arabic


class TestNormalizeText:
    def test_lowercases(self):
        assert normalize_text("HELLO") == "hello"

    def test_removes_accents(self):
        assert normalize_text("éclairage") == "eclairage"
        assert normalize_text("matériel") == "materiel"

    def test_combined(self):
        assert normalize_text("Événement Spécial") == "evenement special"

    def test_empty(self):
        assert normalize_text("") == ""


class TestNormalizeSearchKey:
    def test_removes_punctuation_and_spaces(self):
        assert normalize_search_key("Beam 230W 7R") == "beam230w7r"

    def test_removes_accents(self):
        assert normalize_search_key("Éclairage LED") == "eclairageled"

    def test_empty(self):
        assert normalize_search_key("") == ""


class TestHasArabic:
    def test_arabic_text(self):
        assert has_arabic("مرحبا كيفاش") is True

    def test_french_text(self):
        assert has_arabic("Bonjour, comment allez-vous ?") is False

    def test_mixed(self):
        assert has_arabic("Hello مرحبا") is True

    def test_empty(self):
        assert has_arabic("") is False


class TestExtractKeywords:
    def test_removes_stop_words(self):
        keywords = extract_keywords("what products do you have in the store")
        assert "what" not in keywords
        assert "you" not in keywords
        assert "the" not in keywords

    def test_keeps_meaningful_words(self):
        keywords = extract_keywords("laser beam waterproof")
        assert "laser" in keywords
        assert "beam" in keywords
        assert "waterproof" in keywords

    def test_removes_french_stop_words(self):
        keywords = extract_keywords("avez vous des produits disponibles")
        assert "avez" not in keywords
        assert "vous" not in keywords
        assert "des" not in keywords

    def test_short_words_ignored(self):
        keywords = extract_keywords("is it ok")
        # All words < 3 chars should be excluded
        assert "is" not in keywords
        assert "it" not in keywords
        assert "ok" not in keywords


class TestExtractProductKeywords:
    def test_extracts_product_tokens(self):
        keywords = extract_product_keywords("LED Par 18x18W")
        assert "led" in keywords
        assert "par" in keywords
        assert "18x18w" in keywords

    def test_removes_common_words(self):
        keywords = extract_product_keywords("je cherche un produit LED")
        assert "cherche" not in keywords
        assert "led" in keywords

    def test_empty_input(self):
        assert extract_product_keywords("") == []
