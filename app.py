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
from ai import openai_client, chat_completion
from guide import (
    GUIDE_STEPS, is_guide_trigger, guide_product_search, direct_catalog_response,
    format_product_list,
)

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

    step_keys = {1: "event_type", 2: "environment", 3: "budget", 4: "effect_type"}

    if step in step_keys and answer:
        criteria[step_keys[step]] = answer

    next_step = step + 1

    if next_step in GUIDE_STEPS:
        guide_data = GUIDE_STEPS[next_step]
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
            "🎯 D'après vos besoins, voici les produits que je vous recommande :",
        )
    else:
        fallback = fetch_products(limit=5)
        if fallback:
            result = format_product_list(
                fallback,
                "Je n'ai pas trouvé de correspondance exacte, mais voici quelques suggestions :",
            )
        else:
            result = (
                "Désolé, je n'ai pas pu trouver de produits pour le moment. "
                "Contactez notre support pour une assistance personnalisée. 📧"
            )

    result += "\n\n💬 Besoin de plus de détails sur un produit ? N'hésitez pas à demander !"

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
        guide_data = GUIDE_STEPS[1]
        return jsonify({
            "type": "guide",
            "step": 1,
            "response": guide_data["question"],
            "options": guide_data["options"],
            "criteria": {},
        })

    direct_response = direct_catalog_response(user_message)
    if direct_response:
        return jsonify({"response": direct_response, "source": "database"})

    # Fetch relevant product context from MySQL database
    matched_products = search_database(user_message)

    product_context = ""
    if matched_products:
        product_context = "Relevant products in store catalog:\n"
        for prod in matched_products:
            product_context += (
                f"- Name: {prod['name']}\n"
                f"  Category: {prod['category']}\n"
                f"  Price: {prod['price']:.2f} MAD\n"
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
