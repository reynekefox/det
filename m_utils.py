import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_bot_info() -> Dict[str, Any]:
    """Получение информации о боте"""
    try:
        from m_config import BOT_NAME, BOT_USERNAME, TELEGRAM_TOKEN
        return {
            "name": BOT_NAME,
            "username": BOT_USERNAME,
            "token": TELEGRAM_TOKEN
        }
    except Exception as e:
        logger.error(f"Ошибка при получении информации о боте: {e}")
        return {} 