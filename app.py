import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from openai import OpenAI

# Load environment variables manually so local .env changes are picked up reliably.
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

if os.path.exists(env_path):
    print(f"[*] Loading environment from {env_path}")
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip()
                # Strip quotes if they surround the value
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                os.environ[key] = val
                print(f"  -> Set env var: {key}")
else:
    print(f"[*] No .env file found at {env_path}")

app = Flask(__name__)
# Enable Cross-Origin Resource Sharing (CORS) so Joomla can communicate with this API
CORS(app)

# Fetch AI provider credentials
ai_provider = os.getenv("AI_PROVIDER", "").strip().lower()
openai_api_key = os.getenv("OPENAI_API_KEY", "")
mistral_api_key = os.getenv("MISTRAL_API_KEY", "")
api_key = mistral_api_key if ai_provider == "mistral" or (mistral_api_key and not ai_provider) else openai_api_key
masked_key = api_key[:12] + "..." if len(api_key) > 12 else "Not Set"
print(f"[*] AI API key configured: {masked_key}")
openai_client = None

# Auto-detect API provider based on key prefix
is_gemini = api_key.startswith("AIzaSy") or api_key.startswith("AQ.")
is_groq = api_key.startswith("gsk_")
is_openrouter = api_key.startswith("sk-or-")

if ai_provider == "mistral" or (mistral_api_key and not ai_provider):
    DEFAULT_MODEL = os.getenv("AI_MODEL", "mistral-small-latest")
    if mistral_api_key:
        openai_client = OpenAI(
            api_key=mistral_api_key,
            base_url="https://api.mistral.ai/v1"
        )
        print(f"[*] Mistral API mode enabled (model: {DEFAULT_MODEL}).")
    else:
        print("[!] Mistral API mode selected, but MISTRAL_API_KEY is empty.")
elif is_openrouter:
    # OpenRouter: FREE models available, easy signup (OpenAI-compatible)
    openai_client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    DEFAULT_MODEL = os.getenv("AI_MODEL", "openrouter/free")
    print(f"[*] OpenRouter API mode enabled (model: {DEFAULT_MODEL}).")
elif is_groq:
    # Groq: FREE, fast inference using Llama models (OpenAI-compatible)
    openai_client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )
    DEFAULT_MODEL = os.getenv("AI_MODEL", "llama-3.3-70b-versatile")
    print("[*] Groq FREE API mode enabled (Llama 3.3 70B).")
elif is_gemini:
    # Google Gemini free OpenAI-compatible endpoint
    openai_client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    DEFAULT_MODEL = os.getenv("AI_MODEL", "gemini-2.0-flash")
    print(f"[*] Google Gemini API mode enabled (model: {DEFAULT_MODEL}).")
else:
    # Standard OpenAI endpoint
    openai_client = OpenAI(api_key=api_key)
    DEFAULT_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
    print(f"[*] OpenAI API mode enabled (model: {DEFAULT_MODEL}).")

def get_db_connection():
    """Establishes and returns a new MySQL database connection."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ecommerce_db"),
        port=int(os.getenv("DB_PORT", 3306))
    )

def get_catalog_provider():
    return os.getenv("CATALOG_PROVIDER", "sample").strip().lower()

def get_hikashop_prefix(cursor):
    configured_prefix = os.getenv("JOOMLA_TABLE_PREFIX", "").strip()
    if configured_prefix:
        return configured_prefix

    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name LIKE %s
        LIMIT 1
        """,
        ("%\\_hikashop_product",)
    )
    row = cursor.fetchone()
    if not row:
        raise mysql.connector.Error("Could not find a HikaShop product table in the configured database.")

    table_name = row["table_name"]
    return table_name[:-len("hikashop_product")]

def catalog_select_sql(cursor):
    """Returns the product query fields and table joins for the active catalog."""
    if get_catalog_provider() == "hikashop":
        prefix = get_hikashop_prefix(cursor)
        return f"""
            SELECT
                p.product_name AS name,
                p.product_description AS description,
                COALESCE(MIN(pr.price_value), 0) AS price,
                CASE
                    WHEN p.product_quantity < 0 THEN 999999
                    ELSE p.product_quantity
                END AS stock,
                COALESCE(MIN(c.category_name), 'Uncategorized') AS category
            FROM `{prefix}hikashop_product` p
            LEFT JOIN `{prefix}hikashop_price` pr
                ON pr.price_product_id = p.product_id
            LEFT JOIN `{prefix}hikashop_product_category` pc
                ON pc.product_id = p.product_id
            LEFT JOIN `{prefix}hikashop_category` c
                ON c.category_id = pc.category_id
            WHERE p.product_published = 1
              AND p.product_type = 'main'
        """

    return """
        SELECT name, description, price, stock, category
        FROM products
        WHERE 1 = 1
    """

def catalog_group_order_sql():
    if get_catalog_provider() == "hikashop":
        return " GROUP BY p.product_id, p.product_name, p.product_description, p.product_quantity ORDER BY price ASC"

    return " ORDER BY price ASC"

def catalog_search_condition_sql():
    if get_catalog_provider() == "hikashop":
        return "(p.product_name LIKE %s OR p.product_description LIKE %s OR c.category_name LIKE %s)"

    return "(name LIKE %s OR description LIKE %s OR category LIKE %s)"

def extract_keywords(text):
    """
    Cleans user input and extracts meaningful keywords for database searching,
    removing common English stop words.
    """
    # Extract words with 3 or more alphanumeric characters
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

    keywords = [word for word in words if word not in stop_words]
    return keywords

def search_database(user_message):
    """
    Searches the MySQL database for products matching keywords in the user's message.
    If no matches are found, returns a list of general popular products.
    """
    keywords = extract_keywords(user_message)
    connection = None
    cursor = None
    products = []
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        base_query = catalog_select_sql(cursor)
        params = []

        if keywords:
            conditions = []
            for word in keywords:
                conditions.append(catalog_search_condition_sql())
                pattern = f"%{word}%"
                params.extend([pattern, pattern, pattern])
            base_query += " AND (" + " OR ".join(conditions) + ")"

        query = base_query + catalog_group_order_sql() + " LIMIT %s"
        cursor.execute(query, [*params, 10 if keywords else 5])
        products = cursor.fetchall()

        if keywords and not products:
            query = catalog_select_sql(cursor) + catalog_group_order_sql() + " LIMIT %s"
            cursor.execute(query, [3])
            products = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            
    return products

def fetch_products(where_clause="", params=None, limit=10):
    """Fetches catalog products for direct, fast answers that do not need AI."""
    connection = None
    cursor = None
    params = params or []

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        query = catalog_select_sql(cursor)

        if get_catalog_provider() == "hikashop":
            having_clause = ""
            if "stock > 0" in where_clause:
                query += " AND p.product_quantity != 0"
            if "price BETWEEN" in where_clause:
                having_clause = " HAVING price BETWEEN %s AND %s"
            elif "price <=" in where_clause:
                having_clause = " HAVING price <= %s"
            elif "price >=" in where_clause:
                having_clause = " HAVING price >= %s"
            query += catalog_group_order_sql().replace(" ORDER BY", f"{having_clause} ORDER BY")
        else:
            if where_clause:
                query += f" AND {where_clause}"
            query += catalog_group_order_sql()

        query += " LIMIT %s"
        cursor.execute(query, [*params, limit])
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def format_product_list(products, intro):
    if products is None:
        return "I cannot read the HikaShop catalog yet. Please check DB_NAME and JOOMLA_TABLE_PREFIX in the .env file."

    if not products:
        return "I couldn't find matching products in the catalog right now."

    lines = [intro]
    for product in products:
        stock_count = int(product["stock"] or 0)
        stock_label = "disponible" if stock_count >= 999999 else f"{stock_count} en stock"
        lines.append(
            f"- {product['name']}: {product['price']:.2f} MAD ({stock_label})"
        )

    return "\n".join(lines)

def _has_arabic(text):
    """Returns True if the text contains Arabic/Darija script characters."""
    return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text))

def direct_catalog_response(user_message):
    """Returns instant database answers for common shopping questions.
    Skips to AI when the message is in Arabic/Darija or English so
    the AI can reply in the customer's language."""
    message = user_message.lower()
    compact_message = re.sub(r"[^a-z0-9$€.\s]", " ", message)

    # If the message contains Arabic script, let the AI handle it
    # so it can reply in the same language.
    if _has_arabic(user_message):
        return None

    # Detect if the message is primarily English (not French)
    english_signals = {'do', 'you', 'have', 'what', 'how', 'can', 'is', 'are',
                       'the', 'my', 'your', 'where', 'does', 'which', 'any',
                       'much', 'many', 'i', 'want', 'need', 'looking', 'for'}
    message_words = set(compact_message.split())
    is_english = len(message_words & english_signals) >= 2

    # If English, let the AI handle it so it replies in English.
    if is_english:
        return None

    # English greetings — let AI handle so it replies in English
    if compact_message.strip() in {'hi', 'hello', 'hey'}:
        return None

    # French / universal greetings — reply in French (default language)
    if compact_message.strip() in {'salam', 'bonjour', 'salut', 'labas', 'ahlan', 'marhba'}:
        return "Bonjour ! 😊 Je suis SonoBot, votre assistant SonoLight. Je peux vous aider à trouver des produits, vérifier les prix et la disponibilité. Comment puis-je vous aider ?"

    price_match = re.search(r"(?:\$|€|mad\s*)?(\d+(?:\.\d{1,2})?)", compact_message)
    asks_catalog = any(word in compact_message for word in (
        "produit", "produits", "catalogue", "disponible", "disponibles", "stock", "prix", "mad",
        "materiel", "materiels", "eclairage", "deejay", "dj"
    ))

    if not asks_catalog:
        return None

    if price_match:
        price = float(price_match.group(1))

        if any(word in compact_message for word in ("moins", "dessous")):
            products = fetch_products("price <= %s AND stock > 0", [price], limit=6)
            return format_product_list(products, f"Produits disponibles à moins de {price:.2f} MAD :")

        if any(word in compact_message for word in ("plus", "dessus")):
            products = fetch_products("price >= %s AND stock > 0", [price], limit=6)
            return format_product_list(products, f"Produits disponibles à plus de {price:.2f} MAD :")

        low_price = max(price - 15, 0)
        high_price = price + 15
        products = fetch_products("price BETWEEN %s AND %s AND stock > 0", [low_price, high_price], limit=6)
        return format_product_list(products, f"Produits disponibles autour de {price:.2f} MAD :")

    if any(word in compact_message for word in (
        "disponible", "disponibles", "produits",
        "catalogue", "materiel", "materiels", "deejay", "dj", "eclairage"
    )):
        products = fetch_products("stock > 0", limit=8)
        return format_product_list(products, "Voici les produits disponibles :")

    return None

@app.route('/api/catalog/status', methods=['GET'])
def catalog_status():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        provider = get_catalog_provider()
        prefix = get_hikashop_prefix(cursor) if provider == "hikashop" else ""
        products = fetch_products("stock > 0", limit=1)

        return jsonify({
            'ok': products is not None,
            'provider': provider,
            'database': os.getenv("DB_NAME", "ecommerce_db"),
            'joomla_table_prefix': prefix,
            'has_products': bool(products)
        })
    except mysql.connector.Error as err:
        return jsonify({
            'ok': False,
            'provider': get_catalog_provider(),
            'database': os.getenv("DB_NAME", "ecommerce_db"),
            'error': str(err)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main API endpoint. Receives user message, queries database for product data,
    sends context to OpenAI, and returns the generated chatbot reply.
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Message parameter is missing'}), 400
        
    user_message = data['message']
    if not isinstance(user_message, str) or not user_message.strip():
        return jsonify({'error': 'Message must be a non-empty string'}), 400

    user_message = user_message.strip()

    direct_response = direct_catalog_response(user_message)
    if direct_response:
        return jsonify({
            'response': direct_response,
            'source': 'database'
        })
    
    # 1. Fetch relevant product context from MySQL database
    matched_products = search_database(user_message)
    
    # Format database items as text context for GPT
    product_context = ""
    if matched_products:
        product_context = "Relevant products in store catalog:\n"
        for prod in matched_products:
            product_context += (
                f"- Name: {prod['name']}\n"
                f"  Category: {prod['category']}\n"
                f"  Price: ${prod['price']:.2f}\n"
                f"  Stock: {prod['stock']} available\n"
                f"  Description: {prod['description']}\n\n"
            )
    else:
        product_context = "No catalog information is currently available or matched.\n"

    # 2. Build system instructions and context guidelines
    system_prompt = (
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
    import time as _time

    if openai_client is None:
        return jsonify({
            'response': 'AI API key is missing. Product search still works, but general AI replies need MISTRAL_API_KEY in .env.'
        }), 500

    max_retries = 1
    for attempt in range(max_retries):
        try:
            # 3. Call AI API (OpenAI or Gemini via compatibility endpoint)
            completion = openai_client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            reply = completion.choices[0].message.content.strip()
            
            return jsonify({
                'response': reply,
                'products_queried': len(matched_products)
            })
            
        except Exception as e:
            error_str = str(e)
            print(f"AI API error (attempt {attempt+1}/{max_retries}): {e}")
            
            # If rate limited (429), wait and retry
            if "429" in error_str and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 20  # 20s, 40s
                print(f"Rate limited. Waiting {wait_time}s before retry...")
                _time.sleep(wait_time)
                continue
            
            # Build a user-friendly error message
            if "429" in error_str:
                friendly_msg = "I'm currently receiving too many requests. Please wait a minute and try again!"
            elif "401" in error_str:
                friendly_msg = "API key is invalid. Please check your .env file configuration."
            elif "404" in error_str:
                friendly_msg = "AI model not found. Please check the model configuration."
            else:
                friendly_msg = "I'm having trouble connecting right now. Please try again in a moment!"
            
            return jsonify({
                'response': friendly_msg,
                'error': error_str
            }), 500

if __name__ == '__main__':
    # Start Flask app on port specified in .env
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    print(f"Starting Flask server on port {port} (Debug={debug})...")
    app.run(host='0.0.0.0', port=port, debug=debug)
