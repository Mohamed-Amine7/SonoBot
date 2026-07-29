"""
SonoBot — Flask Application & Routes
Slim entry point: routes, CORS, rate limiting, and health check.
"""

import os
import logging

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import FLASK_PORT, FLASK_DEBUG, CORS_ORIGINS, RATE_LIMIT, DB_NAME
from db import get_db_connection
from catalog import (
    search_database, fetch_products, get_catalog_provider, get_hikashop_prefix,
)
from ai import chat_completion
from guide import (
    GUIDE_STEPS, is_guide_trigger, guide_product_search, direct_catalog_response,
    format_product_list, get_guide_step, guide_copy,
)
from utils import detect_language

logger = logging.getLogger("sonobot.app")

# ---------------------------------------------------------------------------
# Flask App Setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

# CORS: configurable via .env (default "*" for dev)
origins = CORS_ORIGINS if CORS_ORIGINS == "*" else [o.strip() for o in CORS_ORIGINS.split(",")]
CORS(app, origins=origins)

# Rate Limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok", "service": "sonobot"})


@app.route("/api/guide", methods=["POST"])
def guide():
    """Handles the step-by-step guided product recommendation flow."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    step = data.get("step", 0)
    answer = data.get("answer", "")
    criteria = data.get("criteria", {})
    language = criteria.get("language", "fr")

    step_keys = {1: "event_type", 2: "environment", 3: "budget", 4: "effect_type"}

    if step in step_keys and answer:
        criteria[step_keys[step]] = answer

    next_step = step + 1

    if next_step in GUIDE_STEPS:
        guide_data = get_guide_step(next_step, language)
        return jsonify({
            "type": "guide",
            "step": next_step,
            "response": guide_data["question"],
            "options": guide_data["options"],
            "criteria": criteria,
        })

    # All steps completed — search and suggest products
    products = guide_product_search(criteria)
    if products:
        result = format_product_list(
            products,
            guide_copy(language, "recommendations") or "🎯 D'après vos besoins, voici les produits que je vous recommande :",
            language=language,
        )
    else:
        fallback = fetch_products(limit=5)
        if fallback:
            result = format_product_list(
                fallback,
                guide_copy(language, "fallback") or "Je n'ai pas trouvé de correspondance exacte, mais voici quelques suggestions :",
                language=language,
            )
        else:
            result = guide_copy(language, "no_results") or (
                "Désolé, je n'ai pas pu trouver de produits pour le moment. "
                "Contactez notre support pour une assistance personnalisée. 📧"
            )

    result += "\n\n" + (guide_copy(language, "follow_up") or "💬 Besoin de plus de détails sur un produit ? N'hésitez pas à demander !")

    return jsonify({
        "type": "result",
        "response": result,
        "criteria": criteria,
    })


@app.route("/api/catalog/status", methods=["GET"])
def catalog_status():
    """Returns catalog connection status and metadata."""
    try:
        with get_db_connection() as (_conn, cursor):
            provider = get_catalog_provider()
            prefix = get_hikashop_prefix(cursor) if provider == "hikashop" else ""
            products = fetch_products("stock > 0", limit=1)

            return jsonify({
                "ok": products is not None,
                "provider": provider,
                "database": DB_NAME,
                "joomla_table_prefix": prefix,
                "has_products": bool(products),
            })
    except Exception as err:
        return jsonify({
            "ok": False,
            "provider": get_catalog_provider(),
            "database": DB_NAME,
            "error": str(err),
        }), 500


@app.route("/api/chat", methods=["POST"])
@limiter.limit(RATE_LIMIT)
def chat():
    """Main API endpoint. Receives user message, queries database for product data,
    sends context to AI, and returns the generated chatbot reply."""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Message parameter is missing"}), 400

    user_message = data["message"]
    if not isinstance(user_message, str) or not user_message.strip():
        return jsonify({"error": "Message must be a non-empty string"}), 400

    user_message = user_message.strip()
    session_id = data.get("session_id")

    # Check for guided-conversation triggers first
    if is_guide_trigger(user_message):
        language = detect_language(user_message)
        guide_data = get_guide_step(1, language)
        return jsonify({
            "type": "guide",
            "step": 1,
            "response": guide_data["question"],
            "options": guide_data["options"],
            "criteria": {"language": language},
        })

    direct_response = direct_catalog_response(user_message)
    if direct_response:
        # Save to session history so follow-up questions have context
        if session_id:
            from ai import add_to_history
            add_to_history(session_id, "user", user_message)
            add_to_history(session_id, "assistant", direct_response)
        return jsonify({"response": direct_response, "source": "database"})

    # Fetch relevant product context from MySQL database
    matched_products = search_database(user_message) or []

    # If no products matched and the message is short (follow-up like "son prix?"),
    # try to extract product context from the recent conversation history
    if not matched_products and session_id and len(user_message.split()) <= 5:
        from ai import get_history
        from catalog import fetch_product_matches
        from guide import _filter_by_relevance
        history = get_history(session_id)
        # Check recent messages: prioritize user messages (they contain product names)
        for msg in reversed(history[-6:]):
            if len(msg["content"]) > 15:
                candidates = fetch_product_matches(msg["content"], limit=3)
                filtered = _filter_by_relevance(candidates, msg["content"])
                if filtered:
                    matched_products = filtered
                    break

    product_context = ""
    if matched_products:
        product_context = "Relevant products in store catalog:\n"
        for prod in matched_products:
            price = float(prod.get('price', 0) or 0)
            price_str = f"{price:.2f} MAD" if price > 0 else "Prix sur demande"
            ref = prod.get('reference', '')
            ref_str = f"  Reference/SKU: {ref}\n" if ref else ""
            product_context += (
                f"- Name: {prod['name']}\n"
                f"{ref_str}"
                f"  Category: {prod['category']}\n"
                f"  Price: {price_str}\n"
                f"  Stock: {prod['stock']} available\n"
                f"  Description: {prod['description']}\n\n"
            )
    else:
        product_context = "No catalog information is currently available or matched.\n"

    # Call AI with conversation history
    reply, error = chat_completion(user_message, product_context, session_id)

    if error:
        return jsonify({"response": error, "error": error}), 500

    return jsonify({
        "response": reply,
        "products_queried": len(matched_products),
    })


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Flask server on port %d (Debug=%s)...", FLASK_PORT, FLASK_DEBUG)
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)
