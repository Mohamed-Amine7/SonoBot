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


def detect_language(text):
    """Return the response language for a customer message.

    This deliberately uses simple, deterministic signals.  It is used before
    shortcuts such as direct catalogue replies, so those replies cannot switch
    an English or Arabic customer back to French.
    """
    if has_arabic(text):
        return "ar"

    words = set(re.findall(r"[a-z0-9']+", normalize_text(text)))
    darija_signals = {
        "chhal", "chnou", "wach", "wash", "fin", "kifach", "alach",
        "bghit", "bgha", "andkom", "andek", "dial", "dyal", "hada",
        "hadi", "kayn", "kayna", "momkin", "bla", "wla", "hta",
        "lli", "chi", "taman", "mzyan", "khdam",
    }
    if len(words & darija_signals) >= 2:
        return "darija"

    english_signals = {
        "do", "you", "have", "what", "how", "can", "is", "are", "the",
        "my", "your", "where", "does", "which", "any", "much", "many", "i",
        "want", "need", "looking", "for", "show", "me", "something", "good",
        "please", "tell", "give", "get", "sell", "buy", "price", "cost",
        "available", "recommend", "best", "right", "help", "would", "like",
        "some", "about", "this", "that", "with", "from", "there", "still",
        "also", "should", "could", "party",
    }
    if len(words & english_signals) >= 2 or words & {"hello", "hi", "hey"}:
        return "en"
    return "fr"


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
    """Extracts model/product tokens, keeping short numbers like 7, 12, 18.
    Preserves reference codes like INF-SM470 as single tokens."""
    normalized = normalize_text(text)
    # First, extract reference codes (patterns like INF-XX123) as single tokens
    ref_codes = re.findall(r'[a-z]{2,4}[-][a-z0-9]+(?:[-][a-z0-9]+)*', normalized)
    # Remove reference codes from text to avoid double-extraction
    for ref in ref_codes:
        normalized = normalized.replace(ref, ' ')
    # Extract remaining individual words
    words = re.findall(r'[a-z0-9]+', normalized)
    stop_words = {
        # French common words
        "ce", "cet", "cette", "est", "que", "qui", "quoi", "et", "ou",
        "le", "la", "les", "des", "un", "une", "du", "de", "dans",
        "pour", "sur", "avec", "sans", "pas", "plus", "moins",
        "vous", "nous", "ils", "elles", "son", "ses", "nos", "vos",
        "votre", "notre", "leur", "leurs", "mon", "ma", "mes", "ton",
        "tout", "tous", "toute", "toutes", "autre", "autres",
        "quel", "quelle", "quels", "quelles", "comment", "pourquoi",
        "encore", "aussi", "mais", "donc", "car", "ni", "bien",
        "ici", "oui", "non", "tres", "trop", "assez", "peu",
        "avoir", "avez", "fait", "faire", "etre", "sont", "sera",
        "chez", "entre", "vers", "comme", "depuis", "avant", "apres",
        "cherche", "recherche", "trouve", "trouver", "besoin", "veux",
        "veut", "donne", "moi", "liste", "nom", "existe",
        # English common words
        "what", "about", "do", "you", "have", "is", "are", "the",
        "can", "how", "where", "which", "any", "some", "this", "that",
        "product", "products", "please", "show", "find", "search",
        "still", "get", "need", "want", "looking", "for", "your",
        "much", "many", "more", "does", "there", "give", "tell",
        # Catalog / commerce stop words
        "inf", "ref", "reference", "produit", "disponible", "stock",
        "prix", "combien", "coute", "taman", "dyal", "dial",
    }
    filtered_words = [word for word in words if word not in stop_words]
    return ref_codes + filtered_words
