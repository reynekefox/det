# The code is modified to analyze the user's current message when choosing a DeepSeek model, and automatically select reasoning model for complex queries based on keywords.
import logging
from typing import Tuple, Optional
from ds_api import make_deepseek_request

logger = logging.getLogger(__name__)

async def choose_deepseek_model(message) -> tuple[str, str]:
    """
    Выбирает подходящую модель DeepSeek на основе анализа диалога.
    
    Args:
        message: Объект сообщения от пользователя
        
    Returns:
        tuple: (название выбранной модели ('deepseek-chat' или 'deepseek-reasoning'), сырой ответ ('chat' или 'reasoning'))
    """
    try:
        # Получаем историю диалога
        if not hasattr(message.bot, "dialogs"):
            message.bot.dialogs = {}
        dialog_history = message.bot.dialogs.get(message.from_user.id, {}).get("messages", [])
        
        # Берем последние 10 сообщений для анализа
        recent_messages = dialog_history[-10:] if len(dialog_history) > 10 else dialog_history

        # Получаем текущее сообщение пользователя
        current_message = message.text if hasattr(message, 'text') else ""

        # Ключевые слова, которые указывают на необходимость использования reasoning
        reasoning_keywords = [
            "план", "стратегия", "анализ", "причины", "почему", "как лучше", "что делать", 
            "объясни", "разбери", "составь", "помоги разобраться", "мотивационную историю",
            "терапевтическую", "поучительную", "детально", "подробно", "глубоко"
        ]

        # Проверяем наличие ключевых слов
        if any(keyword in current_message.lower() for keyword in reasoning_keywords):
            logger.info(f"[DeepSeek] Автоматически выбрана reasoning модель из-за ключевых слов в сообщении: '{current_message}'")
            return ("deepseek-reasoner", "reasoning")

        # Формируем промпт для выбора модели
        model_selection_prompt = [
            {
                "role": "system",
                "content": "Ты — ассистент, который выбирает оптимальную модель для ответа на вопрос пользователя.\n"
                          "Если вопрос требует анализа, рассуждений, составления плана, объяснения причин, выбора стратегии, создания подробных историй или сложного психологического консультирования — выбери 'reasoning'.\n"
                          "Если вопрос простой, бытовой, не требует глубокого анализа — выбери 'chat'.\n"
                          "Ответь только одним словом: reasoning или chat."
            },
            {
                "role": "user",
                "content": f"Текущий вопрос пользователя: '{current_message}'\n\nИстория диалога: {recent_messages}\n\nКакую модель выбрать для ответа на текущий вопрос?"
            }
        ]
        
        logger.info(f"[DeepSeek] Запрос на выбор модели: {model_selection_prompt}")
        
        # Используем chat модель для выбора модели
        response = await make_deepseek_request(
            messages=model_selection_prompt,
            model="deepseek-chat",
            temperature=0.1,
            max_tokens=10
        )
        
        logger.info(f"[DeepSeek] Ответ: {response}")
        
        if not response or "choices" not in response or not response["choices"]:
            logger.warning("[DeepSeek] Не удалось получить ответ для выбора модели")
            return ("deepseek-chat", "chat")
            
        model_choice = response["choices"][0]["message"]["content"].strip().lower()
        logger.info(f"[DeepSeek] Сырой ответ на выбор модели: '{model_choice}'")
        
        # Определяем итоговую модель
        if model_choice == "reasoning":
            final_model = "deepseek-reasoner"
        else:
            final_model = "deepseek-chat"
        
        logger.info(f"[DeepSeek] Итоговая выбранная модель: {final_model}")
        return (final_model, model_choice)
        
    except Exception as e:
        logger.error(f"Ошибка при выборе модели: {str(e)}")
        return ("deepseek-chat", "chat")  # Возвращаем chat модель в случае ошибки


async def test_model_availability(model: str) -> bool:
    """
    Проверяет доступность модели DeepSeek
    
    Args:
        model: Название модели для проверки
        
    Returns:
        bool: True если модель доступна, False если нет
    """
    try:
        test_messages = [{"role": "user", "content": "test"}]
        response = await make_deepseek_request(
            messages=test_messages,
            model=model,
            temperature=0.1,
            max_tokens=1
        )
        return response is not None and "choices" in response
    except Exception as e:
        logger.error(f"Модель {model} недоступна: {str(e)}")
        return False