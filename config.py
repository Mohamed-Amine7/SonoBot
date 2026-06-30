"""
SonoBot — Configuration & Environment Loading
Handles .env parsing, structured logging, and all application settings.
"""

import os
import logging

# ---------------------------------------------------------------------------
# Structured Logging
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging():
    """Configures structured logging for the entire application."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )


logger = logging.getLogger("sonobot")

# ---------------------------------------------------------------------------
# .env Loader
# ---------------------------------------------------------------------------

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

if os.path.exists(_env_path):
    logger.info("Loading environment from %s", _env_path)
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#"):
                continue
            if "=" in _line:
                _key, _val = _line.split("=", 1)
                _key = _key.strip()
                _val = _val.strip()
                # Strip surrounding quotes
                if (_val.startswith('"') and _val.endswith('"')) or (
                    _val.startswith("'") and _val.endswith("'")
                ):
                    _val = _val[1:-1]
                os.environ[_key] = _val
                logger.debug("  -> Set env var: %s", _key)
else:
    logger.info("No .env file found at %s", _env_path)

# Apply logging level from .env (may have just been loaded)
setup_logging()

# ---------------------------------------------------------------------------
# AI Provider Configuration
# ---------------------------------------------------------------------------

AI_PROVIDER = os.getenv("AI_PROVIDER", "").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

API_KEY = (
    MISTRAL_API_KEY
    if AI_PROVIDER == "mistral" or (MISTRAL_API_KEY and not AI_PROVIDER)
    else OPENAI_API_KEY
)

# Mask to 4 characters max for security
_masked = API_KEY[:4] + "****" if len(API_KEY) > 4 else "Not Set"
logger.info("AI API key configured: %s", _masked)

# Auto-detect provider by key prefix
IS_GEMINI = API_KEY.startswith("AIzaSy") or API_KEY.startswith("AQ.")
IS_GROQ = API_KEY.startswith("gsk_")
IS_OPENROUTER = API_KEY.startswith("sk-or-")

# ---------------------------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------------------------

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "ecommerce_db")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))

CATALOG_PROVIDER = os.getenv("CATALOG_PROVIDER", "sample").strip().lower()
JOOMLA_TABLE_PREFIX = os.getenv("JOOMLA_TABLE_PREFIX", "").strip()
CATALOG_LIST_LIMIT = int(os.getenv("CATALOG_LIST_LIMIT", 100))

# ---------------------------------------------------------------------------
# Flask / Security Configuration
# ---------------------------------------------------------------------------

FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

# CORS origins: comma-separated list or "*" for dev
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").strip()

# Rate limiting: requests per minute on /api/chat
RATE_LIMIT = os.getenv("RATE_LIMIT", "30/minute")

# AI conversation history: max messages to keep per session
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", 10))
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", 30))

# AI model defaults per provider
DEFAULT_MODELS = {
    "mistral": os.getenv("AI_MODEL", "mistral-small-latest"),
    "openrouter": os.getenv("AI_MODEL", "openrouter/free"),
    "groq": os.getenv("AI_MODEL", "llama-3.3-70b-versatile"),
    "gemini": os.getenv("AI_MODEL", "gemini-2.0-flash"),
    "openai": os.getenv("AI_MODEL", "gpt-4o-mini"),
}
