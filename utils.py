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
    """Return the response language ('en', 'fr', 'ar', 'darija') for a customer message.

    Uses robust keyword signaling and pattern detection to accurately identify
    the user's intended language and prevent language inertia in chat history.
    """
    if not text or not str(text).strip():
        return "fr"

    if has_arabic(text):
        # Check if Arabic script contains distinct Moroccan Darija keywords (cleaned from punctuation)
        darija_ar_keywords = {
            "واش", "فين", "كيفاش", "علاش", "بغيت", "كاين", "كاينة", "ديال",
            "شحال", "بزاف", "مزيان", "عافاك", "عفاك", "عندكم", "خويا", "بشحال",
            "دابا", "واخا", "شي", "زوين", "هاد", "هادا", "هادي", "درهم", "لاباس", "سلام",
        }
        words_ar = set(re.findall(r'[\u0600-\u06FF]+', text))
        if words_ar & darija_ar_keywords:
            return "darija"
        return "ar"

    normalized = normalize_text(text)
    words = set(re.findall(r"[a-z0-9'379]+", normalized))

    # Moroccan Darija in Latin script (Arabizi / Darija)
    # Strong single-word Darija indicators that unambiguously identify Darija (no English/French collisions)
    strong_darija = {
        "bghit", "3afak", "afak", "kifach", "dyal", "dial", "3ndkom", "andkom",
        "kayn", "kayna", "bezzaf", "bzaf", "nsewlek", "mzyan", "chhal", "shhal",
        "wach", "chnou", "chno", "khoya", "salam", "labas", "marhba", "merhba",
        "wakha", "daba", "chouf", "drari", "walou",
    }
    darija_signals = strong_darija | {
        "wash", "ach", "ash", "fin", "feen", "taman", "hadi", "hada", "momkin",
        "bla", "wla", "hta", "lli", "chi", "khdam", "chwia", "koulchi",
    }

    english_signals = {
        "do", "you", "have", "what", "how", "can", "is", "are", "the",
        "my", "your", "where", "does", "which", "any", "much", "many", "i",
        "want", "need", "looking", "for", "show", "me", "something", "good",
        "please", "tell", "give", "get", "sell", "buy", "price", "cost",
        "available", "recommend", "best", "right", "help", "would", "like",
        "some", "about", "this", "that", "with", "from", "there", "still",
        "also", "should", "could", "party", "why", "who", "when", "doing",
        "questions", "question", "difference", "between", "explain", "marriage",
        "wedding", "lights", "light", "speaker", "speakers", "shipping",
        "delivery", "stock", "product", "products", "thanks", "thank",
        "hello", "hi", "hey", "yes", "no", "ok", "okay", "dont", "trouble",
        "roadmap", "suit", "beams", "beam", "wash", "wall", "moving", "head",
    }
    english_starters = {"hello", "hi", "hey", "thanks", "thank", "why", "how", "what", "where", "can", "could", "would", "do", "does", "is", "are"}

    en_matches = len(words & english_signals)
    fr_signals = {
        "bonjour", "bonsoir", "salut", "merci", "svp", "prix", "combien",
        "livraison", "est", "ce", "que", "je", "voudrais", "recherche",
        "cherche", "pour", "une", "des", "les", "avec", "dans", "mariage",
        "soiree", "difference", "entre", "pouvez", "vous", "avoir", "magasin",
        "materiel", "garantie", "delai", "paiement", "compte", "mot", "passe",
        "oublié", "oublie", "aidez", "moi", "quoi", "quel", "quelle", "quels",
    }
    fr_matches = len(words & fr_signals)

    darija_matches = len(words & strong_darija)
    all_darija = len(words & darija_signals)

    # If there are clear Darija words and it's not predominantly English:
    if (darija_matches >= 1 or all_darija >= 2) and (darija_matches >= en_matches or en_matches < 2):
        return "darija"

    if (words & english_starters and en_matches >= 1) or en_matches >= 2:
        if en_matches >= fr_matches:
            return "en"

    if darija_matches >= 1 or all_darija >= 2:
        return "darija"

    if fr_matches >= 2 or words & {"bonjour", "bonsoir", "salut", "merci"}:
        return "fr"

    if en_matches > fr_matches:
        return "en"

    return "fr"


def extract_keywords(text):
    """
    Cleans user input and extracts meaningful keywords for database searching,
    removing common English, French, Arabic, and Darija stop words.
    """
    words = re.findall(r'\b\w{3,}\b', text.lower())

    stop_words = {
        # English — determiners, pronouns, prepositions, conjunctions
        'the', 'and', 'are', 'for', 'you', 'with', 'from', 'that', 'this',
        'have', 'has', 'had', 'what', 'where', 'when', 'how', 'who', 'why',
        'please', 'show', 'list', 'about', 'some', 'many', 'much', 'your',
        'tell', 'info', 'information', 'details',
        'not', 'but', 'also', 'just', 'only', 'very', 'really', 'quite',
        'been', 'being', 'will', 'would', 'could', 'should', 'shall', 'might',
        'may', 'can', 'did', 'does', 'done', 'got', 'get', 'gets',
        'its', 'it', 'they', 'them', 'their', 'his', 'her', 'him',
        'our', 'ours', 'yours', 'mine', 'myself', 'here', 'there',
        'then', 'than', 'too', 'own', 'same', 'other', 'each', 'every',
        'both', 'few', 'all', 'any', 'most', 'more', 'less',
        'into', 'over', 'under', 'after', 'before', 'between',
        'through', 'during', 'above', 'below', 'against', 'along',
        # English — commerce / chatbot filler words
        'store', 'shop', 'website', 'item', 'items', 'product', 'products',
        'price', 'prices', 'cost', 'costs',
        'expensive', 'cheap', 'buy', 'purchase', 'order', 'sell',
        'find', 'search', 'looking', 'look', 'want', 'need',
        'like', 'would', 'could', 'still', 'already', 'anymore',
        'offer', 'offers', 'available', 'inventory',
        'machine', 'machines', 'equipment', 'device', 'devices',
        'type', 'types', 'kind', 'kinds', 'sort', 'sorts',
        'model', 'models', 'brand', 'brands',
        # French — determiners, pronouns, prepositions, conjunctions
        'avez', 'avoir', 'vous', 'votre', 'vos', 'des', 'les', 'une', 'dans',
        'pour', 'avec', 'sans', 'chez', 'entre', 'vers', 'depuis',
        'materiel', 'materiels', 'mat\u00e9riel', 'mat\u00e9riels',
        'produit', 'produits', 'prix', 'disponible', 'disponibles',
        'est', 'que', 'qui', 'sur', 'pas', 'sont', 'mais', 'aussi',
        'tout', 'tous', 'toute', 'toutes', 'cette', 'ces', 'son', 'ses', 'nos',
        'encore', 'quand', 'quels', 'quel', 'quelle', 'quelles',
        'machines', 'machine', 'appareil', 'appareils',
        'bon', 'bons', 'bonne', 'bonnes', 'bien', 'mieux',
        'comment', 'pourquoi', 'combien', 'quoi',
        'donc', 'car', 'comme', 'avant', 'apres', 'pendant',
        'peu', 'beaucoup', 'trop', 'tres', 'assez',
        'autre', 'autres', 'meme', 'ainsi', 'cela', 'ceci',
        'oui', 'non', 'peut', 'pouvoir', 'peuvent',
        'fait', 'faire', 'etre', 'sera', 'serait', 'etait',
        'ici', 'voila', 'voici', 'entre',
        'mon', 'mes', 'ton', 'tes', 'leur', 'leurs', 'notre',
        'lui', 'elle', 'eux', 'elles', 'ils', 'nous', 'moi', 'toi',
        'suis', 'sommes', 'etes', 'etais', 'avons', 'ont', 'avait',
        'veux', 'veut', 'vouloir', 'voudrais', 'voudrait',
        'donne', 'donner', 'donnez',
        'cherche', 'recherche', 'trouve', 'trouver', 'besoin',
        'dit', 'dire', 'disent', 'parle', 'parler',
        'faut', 'falloir', 'doit', 'devoir', 'devrait',
        'voir', 'savoir', 'sait', 'connait', 'connaitre',
        'existe', 'exister', 'reste', 'rester',
        'prendre', 'prend', 'prenez', 'pris',
        'mettre', 'met', 'mettez', 'mis',
        'nom', 'liste', 'type', 'genre', 'sorte', 'modele',
        'marque', 'gamme', 'serie', 'version', 'variante',
        # Arabic / Darija common stop words
        'هل', 'ما', 'هذا', 'هذه', 'من', 'في', 'على', 'إلى', 'عن',
        'أن', 'كان', 'لقد', 'هو', 'هي', 'نحن', 'أنا', 'أنت', 'كل',
        'أو', 'لا', 'نعم', 'ذلك', 'تلك', 'بعد', 'قبل', 'عند', 'كيف',
        'لماذا', 'أين', 'متى', 'ماذا', 'كم', 'أريد', 'يمكن', 'يمكنني',
        'واش', 'فين', 'كيفاش', 'علاش', 'شحال', 'بغيت', 'عندكم', 'عندك',
        'ممكن', 'بلا', 'ولا', 'حتى', 'ديال', 'لي', 'اللي', 'شي',
        'هاد', 'هاذ', 'ديال', 'دي', 'ولا', 'يلا', 'إلا',
        'واحد', 'شي', 'بحال', 'كيما', 'فاش', 'منين',
        'عافاك', 'بغينا', 'بغيتي', 'كاين', 'كاينة',
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
        # French — determiners, pronouns, prepositions, conjunctions
        "ce", "cet", "cette", "est", "que", "qui", "quoi", "et", "ou",
        "le", "la", "les", "des", "un", "une", "du", "de", "dans",
        "pour", "sur", "avec", "sans", "pas", "plus", "moins",
        "vous", "nous", "ils", "elles", "son", "ses", "nos", "vos",
        "votre", "notre", "leur", "leurs", "mon", "ma", "mes", "ton",
        "tout", "tous", "toute", "toutes", "autre", "autres",
        "quel", "quelle", "quels", "quelles", "comment", "pourquoi",
        "encore", "aussi", "mais", "donc", "car", "ni", "bien", "quand",
        "ici", "oui", "non", "tres", "trop", "assez", "peu",
        "avoir", "avez", "fait", "faire", "etre", "sont", "sera",
        "chez", "entre", "vers", "comme", "depuis", "avant", "apres",
        "pendant", "beaucoup", "meme", "ainsi", "cela", "ceci",
        "peut", "pouvoir", "peuvent", "faut", "falloir",
        "doit", "devoir", "devrait",
        "suis", "sommes", "etes", "etais", "avons", "ont", "avait",
        "serait", "etait", "voila", "voici",
        "lui", "elle", "eux",
        "bon", "bons", "bonne", "bonnes", "mieux",
        # French — chatbot / commerce filler
        "cherche", "recherche", "trouve", "trouver", "besoin", "veux",
        "veut", "vouloir", "voudrais", "voudrait",
        "donne", "donner", "donnez", "moi", "liste", "nom", "existe",
        "voir", "savoir", "sait", "connait", "connaitre",
        "prendre", "prend", "prenez", "pris",
        "mettre", "met", "mettez", "mis",
        "dit", "dire", "disent", "parle", "parler",
        "reste", "rester", "exister",
        "type", "genre", "sorte", "modele",
        "marque", "gamme", "serie", "version", "variante",
        "appareil", "appareils", "machine", "machines",
        # English — determiners, pronouns, prepositions
        "what", "about", "do", "you", "have", "is", "are", "the",
        "can", "how", "where", "which", "any", "some", "this", "that",
        "product", "products", "please", "show", "find", "search",
        "still", "get", "need", "want", "looking", "for", "your",
        "much", "many", "more", "does", "there", "give", "tell",
        "not", "but", "just", "only", "very", "really", "quite",
        "been", "being", "will", "would", "could", "should",
        "may", "might", "did", "done", "got", "gets",
        "its", "they", "them", "their", "his", "her", "him",
        "our", "ours", "yours", "mine", "here",
        "then", "than", "too", "own", "same", "other",
        "each", "every", "both", "few", "all", "most", "less",
        "into", "over", "under", "after", "before", "between",
        "through", "during", "above", "below", "against", "along",
        "like", "already", "anymore",
        "offer", "offers", "available", "inventory",
        "machine", "machines", "equipment", "device", "devices",
        "type", "types", "kind", "kinds", "sort", "sorts",
        "model", "models", "brand", "brands",
        # Catalog / commerce stop words
        "inf", "ref", "reference", "produit", "disponible", "stock",
        "prix", "combien", "coute", "taman", "dyal", "dial",
        # Darija (Latin) common stop words
        "wach", "wash", "chnou", "chhal", "kifach", "alach",
        "bghit", "bgha", "andkom", "andek", "hada", "hadi",
        "kayn", "kayna", "momkin", "bla", "wla", "hta",
        "lli", "chi", "mzyan", "khdam", "bezzaf",
    }
    filtered_words = [word for word in words if word not in stop_words]
    return ref_codes + filtered_words
