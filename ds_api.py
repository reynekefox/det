import os
import json
import logging
import aiohttp
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

async def make_deepseek_request(
    messages: List[Dict[str, str]],
    model: str = "deepseek-chat",
    temperature: float = 0.2,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Отправляет запрос к API DeepSeek.
    
    Args:
        messages: Список сообщений в формате [{"role": "...", "content": "..."}]
        model: Модель для использования
        temperature: Температура генерации (0.0 - 1.0)
        max_tokens: Максимальное количество токенов в ответе
        
    Returns:
        Dict[str, Any]: Ответ от API в формате JSON
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY не установлен")
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    
    if max_tokens is not None:
        data["max_tokens"] = max_tokens
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ошибка DeepSeek API: {response.status} - {error_text}")
                    raise Exception(f"Ошибка DeepSeek API: {response.status} - {error_text}")
                    
                return await response.json()
                
    except Exception as e:
        logger.error(f"Ошибка при запросе к DeepSeek API: {str(e)}")
        raise 