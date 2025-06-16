import os
import logging
import re
from typing import Optional, Dict
from aiogram import Bot
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)

# Словарь эмоций и соответствующих изображений
EMOTION_IMAGES = {
    "радость": "images/joy.png",
    "грусть": "images/sad.png", 
    "удивление": "images/surprise.png",
    "задумчивость": "images/thinking.png",
    "сочувствие": "images/empathy.png",
    "уверенность": "images/confidense.png",
    "спокойствие": "images/calm.png",
    "энтузиазм": "images/understanding.png",
    "понимание": "images/understanding.png",
    "поддержка": "images/support.png"
}

def extract_emotion_from_text(text: str) -> Optional[str]:
    """
    Извлекает эмоцию из текста по специальному тегу.
    Ищет паттерн [emotion:название_эмоции] в тексте.

    Args:
        text: Текст ответа от DeepSeek

    Returns:
        str или None: Название эмоции или None если не найдено
    """
    # Ищем паттерн [emotion:эмоция]
    pattern = r'\[emotion:([^\]]+)\]'
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        emotion = match.group(1).lower().strip()
        logger.info(f"Найдена эмоция в тексте: {emotion}")
        return emotion

    return None

def remove_emotion_tags(text: str) -> str:
    """
    Удаляет теги эмоций из текста.

    Args:
        text: Текст с возможными тегами эмоций

    Returns:
        str: Очищенный текст
    """
    # Удаляем все теги [emotion:*]
    pattern = r'\[emotion:[^\]]+\]'
    cleaned_text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return cleaned_text.strip()

async def send_emotion_image(bot: Bot, chat_id: int, emotion: str, caption: str = None) -> bool:
    """
    Отправляет изображение с эмоцией пользователю.

    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        emotion: Название эмоции
        caption: Текст подписи к изображению

    Returns:
        bool: True если изображение отправлено успешно
    """
    try:
        # Обработка составных эмоций (например, "сочувствие + поддержка")
        target_emotion = emotion
        if emotion not in EMOTION_IMAGES:
            # Если составная эмоция, берем первую часть
            if '+' in emotion:
                target_emotion = emotion.split('+')[0].strip()
                logger.info(f"Составная эмоция '{emotion}' -> используем '{target_emotion}'")
            
            # Если все еще не найдена, ищем по частичному совпадению
            if target_emotion not in EMOTION_IMAGES:
                for key in EMOTION_IMAGES.keys():
                    if target_emotion in key or key in target_emotion:
                        target_emotion = key
                        logger.info(f"Найдено частичное совпадение: '{emotion}' -> '{target_emotion}'")
                        break
                else:
                    logger.warning(f"Изображение для эмоции '{emotion}' не найдено")
                    return False

        image_path = EMOTION_IMAGES[target_emotion]

        # Проверяем существование файла
        if not os.path.exists(image_path):
            logger.error(f"Файл изображения не найден: {image_path}")
            return False

        # Отправляем изображение с подписью
        photo = FSInputFile(image_path)
        await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, parse_mode="HTML")

        logger.info(f"Изображение с эмоцией '{emotion}' отправлено в чат {chat_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка при отправке изображения с эмоцией '{emotion}': {e}")
        return False

def get_available_emotions() -> str:
    """
    Возвращает список доступных эмоций для использования в промпте.

    Returns:
        str: Строка с перечислением эмоций
    """
    emotions_list = list(EMOTION_IMAGES.keys())
    return ", ".join(emotions_list)