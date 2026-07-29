"""
SonoBot — Guided Conversation & Direct Catalog Response
Step-by-step product recommendation wizard and instant catalog answers.
"""

import re
import logging

from utils import normalize_text, normalize_search_key, detect_language
from catalog import (
    fetch_categories, find_requested_category, fetch_products_by_category,
    fetch_products, fetch_product_matches, format_product_list, format_category_list,
)
from config import CATALOG_LIST_LIMIT

logger = logging.getLogger("sonobot.guide")


GUIDE_COPY = {
    "en": {
        "questions": [
            "To recommend the right products, what kind of event are you preparing? 🎯",
            "Will the event be indoors or outdoors? 🏠☀️",
            "What is your approximate budget? 💰",
            "Which lighting effect are you looking for? ✨",
        ],
        "event": ["Wedding / party", "Concert / show", "Club / nightclub", "Bar / restaurant", "Outdoor event", "Studio / filming"],
        "environment": ["Indoor", "Outdoor", "Both"],
        "budget": ["Budget-friendly", "Mid-range", "Premium", "No set budget"],
        "effect": ["Beam", "Wash / ambience", "Laser", "LED / Par", "Moving head", "Any type"],
        "recommendations": "🎯 Based on your needs, here are my recommendations:",
        "fallback": "I could not find an exact match, but here are a few suggestions:",
        "no_results": "Sorry, I could not find suitable products right now. Please contact our support team for tailored advice.",
        "follow_up": "💬 Would you like more details about a product?",
    },
    "ar": {
        "questions": [
            "لكي أساعدك في الاختيار، ما نوع المناسبة التي تحضّر لها؟ 🎯",
            "هل ستكون المناسبة في الداخل أم في الخارج؟ 🏠☀️",
            "ما هي ميزانيتك التقريبية؟ 💰",
            "ما نوع التأثير الضوئي الذي تبحث عنه؟ ✨",
        ],
        "event": ["عرس / حفلة", "حفل موسيقي / عرض", "نادي ليلي", "بار / مطعم", "فعالية خارجية", "استوديو / تصوير"],
        "environment": ["داخلي", "خارجي", "كلاهما"],
        "budget": ["اقتصادي", "متوسط", "احترافي", "لا توجد ميزانية محددة"],
        "effect": ["Beam", "Wash / أجواء", "ليزر", "LED / Par", "رأس متحرك", "أي نوع"],
        "recommendations": "🎯 بناءً على احتياجاتك، هذه هي المنتجات المقترحة:",
        "fallback": "لم أجد تطابقًا دقيقًا، لكن إليك بعض الاقتراحات:",
        "no_results": "عذرًا، لم أجد منتجات مناسبة الآن. يُرجى التواصل مع الدعم للحصول على مساعدة مخصصة.",
        "follow_up": "💬 هل تريد تفاصيل أكثر عن أحد المنتجات؟",
    },
}


def get_guide_step(step, language="fr"):
    """Return one guide question and its labels in the customer's language."""
    if language not in GUIDE_COPY:
        return GUIDE_STEPS[step]

    copy = GUIDE_COPY[language]
    option_groups = {1: "event", 2: "environment", 3: "budget", 4: "effect"}
    base_options = GUIDE_STEPS[step]["options"]
    return {
        "question": copy["questions"][step - 1],
        "options": [
            {**option, "label": label}
            for option, label in zip(base_options, copy[option_groups[step]])
        ],
    }


def guide_copy(language, key):
    return GUIDE_COPY.get(language, {}).get(key)

# ---------------------------------------------------------------------------
# Guided Conversation Steps
# ---------------------------------------------------------------------------

GUIDE_STEPS = {
    1: {
        "question": "Pour mieux vous conseiller, quel type d'événement préparez-vous ? 🎯",
        "options": [
            {"label": "🎉 Mariage / Fête", "value": "mariage"},
            {"label": "🎵 Concert / Spectacle", "value": "concert"},
            {"label": "🎧 Club / Discothèque", "value": "club"},
            {"label": "🍷 Bar / Restaurant", "value": "bar"},
            {"label": "🌳 Événement extérieur", "value": "exterieur"},
            {"label": "🎬 Studio / Tournage", "value": "studio"},
        ],
    },
    2: {
        "question": "L'événement sera en intérieur ou en extérieur ? 🏠🌤️",
        "options": [
            {"label": "🏠 Intérieur", "value": "interieur"},
            {"label": "🌤️ Extérieur", "value": "exterieur"},
            {"label": "🔄 Les deux", "value": "both"},
        ],
    },
    3: {
        "question": "Quel est votre budget approximatif ? 💰",
        "options": [
            {"label": "💰 Économique", "value": "low"},
            {"label": "💰💰 Moyen", "value": "mid"},
            {"label": "💎 Haut de gamme", "value": "high"},
            {"label": "🤷 Pas de budget précis", "value": "any"},
        ],
    },
    4: {
        "question": "Quel type d'effet lumineux recherchez-vous ? ✨",
        "options": [
            {"label": "💡 Beam (faisceaux)", "value": "beam"},
            {"label": "🌈 Wash (ambiance)", "value": "wash"},
            {"label": "⚡ Laser", "value": "laser"},
            {"label": "🔆 LED / Par", "value": "led"},
            {"label": "🎯 Moving Head", "value": "moving"},
            {"label": "🌟 Tout type", "value": "any"},
        ],
    },
}


def _word_match(word, text):
    """Check if a word exists as a whole word in text (not as substring)."""
    return bool(re.search(r'\b' + re.escape(word) + r'\b', text))


def _any_word_match(words, text):
    """Check if any of the words exist as whole words in text."""
    return any(_word_match(w, text) for w in words)


def is_guide_trigger(user_message):
    """Detects when a user needs guided product assistance."""
    message = normalize_text(user_message)
    compact = re.sub(r"[^a-z0-9\s]", " ", message)

    phrase_triggers = [
        # French triggers
        "sais pas", "connais pas", "aide moi", "aidez moi",
        "conseillez moi", "conseille moi", "guide moi", "guidez moi",
        "quoi choisir", "quoi prendre", "pas sur", "pas sure",
        "pas decide", "suis perdu", "suis perdue",
        "recommandez", "recommande moi", "besoin aide",
        "c est quoi le mieux", "meilleur choix",
        "orienter", "orientez moi", "oriente moi",
        "guide d achat", "guidez moi", "aidez moi a choisir",
        # English triggers
        "help me choose", "not sure", "don t know",
        "guide me", "help me pick", "recommend me",
        "choose the right", "which one should", "what should i get",
        "what do you recommend", "help me find", "help me select",
        "i need guidance", "i need help choosing",
        "something good for", "for a party", "for my party",
        # Darija triggers (Latin script)
        "3awni nkhtar", "chnou khass", "ach ghadi nakhod",
    ]
    if any(phrase in compact for phrase in phrase_triggers):
        return True

    # Arabic triggers
    arabic_triggers = [
        "ساعدني", "ساعدوني", "نصحني", "أنصحني", "وجهني",
        "اختار", "نختار", "شنو نختار", "شنو نأخذ",
        "دليل", "ارشدني", "مساعدة",
    ]
    if any(trigger in user_message for trigger in arabic_triggers):
        return True

    word_triggers = {
        "suggestion", "suggestions", "recommandation", "recommandations",
        "indecis", "hesit", "hesite", "guidance", "recommend",
    }
    return any(word in compact for word in word_triggers)


def guide_product_search(criteria):
    """Search products based on guided conversation criteria."""
    effect_type = criteria.get("effect_type", "any")
    environment = criteria.get("environment", "")

    effect_map = {
        "beam": "beam light",
        "wash": "wash light",
        "laser": "laser",
        "led": "LED par light",
        "moving": "moving head",
    }

    search_parts = []
    if effect_type in effect_map:
        search_parts.append(effect_map[effect_type])

    if environment in ("exterieur", "both"):
        search_parts.append("waterproof IP65")

    search_message = " ".join(search_parts) if search_parts else "light"
    products = fetch_product_matches(search_message, limit=20)

    # If outdoor was requested and we got results, prefer waterproof ones
    if environment in ("exterieur", "both") and products:
        waterproof = [
            p for p in products
            if any(
                kw in normalize_text(p.get("name", "") + " " + str(p.get("description", "")))
                for kw in ("waterproof", "ip65", "ip54", "outdoor")
            )
        ]
        if waterproof:
            products = waterproof

    return products[:8] if products else []


# ---------------------------------------------------------------------------
# Direct Catalog Response (instant DB answers without AI)
# ---------------------------------------------------------------------------


def _filter_by_relevance(products, user_message):
    """Filters product results to keep only the most relevant matches.

    1. If a product name is an exact substring of the user query, return only that.
    2. Otherwise, keep products scoring >= 50% of the best relevance score.
    """
    if not products:
        return products

    # Check for exact name match inside user message
    requested_key = normalize_search_key(user_message)
    exact = [
        p for p in products
        if normalize_search_key(p.get("name", ""))
        and normalize_search_key(p.get("name", "")) in requested_key
    ]
    if exact:
        return exact[:1]

    # Score-based filtering
    if len(products) > 1 and "relevance_score" in products[0]:
        max_score = float(products[0]["relevance_score"])
        if max_score > 0:
            products = [
                p for p in products
                if float(p["relevance_score"]) >= max_score * 0.5
            ]
    return products


def direct_catalog_response(user_message):
    """Returns instant database answers for common shopping questions.
    Skips to AI when the message is in Arabic/Darija or English so
    the AI can reply in the customer's language."""
    message = normalize_text(user_message)
    compact_message = re.sub(r"[^a-z0-9$€.\s]", " ", message)

    # Catalogue shortcuts contain fixed French copy. Keep them exclusively for
    # French; all other languages continue to the language-aware response path.
    if detect_language(user_message) != "fr":
        return None

    # English greetings — let AI handle so it replies in English
    if compact_message.strip() in {'hi', 'hello', 'hey'}:
        return None

    # French / universal greetings — reply in French (default language)
    if compact_message.strip() in {'salam', 'bonjour', 'salut', 'labas', 'ahlan', 'marhba'}:
        return (
            "Bonjour ! 😊 Je suis SonoBot, votre assistant SonoLight. "
            "Je peux vous aider à trouver des produits, vérifier les prix et la disponibilité. "
            "Comment puis-je vous aider ?"
        )

    # --- AI-bypass: questions that need reasoning, not a raw product list ---
    needs_ai = any(
        phrase in compact_message
        for phrase in (
            "commande", "commander", "acheter", "comment", "pourquoi",
            "difference", "comparer", "comparaison", "entre",
            "assister", "aider", "expliquer", "explication",
            "livraison", "paiement", "retour", "garantie",
            "mot de passe", "password", "compte",
            "probleme", "reclamation", "support",
        )
    )
    if needs_ai:
        return None

    price_match = re.search(r"(?:\$|€|mad\s*)?(\d+(?:\.\d{1,2})?)", compact_message)
    product_search_signals = _any_word_match(
        ("cherche", "recherche", "trouve", "trouver", "existe"), compact_message
    )
    product_name_terms = _any_word_match(
        ("light", "laser", "beam", "wash", "waterproof", "flat", "par", "pcs", "led", "in1"), compact_message
    )
    price_search_signals = _any_word_match(
        ("prix", "price", "mad", "dh", "dhs", "moins", "dessous", "plus", "dessus", "budget"), compact_message
    )
    asks_count = _any_word_match(("nombre", "combien", "count", "total"), compact_message)
    asks_quantity = _any_word_match(("quantite", "quantity", "stock"), compact_message)
    asks_catalog = _any_word_match(
        (
            "produit", "produits", "catalogue", "disponible", "disponibles", "stock", "prix", "mad",
            "materiel", "materiels", "eclairage", "deejay", "dj", "categorie", "categories",
            "light", "laser", "beam", "wash", "waterproof", "flat", "par", "pcs", "led", "in1",
            "coup", "coeur", "quantite", "nombre", "combien",
        ), compact_message
    ) or product_search_signals

    if not asks_catalog:
        return None

    asks_category_list = (
        "categorie" in compact_message or "categories" in compact_message
    ) and not any(word in compact_message for word in ("produit", "produits", "nombre", "combien"))

    if asks_category_list:
        return format_category_list(fetch_categories())

    # --- COUNT: "combien / nombre de produits dans la catégorie X" ---
    if asks_count:
        categories = fetch_categories()
        requested_category = find_requested_category(user_message, categories)
        if requested_category:
            products = fetch_products_by_category(requested_category, limit=1000)
            count = len(products)
            return f"La catégorie **{requested_category}** contient **{count}** produit{'s' if count != 1 else ''}."
        all_products = fetch_products(limit=None)
        total = len(all_products) if all_products else 0
        return f"Le catalogue contient actuellement **{total}** produit{'s' if total != 1 else ''} au total."

    # --- QUANTITY: "quelle est la quantité du produit X" ---
    if asks_quantity and not asks_count:
        products = _filter_by_relevance(
            fetch_product_matches(user_message, limit=5), user_message
        )
        if products:
            lines = ["Voici la quantité disponible :"]
            for product in products:
                stock_count = int(product["stock"] or 0)
                if stock_count >= 999999:
                    qty_label = "Disponible (quantité illimitée)"
                elif stock_count > 0:
                    qty_label = f"{stock_count} unité{'s' if stock_count != 1 else ''} en stock"
                else:
                    qty_label = "Rupture de stock (0 unités)"
                lines.append(f"- {str(product['name']).strip()} → {qty_label}")
            return "\n".join(lines)
        else:
            # No matching product found — let AI handle to say "not found"
            return None

    if ("categorie" in compact_message or "categories" in compact_message) and any(
        word in compact_message for word in ("produit", "produits", "liste")
    ):
        categories = fetch_categories()
        requested_category = find_requested_category(user_message, categories)
        if requested_category:
            products = fetch_products_by_category(requested_category, limit=100)
            return format_product_list(
                products, f"Voici les produits de la catégorie {requested_category} :"
            )
        return format_category_list(categories)

    # --- "Coup de cœur" category products ---
    if "coup" in compact_message and "coeur" in compact_message:
        categories = fetch_categories()
        coup_category = find_requested_category("Coup de cœur", categories)
        if not coup_category:
            coup_category = find_requested_category("coup de coeur", categories)
        if coup_category:
            products = fetch_products_by_category(coup_category, limit=100)
            return format_product_list(
                products, f"Voici les produits de la catégorie {coup_category} :"
            )
        return "La catégorie 'Coup de cœur' n'existe pas actuellement dans le catalogue."

    if product_search_signals or product_name_terms:
        products = _filter_by_relevance(
            fetch_product_matches(user_message, limit=8), user_message
        )
        if products:
            if len(products) == 1:
                return format_product_list(
                    products,
                    "Oui, ce produit existe dans le catalogue :",
                )
            return format_product_list(
                products,
                "Voici les produits trouvés dans le catalogue :",
            )

    if price_match and price_search_signals:
        price = float(price_match.group(1))

        if any(word in compact_message for word in ("moins", "dessous")):
            products = fetch_products("price <= %s AND stock > 0", [price], limit=6)
            return format_product_list(products, f"Produits disponibles à moins de {price:.2f} MAD :")

        if any(word in compact_message for word in ("plus", "dessus")):
            products = fetch_products("price >= %s AND stock > 0", [price], limit=6)
            return format_product_list(products, f"Produits disponibles à plus de {price:.2f} MAD :")

        low_price = max(price - 15, 0)
        high_price = price + 15
        products = fetch_products(
            "price BETWEEN %s AND %s AND stock > 0", [low_price, high_price], limit=6
        )
        return format_product_list(products, f"Produits disponibles autour de {price:.2f} MAD :")

    if any(
        word in compact_message
        for word in (
            "disponible", "disponibles", "produits",
            "catalogue", "materiel", "materiels", "deejay", "dj", "eclairage",
            "categorie", "categories",
        )
    ):
        asks_all_products = any(
            word in compact_message for word in ("tous", "toutes", "tout", "catalogue", "categorie", "categories")
        )
        asks_available_products = any(
            word in compact_message for word in ("disponible", "disponibles", "stock")
        )

        # If asking about a SPECIFIC product's availability (not a general browse),
        # search for it first. If not found, let AI handle to say "not found".
        if asks_available_products and not asks_all_products:
            specific_matches = _filter_by_relevance(
                fetch_product_matches(user_message, limit=5), user_message
            )
            if specific_matches:
                return format_product_list(specific_matches, "Voici les produits disponibles :")
            # No match: let AI handle to politely say "product not found"
            return None

        if asks_all_products or not asks_available_products:
            products = fetch_products(limit=CATALOG_LIST_LIMIT)
            return format_product_list(
                products,
                "Voici les produits du catalogue, classés par catégorie :",
                group_by_category=True,
            )

        products = fetch_products("stock > 0", limit=12)
        return format_product_list(products, "Voici les produits disponibles :")

    return None
