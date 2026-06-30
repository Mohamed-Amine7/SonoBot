"""
SonoBot — Guided Conversation & Direct Catalog Response
Step-by-step product recommendation wizard and instant catalog answers.
"""

import re
import logging

from utils import normalize_text, normalize_search_key, has_arabic
from catalog import (
    fetch_categories, find_requested_category, fetch_products_by_category,
    fetch_products, fetch_product_matches, format_product_list, format_category_list,
)
from config import CATALOG_LIST_LIMIT

logger = logging.getLogger("sonobot.guide")

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


def is_guide_trigger(user_message):
    """Detects when a user needs guided product assistance."""
    if has_arabic(user_message):
        return False

    message = normalize_text(user_message)
    compact = re.sub(r"[^a-z0-9\s]", " ", message)

    phrase_triggers = [
        "sais pas", "connais pas", "aide moi", "aidez moi",
        "conseillez moi", "conseille moi", "guide moi", "guidez moi",
        "quoi choisir", "quoi prendre", "pas sur", "pas sure",
        "pas decide", "suis perdu", "suis perdue",
        "recommandez", "recommande moi", "besoin aide",
        "help me choose", "not sure", "don t know",
        "c est quoi le mieux", "meilleur choix",
        "orienter", "orientez moi", "oriente moi",
    ]
    if any(phrase in compact for phrase in phrase_triggers):
        return True

    word_triggers = {
        "suggestion", "suggestions", "recommandation", "recommandations",
        "indecis", "hesit", "hesite",
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

def direct_catalog_response(user_message):
    """Returns instant database answers for common shopping questions.
    Skips to AI when the message is in Arabic/Darija or English so
    the AI can reply in the customer's language."""
    message = normalize_text(user_message)
    compact_message = re.sub(r"[^a-z0-9$€.\s]", " ", message)

    # If the message contains Arabic script, let the AI handle it
    if has_arabic(user_message):
        return None

    # Detect if the message is primarily English (not French)
    english_signals = {
        'do', 'you', 'have', 'what', 'how', 'can', 'is', 'are',
        'the', 'my', 'your', 'where', 'does', 'which', 'any',
        'much', 'many', 'i', 'want', 'need', 'looking', 'for',
    }
    message_words = set(compact_message.split())
    is_english = len(message_words & english_signals) >= 2

    if is_english:
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

    price_match = re.search(r"(?:\$|€|mad\s*)?(\d+(?:\.\d{1,2})?)", compact_message)
    product_search_signals = any(
        word in compact_message
        for word in ("cherche", "recherche", "trouve", "trouver", "besoin", "veux", "existe", "about")
    )
    product_name_terms = any(
        word in compact_message
        for word in ("light", "laser", "beam", "wash", "waterproof", "flat", "par", "pcs", "led", "in1")
    )
    price_search_signals = any(
        word in compact_message
        for word in ("prix", "price", "mad", "dh", "dhs", "moins", "dessous", "plus", "dessus", "budget")
    )
    asks_count = any(word in compact_message for word in ("nombre", "combien", "count", "total"))
    asks_quantity = any(word in compact_message for word in ("quantite", "quantity", "stock"))
    asks_catalog = any(
        word in compact_message
        for word in (
            "produit", "produits", "catalogue", "disponible", "disponibles", "stock", "prix", "mad",
            "materiel", "materiels", "eclairage", "deejay", "dj", "categorie", "categories",
            "light", "laser", "beam", "wash", "waterproof", "flat", "par", "pcs", "led", "in1",
            "coup", "coeur", "quantite", "nombre", "combien",
        )
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
        products = fetch_product_matches(user_message, limit=5)
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
        products = fetch_product_matches(user_message, limit=8)
        if products:
            requested_key = normalize_search_key(user_message)
            exact_products = [
                product for product in products
                if normalize_search_key(product.get("name", ""))
                and normalize_search_key(product.get("name", "")) in requested_key
            ]
            if exact_products:
                return format_product_list(
                    exact_products[:1],
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
