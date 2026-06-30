"""
Tests for SonoBot guide & direct catalog response logic.
"""

import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import has_arabic, normalize_text
from guide import is_guide_trigger


class TestIsGuideTrigger:
    """Tests for the guided conversation trigger detection."""

    def test_french_help_phrases(self):
        assert is_guide_trigger("aide moi à choisir") is True
        assert is_guide_trigger("conseillez moi") is True
        assert is_guide_trigger("je sais pas quoi prendre") is True
        assert is_guide_trigger("je suis perdu") is True

    def test_english_help_phrases(self):
        assert is_guide_trigger("help me choose") is True
        assert is_guide_trigger("I'm not sure what to pick") is True

    def test_keyword_triggers(self):
        assert is_guide_trigger("des suggestions ?") is True
        assert is_guide_trigger("une recommandation svp") is True

    def test_no_trigger_on_normal_questions(self):
        assert is_guide_trigger("bonjour") is False
        assert is_guide_trigger("quels produits avez-vous ?") is False
        assert is_guide_trigger("prix du laser") is False

    def test_no_trigger_on_arabic(self):
        """Arabic messages should not trigger the guide (AI handles them)."""
        assert is_guide_trigger("ساعدني نختار") is False
        assert is_guide_trigger("واش عندكم شي اقتراح") is False


class TestDirectCatalogResponseGreetings:
    """Tests for greeting detection in direct_catalog_response."""

    def test_french_greetings_return_response(self):
        from guide import direct_catalog_response

        result = direct_catalog_response("bonjour")
        assert result is not None
        assert "SonoBot" in result

        result = direct_catalog_response("salut")
        assert result is not None

    def test_english_greetings_return_none(self):
        """English greetings should fall through to AI for English reply."""
        from guide import direct_catalog_response

        assert direct_catalog_response("hello") is None
        assert direct_catalog_response("hi") is None

    def test_arabic_returns_none(self):
        """Arabic messages should fall through to AI."""
        from guide import direct_catalog_response

        assert direct_catalog_response("مرحبا") is None
        assert direct_catalog_response("السلام عليكم") is None


class TestLanguageDetection:
    """Tests for language-related utilities used by the guide."""

    def test_arabic_detection(self):
        assert has_arabic("مرحبا") is True
        assert has_arabic("واش عندكم") is True

    def test_non_arabic(self):
        assert has_arabic("Bonjour") is False
        assert has_arabic("Hello world") is False

    def test_darija_mixed(self):
        """Darija often mixes Arabic script with numbers/latin."""
        assert has_arabic("3ndkom chi laser?") is False
        assert has_arabic("عندكم شي laser?") is True
