import asyncio
import logging
import re
from typing import Optional, Dict, Any
from aiogram.types import Message

from ds_models import choose_deepseek_model
from ds_api import make_deepseek_request
from ds_utils import send_long_message_safe, format_dialog_history, _split_message_smartly
from emotion_handler import extract_emotion_from_text, remove_emotion_tags, send_emotion_image

logger = logging.getLogger(__name__)

def convert_markdown_to_html(text: str) -> str:
    """
    Конвертирует markdown разметку в HTML-теги, поддерживаемые Telegram.
    """
    # Конвертируем жирный текст **text** и __text__ в <b>text</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

    # Конвертируем курсив *text* и _text_ в <i>text</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)

    # Конвертируем моноширинный код `text` в <code>text</code>
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)

    # Удаляем блоки кода (они плохо отображаются в Telegram)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

    # Конвертируем ссылки [text](url) в <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', text)

    return text

async def handle_deepseek_message(
    message: Message,
    user_data_manager=None,
    user_manager=None,
    sheets_logger_instance=None,
    docs_loader_instance=None
):
    """Обрабатывает сообщение и отправляет его в DeepSeek API."""
    user_id = message.from_user.id
    start_time = asyncio.get_event_loop().time()
    logger.info(f"[НАЧАЛО_ОБРАБОТКИ] Пользователь {user_id}: {message.text[:50]}...")

    try:
        # Устанавливаем общий таймаут на обработку сообщения
        async with asyncio.timeout(90):  # 1.5 минуты максимум
            """
            Обрабатывает сообщение пользователя с помощью DeepSeek API.

            Args:
                message: Объект сообщения от пользователя
                is_classification_request: Флаг, указывающий что это запрос на классификацию
                dialog_history_override: Переопределение истории диалога
                max_tokens_override: Переопределение максимального количества токенов
            """
            try:
                user_id = message.from_user.id
                logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] НАЧАЛО обработки сообщения от пользователя {user_id}: '{message.text[:100]}...'")

                # Добавляем пользователя в user_manager для рассылки (делаем это в самом начале)
                if user_manager:
                    user_manager.add_user(user_id)
                    logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Пользователь {user_id} добавлен в user_manager")

                # Обновляем время последнего взаимодействия
                user_data_manager.update_last_interaction(user_id)
                logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Время последнего взаимодействия обновлено для {user_id}")

                # Выбираем модель
                logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Начинаем выбор модели для {user_id}")
                model, model_choice = await choose_deepseek_model(message)
                logger.info(f"🧠 Используется модель '{model}' для ответа (выбор: {model_choice})")
                logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Модель выбрана: {model}")

                # Проверяем доступность reasoning модели
                if model_choice == "reasoning":
                    from ds_models import test_model_availability
                    if not await test_model_availability("deepseek-reasoner"):
                        logger.warning("[DeepSeek] Reasoning модель недоступна, переключаемся на chat")
                        model = "deepseek-chat"
                        model_choice = "chat"
                        await message.answer("🤔 Надо подумать... Упс, не получилось, отвечу проще!")
                        thinking_message = None
                    else:
                        thinking_message = await message.answer("🤔 Надо подумать...")
                else:
                    thinking_message = None

                # Получаем историю диалога
                from ds_utils import get_dialog_history
                dialog_history = get_dialog_history(message.from_user.id, message.bot)

                # Добавляем текущее сообщение пользователя в историю
                from ds_utils import add_message_to_deepseek_dialog
                add_message_to_deepseek_dialog(message=message, is_user=True)

                # Форматируем историю диалога
                formatted_messages = format_dialog_history(dialog_history)

                # Получаем системный промпт из docs_loader
                from m_prompts import get_system_prompt_content
                try:
                    system_prompt_content = await get_system_prompt_content(docs_loader_instance)
                except Exception as e:
                    logger.error(f"Ошибка получения системного промпта: {e}")
                    system_prompt_content = ("Ты — опытный детский психолог и педагог. Твоя задача — помогать родителям в воспитании детей, "
                                           "отвечать на их вопросы о развитии, обучении и поведении детей. Используй научный подход, "
                                           "но объясняй простым языком. Всегда проявляй эмпатию и понимание к родителям.")

                system_message = {
                    "role": "system",
                    "content": system_prompt_content
                }
                formatted_messages.insert(0, system_message)

                # Отправляем запрос к API
                logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Отправляем запрос к DeepSeek API для {user_id}")
                response = await make_deepseek_request(
                    messages=formatted_messages,
                    model=model,
                    temperature=0.05,
                    max_tokens=None
                )

                logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Получен ответ от DeepSeek API для {user_id}")
                logger.info(f"[DeepSeek] Ответ: {response}")

                if not response or "choices" not in response or not response["choices"]:
                    logger.error(f"[ДЕТАЛЬНЫЙ_ЛОГ] ОШИБКА: Не удалось получить ответ от DeepSeek API для {user_id}")
                    await message.answer("Извините, произошла ошибка при обработке вашего запроса.")
                    return

                # Получаем текст ответа
                response_text = response["choices"][0]["message"]["content"]

                # Извлекаем эмоцию из ответа
                emotion = extract_emotion_from_text(response_text)

                # Удаляем теги эмоций из текста
                response_text = remove_emotion_tags(response_text)

                # Конвертируем markdown в HTML
                response_text = convert_markdown_to_html(response_text)

                # Асинхронно логируем пользовательское сообщение в Google Sheets (не блокируем ответ)
                if sheets_logger_instance:
                    asyncio.create_task(sheets_logger_instance.log_message_async(
                        user_name=message.from_user.full_name,
                        user_id=message.from_user.id,
                        message_text=message.text,
                        is_user=True
                    ))

                # Удаляем сообщение 'Надо подумать...', если оно было
                if thinking_message:
                    try:
                        await thinking_message.delete()
                    except Exception:
                        pass

                # Если есть эмоция, всегда отправляем изображение с текстом как подпись
                if emotion:
                    logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Отправляем ответ с эмоцией '{emotion}' для {user_id}")
                    # Проверяем длину текста (лимит подписи в Telegram - 1024 символа)
                    if len(response_text) <= 1024:
                        # Текст помещается в подпись - отправляем одним сообщением
                        await send_emotion_image(message.bot, message.chat.id, emotion, response_text)
                        logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Отправлено одно сообщение с картинкой для {user_id}")
                    else:
                        # Текст слишком длинный - разбиваем на части и к последней части добавляем картинку
                        chunks = _split_message_smartly(response_text, 900)  # Оставляем место для индикатора части
                        logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Разбиваем текст на {len(chunks)} частей для {user_id}")

                        # Отправляем все части кроме последней как обычный текст
                        for i, chunk in enumerate(chunks[:-1]):
                            try:
                                chunk_with_indicator = f"📝 Часть {i+1}/{len(chunks)}:\n\n{chunk}"
                                logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Отправляем часть {i+1}/{len(chunks)} для {user_id}")
                                await message.answer(chunk_with_indicator, parse_mode="HTML")
                                logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Успешно отправлена часть {i+1}/{len(chunks)} для {user_id}")

                                # Добавляем задержку между частями
                                await asyncio.sleep(0.5)

                            except Exception as e:
                                logger.error(f"[ДЕТАЛЬНЫЙ_ЛОГ] ОШИБКА при отправке части {i+1}/{len(chunks)} для {user_id}: {e}")
                                # Пытаемся отправить без HTML разметки
                                try:
                                    await message.answer(chunk_with_indicator)
                                    logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Fallback успешен для части {i+1}/{len(chunks)}")
                                except Exception as e2:
                                    logger.error(f"[ДЕТАЛЬНЫЙ_ЛОГ] КРИТИЧЕСКАЯ ОШИБКА части {i+1}/{len(chunks)}: {e2}")

                # Последнюю часть отправляем как подпись к картинке
                        try:
                            last_chunk = chunks[-1]
                            if len(chunks) > 1:
                                last_chunk_with_indicator = f"📝 Часть {len(chunks)}/{len(chunks)}:\n\n{last_chunk}"
                            else:
                                last_chunk_with_indicator = last_chunk

                            logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Отправляем последнюю часть с картинкой для {user_id}")
                            await send_emotion_image(message.bot, message.chat.id, emotion, last_chunk_with_indicator)
                            logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Успешно отправлена последняя часть с картинкой для {user_id}")
                        except Exception as e:
                            logger.error(f"[ДЕТАЛЬНЫЙ_ЛОГ] ОШИБКА при отправке последней части с картинкой для {user_id}: {e}")
                else:
                    logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Отправляем ответ без эмоции для {user_id}")
                    # Если эмоции нет, отправляем только текст
                    await send_long_message_safe(message, response_text, parse_mode="HTML")
                    logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] Текстовый ответ отправлен для {user_id}")

                # Асинхронно логируем ответ бота в Google Sheets (не блокируем пользователя)
                if sheets_logger_instance:
                    asyncio.create_task(sheets_logger_instance.log_message_async(
                        user_name=message.from_user.full_name,
                        user_id=message.from_user.id,
                        message_text=response_text,
                        is_user=False
                    ))

        # Добавляем ответ бота в историю диалога
                add_message_to_deepseek_dialog(
                    user_id=message.from_user.id,
                    role="assistant", 
                    content=response["choices"][0]["message"]["content"],
                    bot=message.bot
                )

                logger.info(f"[ДЕТАЛЬНЫЙ_ЛОГ] УСПЕХ: Обработка сообщения завершена для {user_id}")

            except asyncio.TimeoutError:
                logger.error(f"[ДЕТАЛЬНЫЙ_ЛОГ] ТАЙМАУТ при обработке сообщения для {user_id}")
                try:
                    await message.answer("⏰ Извините, обработка заняла слишком много времени. Попробуйте еще раз.")
                except Exception:
                    pass
                return
            except Exception as e:
                logger.error(f"[ДЕТАЛЬНЫЙ_ЛОГ] ОШИБКА при обработке сообщения для {user_id}: {e}", exc_info=True)
                try:
                    await message.answer("😔 Извините, произошла ошибка при обработке вашего запроса. Попробуйте еще раз.")
                except Exception:
                    pass
                return

    except asyncio.TimeoutError:
        processing_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"⏰ ТАЙМАУТ обработки сообщения от пользователя {user_id} после {processing_time:.2f}с")
        await message.answer("Извините, обработка вашего сообщения заняла слишком много времени. Попробуйте еще раз.")
    except Exception as e:
        processing_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"❌ Ошибка при обработке сообщения от пользователя {user_id} за {processing_time:.2f}с: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте позже.")
    finally:
        processing_time = asyncio.get_event_loop().time() - start_time
        logger.info(f"[КОНЕЦ_ОБРАБОТКИ] Пользователь {user_id}: обработка заняла {processing_time:.2f}с")