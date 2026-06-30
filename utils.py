"""
SonoBot — Text Utilities
Normalization, keyword extraction, and language detection helpers.
"""

import re
import unicodedata


def normalize_text(text):
    """Lowercases text and removes accents for robust intent matching."""
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_search_key(text):
    """Normalizes names so punctuation and spaces do not break exact checks."""
    return re.sub(r"[^a-z0-9]+", "", normalize_text(str(text)))


def has_arabic(text):
    """Returns True if the text contains Arabic/Darija script characters."""
    return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text))


def extract_keywords(text):
    """
    Cleans user input and extracts meaningful keywords for database searching,
    removing common English, French, Arabic, and Darija stop words.
    """
    words = re.findall(r'\b\w{3,}\b', text.lower())

    stop_words = {
        # English
        'the', 'and', 'are', 'for', 'you', 'with', 'from', 'that', 'this',
        'have', 'has', 'had', 'what', 'where', 'when', 'how', 'who', 'why',
        'please', 'show', 'list', 'about', 'some', 'many', 'much', 'your',
        'store', 'shop', 'website', 'item', 'items', 'product', 'products',
        'tell', 'info', 'information', 'details', 'price', 'prices', 'cost',
        'expensive', 'cheap', 'buy', 'purchase', 'order', 'sell', 'find', 'search',
        # French
        'avez', 'avoir', 'vous', 'votre', 'vos', 'des', 'les', 'une', 'dans',
        'pour', 'avec', 'materiel', 'materiels', 'matériel', 'matériels',
        'produit', 'produits', 'prix', 'disponible', 'disponibles',
        'est', 'que', 'qui', 'sur', 'pas', 'sont', 'mais', 'aussi',
        'tout', 'tous', 'cette', 'ces', 'son', 'ses', 'nos',
        # Arabic / Darija common stop words
        'هل', 'ما', 'هذا', 'هذه', 'من', 'في', 'على', 'إلى', 'عن',
        'أن', 'كان', 'لقد', 'هو', 'هي', 'نحن', 'أنا', 'أنت', 'كل',
        'أو', 'لا', 'نعم', 'ذلك', 'تلك', 'بعد', 'قبل', 'عند', 'كيف',
        'لماذا', 'أين', 'متى', 'ماذا', 'كم', 'أريد', 'يمكن', 'يمكنني',
        'واش', 'فين', 'كيفاش', 'علاش', 'شحال', 'بغيت', 'عندكم', 'عندك',
        'ممكن', 'بلا', 'ولا', 'حتى', 'ديال', 'لي', 'اللي', 'شي',
    }

    return [word for word in words if word not in stop_words]


def extract_product_keywords(text):
    """Extracts model/product tokens, keeping short numbers like 7, 12, 18."""
    words = re.findall(r'[a-z0-9]+', normalize_text(text))
    stop_words = {
        "ce", "cet", "cette", "est", "que", "qui", "quoi", "et", "ou",
        "le", "la", "les", "des", "un", "une", "du", "de", "dans",
        "cherche", "recherche", "trouve", "trouver", "besoin", "veux",
        "veut", "donne", "moi", "liste", "nom", "existe", "avez",
        "what", "about", "do", "you", "have", "is", "are", "the",
        "product", "products", "please", "show", "find", "search",
    }
    return [word for word in words if word not in stop_words]
