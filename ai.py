"""
SonoBot — AI Client & Conversation History
Multi-provider AI initialization, session-based history, and chat completion.
"""

import logging
import time
import threading
from collections import defaultdict

from openai import OpenAI

from config import (
    AI_PROVIDER, API_KEY, MISTRAL_API_KEY,
    IS_GEMINI, IS_GROQ, IS_OPENROUTER,
    DEFAULT_MODELS, MAX_HISTORY_MESSAGES, SESSION_TIMEOUT_MINUTES,
)

logger = logging.getLogger("sonobot.ai")

# ---------------------------------------------------------------------------
# AI Client Initialization
# ---------------------------------------------------------------------------

openai_client = None
DEFAULT_MODEL = None

if AI_PROVIDER == "mistral" or (MISTRAL_API_KEY and not AI_PROVIDER):
    DEFAULT_MODEL = DEFAULT_MODELS["mistral"]
    if MISTRAL_API_KEY:
        openai_client = OpenAI(
            api_key=MISTRAL_API_KEY,
            base_url="https://api.mistral.ai/v1",
        )
        logger.info("Mistral API mode enabled (model: %s).", DEFAULT_MODEL)
    else:
        logger.warning("Mistral API mode selected, but MISTRAL_API_KEY is empty.")
elif IS_OPENROUTER:
    openai_client = OpenAI(
        api_key=API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
    DEFAULT_MODEL = DEFAULT_MODELS["openrouter"]
    logger.info("OpenRouter API mode enabled (model: %s).", DEFAULT_MODEL)
elif IS_GROQ:
    openai_client = OpenAI(
        api_key=API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    DEFAULT_MODEL = DEFAULT_MODELS["groq"]
    logger.info("Groq FREE API mode enabled (model: %s).", DEFAULT_MODEL)
elif IS_GEMINI:
    openai_client = OpenAI(
        api_key=API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    DEFAULT_MODEL = DEFAULT_MODELS["gemini"]
    logger.info("Google Gemini API mode enabled (model: %s).", DEFAULT_MODEL)
else:
    openai_client = OpenAI(api_key=API_KEY)
    DEFAULT_MODEL = DEFAULT_MODELS["openai"]
    logger.info("OpenAI API mode enabled (model: %s).", DEFAULT_MODEL)

# ---------------------------------------------------------------------------
# Session-based Conversation History
# ---------------------------------------------------------------------------

# { session_id: {"messages": [...], "last_active": timestamp} }
_sessions = defaultdict(lambda: {"messages": [], "last_active": time.time()})
_sessions_lock = threading.Lock()


def _cleanup_expired_sessions():
    """Removes sessions that have been inactive for longer than SESSION_TIMEOUT_MINUTES."""
    cutoff = time.time() - (SESSION_TIMEOUT_MINUTES * 60)
    with _sessions_lock:
        expired = [sid for sid, data in _sessions.items() if data["last_active"] < cutoff]
        for sid in expired:
            del _sessions[sid]
        if expired:
            logger.debug("Cleaned up %d expired sessions.", len(expired))


def get_history(session_id):
    """Returns the conversation history for a session (max MAX_HISTORY_MESSAGES)."""
    with _sessions_lock:
        session = _sessions[session_id]
        session["last_active"] = time.time()
        return list(session["messages"][-MAX_HISTORY_MESSAGES:])


def add_to_history(session_id, role, content):
    """Appends a message to the session history."""
    with _sessions_lock:
        session = _sessions[session_id]
        session["messages"].append({"role": role, "content": content})
        # Trim to keep only the last MAX_HISTORY_MESSAGES
        if len(session["messages"]) > MAX_HISTORY_MESSAGES * 2:
            session["messages"] = session["messages"][-MAX_HISTORY_MESSAGES:]
        session["last_active"] = time.time()


# ---------------------------------------------------------------------------
# System Prompt Builder
# ---------------------------------------------------------------------------

def build_system_prompt(product_context):
    """Builds the full system prompt with store policies and product catalog."""
    return (
        "You are 'SonoBot', the AI shopping assistant for **SonoLight**, a Moroccan online store "
        "specializing in professional lighting, DJ equipment, laser effects, and event gear.\n\n"

        "=== LANGUAGE RULES (CRITICAL — HIGHEST PRIORITY) ===\n"
        "• ALWAYS reply in the SAME language the customer writes in. This is the #1 rule.\n"
        "• If the customer writes in English, reply ENTIRELY in English.\n"
        "• If the customer writes in Arabic, reply ENTIRELY in Arabic.\n"
        "• If the customer writes in Moroccan Darija, reply ENTIRELY in Darija.\n"
        "• If the customer writes in French, reply ENTIRELY in French.\n"
        "• Only use French as a fallback when the language is truly ambiguous or unclear.\n"
        "• NEVER mix two languages in one response.\n"
        "• NEVER output Chinese, Japanese, Korean, or any script unrelated to the customer's language.\n"
        "• Use MAD (درهم) as the currency.\n\n"

        "=== STORE INFO ===\n"
        "Location: Agadir, Morocco\n\n"

        "=== STORE POLICIES ===\n"
        "Payment methods:\n"
        "  - ✅ Cash on Delivery (الدفع عند الاستلام / Paiement à la livraison) — available for all orders\n"
        "  - ✅ Bank transfer (Virement bancaire)\n"
        "  - ✅ Online payment (Paiement en ligne)\n"
        "Delivery:\n"
        "  - ✅ Delivery available across ALL of Morocco (جميع مناطق المغرب)\n"
        "  - Same city (Agadir): approximately 25–35 MAD\n"
        "  - Other cities in Morocco: approximately 45–65 MAD\n"
        "  - Remote areas / rural zones: approximately 60–80 MAD\n"
        "  - Free delivery for orders above 2000 MAD\n"
        "  - Delivery time: Same day or next day for Agadir, 2–5 business days for other cities\n"
        "Returns:\n"
        "  - 7-day return policy for defective or incorrect items\n"
        "Support & Contact:\n"
        "  - 📧 Email: contact@sonolight.ma\n"
        "  - 📞 Phone / WhatsApp: +212 6XX-XXXXXX\n"
        "  - Working hours: Monday–Friday 09:00–18:00, Saturday 09:00–12:00\n\n"

        "=== PASSWORD RESET ===\n"
        "If the customer forgot their password, guide them to:\n"
        "  1. Go to the SonoLight website and click 'Mon compte' / 'حسابي'\n"
        "  2. Click 'Mot de passe oublié' / 'نسيت كلمة المرور'\n"
        "  3. Enter their email to receive a reset link\n"
        "  4. If that doesn't work, contact support via email or WhatsApp\n\n"

        "=== PRODUCT CATALOG (REAL-TIME DATA) ===\n"
        "--------------------------------------------------\n"
        f"{product_context}"
        "--------------------------------------------------\n\n"

        "=== BEHAVIORAL RULES ===\n"
        "1. For product questions: rely ONLY on the catalog data above. Never invent products or prices.\n"
        "2. If a product is out of stock (Stock: 0), inform the customer and suggest similar items from the catalog.\n"
        "3. If the requested product is not in the catalog, politely say it's not currently available and suggest what we do have.\n"
        "4. For store policy questions (delivery, payment, returns, contact): use ONLY the STORE POLICIES section above. "
        "Do NOT invent shipping prices, store addresses, or cities. If you don't know, say 'contactez notre support'.\n"
        "5. For off-topic questions (jokes, weather, general knowledge): politely and warmly decline, "
        "saying you're specialized in SonoLight products, but do it with a friendly tone — not robotic.\n"
        "6. For promotions/discounts: if none are in the catalog, say there are no active promotions "
        "but invite the customer to follow SonoLight on social media for upcoming deals.\n"
        "7. Keep answers friendly, professional, warm, and concise (3-5 sentences max).\n"
        "8. Add relevant emojis sparingly for a warm feel (😊, 🎵, 💡, 🚚, ✅).\n"
        "9. Always end with an offer to help further.\n"
        "10. NEVER mention or share website URLs or links in your responses.\n"
        "11. NEVER fabricate information. If you don't have specific data (exact delivery fees, "
        "store physical address, exact location), say you don't have that info and suggest contacting support.\n"
    )


# ---------------------------------------------------------------------------
# Chat Completion
# ---------------------------------------------------------------------------

def chat_completion(user_message, product_context, session_id=None):
    """Calls the AI API with conversation history and returns the reply.

    Returns:
        tuple: (reply_text, error_message). One of them will be None.
    """
    if openai_client is None:
        return None, (
            "AI API key is missing. Product search still works, "
            "but general AI replies need an API key in .env."
        )

    # Periodically clean up old sessions
    _cleanup_expired_sessions()

    system_prompt = build_system_prompt(product_context)

    # Build messages list with history
    messages = [{"role": "system", "content": system_prompt}]

    if session_id:
        history = get_history(session_id)
        messages.extend(history)

    messages.append({"role": "user", "content": user_message})

    max_retries = 1
    for attempt in range(max_retries):
        try:
            completion = openai_client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                max_tokens=300,
                temperature=0.7,
            )

            reply = completion.choices[0].message.content.strip()

            # Save to history
            if session_id:
                add_to_history(session_id, "user", user_message)
                add_to_history(session_id, "assistant", reply)

            return reply, None

        except Exception as e:
            error_str = str(e)
            logger.error("AI API error (attempt %d/%d): %s", attempt + 1, max_retries, e)

            if "429" in error_str and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 20
                logger.warning("Rate limited. Waiting %ds before retry...", wait_time)
                time.sleep(wait_time)
                continue

            # Build user-friendly error messages
            if "429" in error_str:
                friendly = "I'm currently receiving too many requests. Please wait a minute and try again!"
            elif "401" in error_str:
                friendly = "API key is invalid. Please check your .env file configuration."
            elif "404" in error_str:
                friendly = "AI model not found. Please check the model configuration."
            else:
                friendly = "I'm having trouble connecting right now. Please try again in a moment!"

            return None, friendly
