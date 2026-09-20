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
            max_retries=0,  # Prevent SDK retries from tripling 429 requests
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
_request_counter = 0


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

def build_system_prompt(product_context, target_language=None):
    """Builds the full system prompt with store policies and product catalog."""
    lang_names = {
        "en": "English",
        "fr": "French (Français)",
        "ar": "Arabic (العربية)",
        "darija": "Moroccan Darija (الدارجة المغربية)",
    }
    target_name = lang_names.get(target_language)

    lang_priority_block = ""
    if target_name:
        if target_language == "darija":
            lang_priority_block = (
                "=== 🚨 MANDATORY LANGUAGE FOR THIS TURN: AUTHENTIC MOROCCAN DARIJA (الدارجة المغربية) 🚨 ===\n"
                "• The customer is communicating in Moroccan Darija (الدارجة المغربية).\n"
                "• You MUST formulate your response in 100% authentic Moroccan Darija (preferably in Arabic letters, or clean Latin text).\n"
                "• ⛔ STRICTLY FORBIDDEN: DO NOT use Egyptian, Levantine, or Gulf Arabic. NEVER use words like '3ayza', '3ayez', 'shoo', 'baddi', 'keda', 'dilwa'ti', 'eh'.\n"
                "• ⛔ STRICTLY FORBIDDEN: DO NOT reply in French.\n"
                "• ✅ AUTHENTIC MOROCCAN VOCABULARY TO USE:\n"
                "  - 'bghiti' / 'bghit' (بغيتي / بغيت) — NEVER '3ayza'\n"
                "  - 'khassek' (خاصك) — what you need\n"
                "  - 'kayn' / 'kayna' (كاين / كاينة) — available in stock\n"
                "  - 'dyal' / 'dial' (ديال) — of / for\n"
                "  - 'chhal' (شحال) — how much / how many\n"
                "  - 'taman' (الثمن) — price\n"
                "  - 'mzyan' (مزيان) — good / great\n"
                "  - 'l-3rassat' (الأعراس / العراسات) — weddings\n"
                "  - 'at-tawsil' / 'livraison' (التوصيل) — delivery across Morocco (Agadir 35–50 DH, other cities 55–80 DH)\n"
                "  - 'ad-daf3 3inda l-istilam' (الدفع عند الاستلام) — Cash on Delivery\n"
                "• Keep the answer short, warm, and natural (2–4 lines).\n\n"
            )
        else:
            lang_priority_block = (
                f"=== 🚨 MANDATORY LANGUAGE FOR THIS TURN: {target_name.upper()} 🚨 ===\n"
                f"• The customer's current message is written in {target_name}.\n"
                f"• You MUST formulate 100% of your response in {target_name}.\n"
                f"• Even if earlier messages in the chat history were in French or another language, switch IMMEDIATELY to {target_name}.\n"
                f"• Under NO circumstances should you reply in French when the customer wrote in {target_name}.\n\n"
            )

    return (
        "You are 'SonoBot', the AI shopping assistant for **SonoLight**, a Moroccan online store "
        "specializing in professional lighting, DJ equipment, laser effects, and event gear.\n\n"
        f"{lang_priority_block}"
        "=== LANGUAGE RULES (CRITICAL — ABSOLUTE HIGHEST PRIORITY) ===\n"
        "• Reply ENTIRELY in the customer's language.\n"
        "• If the customer writes in English → reply 100% in English. NOT a single French word.\n"
        "• If the customer writes in French → reply 100% in French.\n"
        "• If the customer writes in Arabic → reply 100% in Arabic.\n"
        "• If the customer writes in Moroccan Darija (Latin or Arabic script) → reply in Moroccan Darija.\n"
        "• NEVER mix two languages in one response.\n"
        "• The store policies and product catalog below are written in English for your reference, "
        "but you MUST translate them to the customer's language when responding.\n"
        "• Use MAD (درهم) as the currency.\n\n"

        "=== SPEED & CONCISENESS RULES (CRITICAL FOR PERFORMANCE) ===\n"
        "• Be DIRECT, CONCISE, and FAST: Keep responses under 100–160 words (2–4 short paragraphs or bullet points maximum).\n"
        "• Do NOT write gigantic essays, exhaustive manuals, or repeating disclaimers.\n"
        "• Give clear, punchy recommendations, mention the exact price in MAD, and ask ONE focused follow-up question.\n\n"

        "=== STORE INFO ===\n"
        "Location: Agadir, Morocco\n\n"

        "=== STORE POLICIES ===\n"
        "Payment methods:\n"
        "  - ✅ Cash on Delivery (الدفع عند الاستلام / Paiement à la livraison) — available for all orders\n"
        "  - ✅ Bank transfer (Virement bancaire)\n"
        "  - ✅ Online payment (Paiement en ligne)\n"
        "Delivery:\n"
        "  - ✅ Delivery available across ALL of Morocco (جميع مناطق المغرب)\n"
        "  - Same city (Agadir): approximately 35–50 MAD\n"
        "  - Other cities in Morocco: approximately 55–80 MAD\n"
        "  - Remote areas / rural zones: approximately 75–100 MAD\n"
        "  - Free delivery for orders above 6000 MAD\n"
        "  - Delivery time: Same day or next day for Agadir, 2–5 business days for other cities\n"
        "Returns:\n"
        "  - 7-day return policy for defective or incorrect items\n"
        "Support & Contact:\n"
        "  - 📧 Email: contact@sonolight.ma\n"
        "  - 📞 Phone / WhatsApp: +212 6 000 351 01\n"
        "  - Working hours: Monday–Friday 09:00–18:00, Saturday 09:00–12:00\n\n"

        "=== PASSWORD RESET ===\n"
        "If the customer forgot their password, guide them to:\n"
        "  1. Go to the SonoLight website and click 'Mon compte' / 'حسابي' / 'My Account'\n"
        "  2. Click 'Mot de passe oublié' / 'نسيت كلمة المرور' / 'Forgot password'\n"
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
        "Do NOT invent shipping prices, store addresses, or cities. If you don't know, say contact our support.\n"
        "5. For off-topic questions (jokes, weather, general knowledge): politely and warmly decline, "
        "saying you're specialized in SonoLight products, but do it with a friendly tone — not robotic.\n"
        "6. For promotions/discounts: if none are in the catalog, say there are no active promotions "
        "but invite the customer to follow SonoLight on social media for upcoming deals.\n"
        "7. Keep answers friendly, professional, warm, and concise (maximum 150 words).\n"
        "8. Add relevant emojis sparingly for a warm feel (😊, 🎵, 💡, 🚚, ✅).\n"
        "9. Always end with an offer to help further.\n"
        "10. NEVER mention or share website URLs or links in your responses.\n"
        "11. NEVER fabricate information. If you don't have specific data, say you don't have that info and suggest contacting support.\n"
        "12. If a product's price is 0.00 MAD or missing, say 'Prix sur demande' / 'Price on request' and invite the customer "
        "to contact support for a personalized quote. Do NOT say 'gratuit' or 'free'.\n"
        "13. When a customer asks about ordering, payments, or delivery, answer their question directly "
        "with clear step-by-step instructions. Do NOT list products unless they specifically asked for a product list.\n"
        "14. FOLLOW-UP QUESTIONS: When a customer asks a short follow-up like 'son prix?', 'how much?', 'combien?', 'et le stock?', "
        "look at the conversation history to identify which product they are referring to. "
        "Then answer with the EXACT data from the PRODUCT CATALOG section above for that specific product.\n"
        "15. REFERENCE CODES: Products have reference codes (SKU) like INF-SM470, INF-BM380. "
        "When a customer asks about a reference code, match it to the product in the catalog and answer about that specific product.\n"
        "\n"
        "=== FORMATTING RULES (CRITICAL) ===\n"
        "NEVER use Markdown tables (| col | col |). They are unreadable in a chat.\n"
        "NEVER use Markdown headers (#, ##, ###, ####). They render as raw text.\n"
        "NEVER use horizontal rules (---).\n"
        "ONLY USE these formatting elements:\n"
        "  - **bold text** for emphasis and section titles (translated to the customer's language)\n"
        "  - Bullet points (- item) for lists\n"
        "  - Emojis for visual warmth\n"
        "  - Line breaks for spacing\n"
        "\n"
        "For PRODUCT COMPARISONS, use this clean format (translate titles to customer language):\n"
        "\n"
        "**💡 Power / Puissance / القوة**\n"
        "- Product A : 380W\n"
        "- Product B : 240W total\n"
        "\n"
        "**🎨 Lighting Effects / Effets lumineux / التأثيرات**\n"
        "- Product A : Beam, Spot, Wash, prisms, gobos\n"
        "- Product B : RGBW, basic modes\n"
        "\n"
        "**🛡️ Protection / الحماية**\n"
        "- Product A : IP20 (indoor only)\n"
        "- Product B : IP65 (outdoor, rain, dust)\n"
        "\n"
        "End with a clear **🎯 Verdict** advising which product fits the use case.\n"
    )


# ---------------------------------------------------------------------------
# Chat Completion
# ---------------------------------------------------------------------------

def chat_completion(user_message, product_context, session_id=None, target_language=None):
    """Calls the AI API with conversation history and returns the reply.

    Returns:
        tuple: (reply_text, error_message). One of them will be None.
    """
    if openai_client is None:
        return None, (
            "AI API key is missing. Product search still works, "
            "but general AI replies need an API key in .env."
        )

    # Periodically clean up old sessions (every 20 requests, not every time)
    global _request_counter
    _request_counter += 1
    if _request_counter % 20 == 0:
        _cleanup_expired_sessions()

    system_prompt = build_system_prompt(product_context, target_language=target_language)

    # Build messages list with history
    messages = [{"role": "system", "content": system_prompt}]

    if session_id:
        history = get_history(session_id)
        messages.extend(history)

    # To break LLM history priming (language inertia), append a clear language directive to the user turn:
    lang_map = {
        "en": "English",
        "fr": "French",
        "ar": "Arabic",
        "darija": "Moroccan Darija",
    }
    target_name = lang_map.get(target_language)
    if target_name:
        if target_language == "darija":
            lang_note = (
                "Reply strictly in authentic Moroccan Darija (الدارجة المغربية). "
                "FORBIDDEN: Do NOT use Egyptian words (NEVER say 3ayza, 3ayez, shoo, baddi). "
                "Use true Moroccan words: bghiti (NOT 3ayza), khassek, kayn, dyal, chhal, mzyan. "
                "Do NOT reply in French."
            )
        else:
            lang_note = f"Reply strictly in {target_name}. Do NOT use French or mix languages."
        prompt_user_content = (
            f"{user_message}\n\n"
            f"[System note: {lang_note}]"
        )
    else:
        prompt_user_content = user_message

    messages.append({"role": "user", "content": prompt_user_content})

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # max_tokens=320 ensures instant, snappy replies (around 1.0-1.5s)
            completion = openai_client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                max_tokens=320,
                temperature=0.6,
            )

            reply = completion.choices[0].message.content.strip()

            # Save clean user message to history
            if session_id:
                add_to_history(session_id, "user", user_message)
                add_to_history(session_id, "assistant", reply)

            return reply, None

        except Exception as e:
            error_str = str(e)
            logger.error("AI API error (attempt %d/%d): %s", attempt + 1, max_retries, e)

            if "429" in error_str and attempt < max_retries - 1:
                # Fast burst backoff (1.5s, 3s) instead of 30s lockup
                wait_time = 1.5 * (attempt + 1)
                logger.warning("Rate limited. Waiting %.1fs before retry...", wait_time)
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
