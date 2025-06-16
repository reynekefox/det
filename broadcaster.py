import asyncio
import logging

from aiogram import Bot
from aiogram.types import Message
from user_manager import UserManager
from ds_utils import add_message_to_deepseek_dialog

logger = logging.getLogger(__name__)

async def send_broadcast_message(bot: Bot, user_manager: UserManager, message_text: str):
    logger.info(f"DEBUG_BROADCAST: В send_broadcast_message получен message_text: '{message_text}'")
    all_user_ids = user_manager.get_all_user_ids()
    logger.info(f"DEBUG_BROADCAST: Список всех user_ids для рассылки: {all_user_ids}")
    logger.info(f"Начинается рассылка сообщения '{message_text[:50]}...' для {len(all_user_ids)} пользователей.")
    sent_count = 0
    blocked_count = 0

    for i, user_id in enumerate(all_user_ids):
        logger.info(f"DEBUG_BROADCAST: Обрабатываем пользователя {i+1}/{len(all_user_ids)}: {user_id}")
        try:
            await bot.send_message(chat_id=user_id, text=message_text, parse_mode='HTML')
            sent_count += 1
            logger.info(f"DEBUG_BROADCAST: Сообщение успешно отправлено в чат {user_id}")

            # --- ЭТО НУЖНО ДОБАВИТЬ: ЗАПИСЬ В ИСТОРИЮ DEEPSEEK ---
            add_message_to_deepseek_dialog(user_id=user_id, role="assistant", content=message_text, bot=bot)
            # --- КОНЕЦ ДОБАВЛЕНИЯ ---

            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"DEBUG_BROADCAST: Не удалось отправить сообщение в чат {user_id}: {e}", exc_info=True)
            if "bot was blocked by the user" in str(e) or "chat not found" in str(e).lower():
                blocked_count += 1
                logger.info(f"DEBUG_BROADCAST: Удаляем заблокированного пользователя {user_id}")
                user_manager.remove_user(user_id)
            await asyncio.sleep(0.1)

    logger.info(f"Рассылка завершена. Отправлено {sent_count} сообщений. Бот был заблокирован {blocked_count} пользователями.")
    return sent_count, blocked_count

async def broadcast_command_handler(
    message: Message,
    bot: Bot,
    sheets_logger_instance,
    user_manager: UserManager,
    ADMIN_IDS
):
    logger.info(f"DEBUG_BROADCAST_CMD: Получена команда /broadcast от пользователя {message.from_user.id}")
    logger.info(f"DEBUG_BROADCAST_CMD: Полный текст сообщения: '{message.text}'")
    logger.info(f"DEBUG_BROADCAST_CMD: ADMIN_IDS: {ADMIN_IDS}")
    logger.info(f"DEBUG_BROADCAST_CMD: Тип message.from_user.id: {type(message.from_user.id)}")
    logger.info(f"DEBUG_BROADCAST_CMD: Тип ADMIN_IDS[0]: {type(ADMIN_IDS[0]) if ADMIN_IDS else 'N/A'}")

    if message.from_user.id not in ADMIN_IDS:
        logger.warning(f"Пользователь {message.from_user.id} попытался использовать /broadcast без прав администратора.")
        await message.answer("У вас нет прав для использования этой команды.")
        return

    current_broadcast_text = message.text.removeprefix("/broadcast").strip().rstrip('/')

    if not current_broadcast_text:
        logger.warning("DEBUG_BROADCAST_CMD: Текст для рассылки пуст после удаления команды.")
        await message.answer("Пожалуйста, укажите текст для рассылки. Пример: `/broadcast Привет всем!`")
        return

    logger.info(f"DEBUG_BROADCAST_CMD: Извлеченный текст для рассылки (current_broadcast_text): '{current_broadcast_text}'")

    await message.answer(f"Начинаю рассылку сообщения:\n\n`{current_broadcast_text}`\n\nЭто может занять некоторое время...", parse_mode='Markdown')

    try:
        logger.info(f"DEBUG_BROADCAST_CMD: Вызов send_broadcast_message с текстом: '{current_broadcast_text}'")
        sent, blocked = await send_broadcast_message(bot, user_manager, current_broadcast_text)
        await message.answer(f"Рассылка завершена. Отправлено {sent} сообщений. Не удалось отправить (бот заблокирован/чат не найден) {blocked} пользователям.")
        if sheets_logger_instance:
            asyncio.create_task(sheets_logger_instance.log_message_async(message.from_user.full_name, message.from_user.id, f"/broadcast: Отправлено {sent}, заблокировано {blocked}", is_user=True))
    except Exception as e:
        logger.error(f"DEBUG_BROADCAST_CMD: Ошибка при выполнении рассылки: {e}", exc_info=True)
        await message.answer("Произошла ошибка при выполнении рассылки. Проверьте логи.")