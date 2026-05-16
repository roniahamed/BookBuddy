"""
Google Translate API integration for book detail translation.
Supports EN ↔ HE auto-detection and translation.
"""
import logging
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)


def translate_text(text: str, target_lang: str, source_lang: str = None) -> str:
    """
    Translate text using Google Translate API.
    - target_lang: e.g. 'he' for Hebrew, 'en' for English
    - source_lang: auto-detected if not provided
    Returns translated text, or original if translation fails.
    """
    if not text or not text.strip():
        return text

    api_key = settings.GOOGLE_TRANSLATE_API_KEY
    if not api_key or api_key == "your-google-translate-api-key":
        logger.warning("Google Translate API key not configured")
        return text

    try:
        url = "https://translation.googleapis.com/language/translate/v2"
        params = {
            "q": text,
            "target": target_lang.lower(),
            "format": "text",
            "key": api_key,
        }
        if source_lang:
            params["source"] = source_lang.lower()

        response = requests.post(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        translated = data["data"]["translations"][0]["translatedText"]
        logger.info(f"Translated ({source_lang or 'auto'} → {target_lang}): {text[:50]}...")
        return translated
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return text


def translate_book_fields(
    title: str,
    description: str,
    author_name: str,
    target_lang: str,
) -> dict:
    """
    Translate book detail fields to target language.
    Returns dict with translated title, description, author_name.
    """
    return {
        "title": translate_text(title, target_lang),
        "description": translate_text(description, target_lang) if description else None,
        "author_name": translate_text(author_name, target_lang),
        "target_language": target_lang,
    }
