import logging
from typing import List, Dict, Any
from aiogram.types import Message

logger = logging.getLogger(__name__)

async def send_long_message_safe(message: Message, text: str, parse_mode=None, chunk_size=2000) -> None:
    """
    Безопасно отправляет длинное сообщение, разбивая его на части если необходимо.

    Args:
        message: Объект сообщения для ответа
        text: Текст для отправки
        parse_mode: Режим разметки для отправки сообщения
        chunk_size: Максимальная длина одной части сообщения
    """
    try:
        if len(text) <= chunk_size:
            await message.answer(text, parse_mode=parse_mode)
            return

        # Умная разбивка на части
        chunks = _split_message_smartly(text, chunk_size)
        
        for i, chunk in enumerate(chunks):
            try:
                logger.info(f"[ОТПРАВКА_ЧАСТИ] Отправляем часть {i+1}/{len(chunks)} пользователю {message.from_user.id}")
                # Добавляем индикатор части если частей больше одной
                if len(chunks) > 1:
                    chunk_with_indicator = f"📝 Часть {i+1}/{len(chunks)}:\n\n{chunk}"
                    await message.answer(chunk_with_indicator, parse_mode=parse_mode)
                else:
                    await message.answer(chunk, parse_mode=parse_mode)
                logger.info(f"[ОТПРАВКА_ЧАСТИ] Успешно отправлена часть {i+1}/{len(chunks)} пользователю {message.from_user.id}")
                
                # Добавляем небольшую задержку между частями
                if i < len(chunks) - 1:  # не добавляем задержку после последней части
                    import asyncio
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                # fallback если parse_mode не подошёл
                logger.error(f"[ОТПРАВКА_ЧАСТИ] Ошибка при отправке части {i+1}/{len(chunks)} пользователю {message.from_user.id}: {e}")
                try:
                    if len(chunks) > 1:
                        chunk_with_indicator = f"📝 Часть {i+1}/{len(chunks)}:\n\n{chunk}"
                        await message.answer(chunk_with_indicator)
                    else:
                        await message.answer(chunk)
                    logger.info(f"[ОТПРАВКА_ЧАСТИ] Fallback успешен для части {i+1}/{len(chunks)}")
                except Exception as e2:
                    logger.error(f"[ОТПРАВКА_ЧАСТИ] КРИТИЧЕСКАЯ ОШИБКА: не удалось отправить часть {i+1}/{len(chunks)}: {e2}")
                    # Пытаемся отправить хотя бы уведомление об ошибке
                    try:
                        await message.answer(f"❌ Не удалось отправить часть {i+1}/{len(chunks)} сообщения")
                    except:
                        pass

    except Exception as e:
        logger.error(f"Ошибка при отправке длинного сообщения: {str(e)}")
        await message.answer("Извините, произошла ошибка при отправке сообщения.")

def _split_message_into_chunks(text: str, max_length: int) -> List[str]:
    """
    Разбивает текст на части заданной максимальной длины.

    Args:
        text: Исходный текст
        max_length: Максимальная длина одной части

    Returns:
        List[str]: Список частей текста
    """
    chunks = []
    current_chunk = ""

    for line in text.split("\n"):
        if len(current_chunk) + len(line) + 1 <= max_length:
            current_chunk += line + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line + "\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def _split_message_smartly(text: str, max_length: int) -> List[str]:
    """
    Умно разбивает текст на части, стараясь сохранить целостность абзацев и предложений.

    Args:
        text: Исходный текст
        max_length: Максимальная длина одной части

    Returns:
        List[str]: Список частей текста
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Сначала пробуем разбить по абзацам
    paragraphs = text.split("\n\n")
    
    for paragraph in paragraphs:
        # Если абзац помещается в текущий chunk
        if len(current_chunk) + len(paragraph) + 2 <= max_length:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
        else:
            # Сохраняем текущий chunk если он не пустой
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Если абзац слишком большой, разбиваем его по предложениям
            if len(paragraph) > max_length:
                sentences = paragraph.split(". ")
                temp_chunk = ""
                
                for i, sentence in enumerate(sentences):
                    sentence_with_dot = sentence + ("." if i < len(sentences) - 1 else "")
                    
                    if len(temp_chunk) + len(sentence_with_dot) + 1 <= max_length:
                        if temp_chunk:
                            temp_chunk += " " + sentence_with_dot
                        else:
                            temp_chunk = sentence_with_dot
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = sentence_with_dot
                
                current_chunk = temp_chunk
            else:
                current_chunk = paragraph
    
    # Добавляем последний chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def format_dialog_history(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Форматирует историю диалога для отправки в API.

    Args:
        messages: Список сообщений в формате [{"role": "...", "content": "..."}]

    Returns:
        List[Dict[str, str]]: Отформатированная история диалога
    """
    formatted_messages = []

    for msg in messages:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            formatted_messages.append({
                "role": msg["role"],
                "content": str(msg["content"])
            })

    return formatted_messages

def add_message_to_deepseek_dialog(user_id: int = None, role: str = None, content: str = None, message: Message = None, is_user: bool = True, bot=None) -> None:
    """
    Добавляет сообщение в историю диалога DeepSeek.

    Args:
        user_id: ID пользователя (если не передан message)
        role: Роль сообщения ('user' или 'assistant')
        content: Содержимое сообщения
        message: Объект сообщения (альтернативный способ передачи данных)
        is_user: Флаг, указывающий что это сообщение от пользователя
        bot: Объект бота (требуется если не передан message)
    """
    try:
        # Определяем параметры из message или напрямую
        if message:
            user_id = message.from_user.id
            content = message.text
            role = "user" if is_user else "assistant"
            bot = message.bot

        if not bot:
            logger.error("Не удалось получить объект бота для сохранения диалога")
            return

        # Используем DialogManager если он есть, иначе старую систему
        if hasattr(bot, "dialog_manager"):
            bot.dialog_manager.add_message(user_id, role, content)
        else:
            # Fallback на старую систему (для совместимости)
            if not hasattr(bot, "dialogs"):
                bot.dialogs = {}

            if user_id not in bot.dialogs:
                bot.dialogs[user_id] = {"messages": []}

            message_data = {
                "role": role,
                "content": content
            }

            bot.dialogs[user_id]["messages"].append(message_data)
            logger.info(f"Добавлено сообщение в диалог пользователя {user_id}: {role} - {content[:50]}...")

    except Exception as e:
        logger.error(f"Ошибка при добавлении сообщения в диалог: {e}")

def get_dialog_history(user_id: int, bot) -> List[Dict[str, str]]:
    """
    Получает историю диалога пользователя.
    
    Args:
        user_id: ID пользователя
        bot: Объект бота
        
    Returns:
        Список сообщений диалога
    """
    try:
        # Используем DialogManager если он есть
        if hasattr(bot, "dialog_manager"):
            return bot.dialog_manager.get_messages(user_id)
        else:
            # Fallback на старую систему
            if not hasattr(bot, "dialogs"):
                return []
            return bot.dialogs.get(user_id, {}).get("messages", [])
    except Exception as e:
        logger.error(f"Ошибка при получении истории диалога пользователя {user_id}: {e}")
        return []

def clear_dialog_history(user_id: int, bot) -> None:
    """
    Очищает историю диалога пользователя.
    
    Args:
        user_id: ID пользователя
        bot: Объект бота
    """
    try:
        if hasattr(bot, "dialog_manager"):
            bot.dialog_manager.clear_dialog(user_id)
        else:
            # Fallback на старую систему
            if hasattr(bot, "dialogs") and user_id in bot.dialogs:
                bot.dialogs[user_id] = {"messages": []}
        logger.info(f"Диалог пользователя {user_id} очищен")
    except Exception as e:
        logger.error(f"Ошибка при очистке диалога пользователя {user_id}: {e}")