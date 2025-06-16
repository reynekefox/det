from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from m_config import logger, ADMIN_IDS, BOT_NAME, BOT_USERNAME, TELEGRAM_TOKEN
from m_utils import get_bot_info
from ds_utils import add_message_to_deepseek_dialog, send_long_message_safe
from ds_message_handler import handle_deepseek_message
from datetime import datetime

router = Router()

@router.message(CommandStart())
async def start_router(message: Message):
    """Обработчик команды /start"""
    try:
        welcome_message = (
            "👋 Привет! Я ваш ИИ-помощник по вопросам детского воспитания и мотивации. Я здесь, чтобы помочь родителям справиться с трудностями, связанными с воспитанием, обучением, мотивацией и дисциплиной, разобраться в причинах нежелания ребенка учиться, подобрать способы мотивации, подходящие именно вашему ребенку, найти подход к сложностям в поведении.\n\n"
            "Я могу:\n"
            "✨ Выдать подробный гайд по вашей проблеме.\n"
            "🛠️ Разработать стратегию и конкретные шаги по решению вашей проблемы с индивидуальными рекомендациями.\n"
            "🧩 Сгенерировать для вас персональные идеи мотивирующих сказок или историй, которые помогут вашему ребенку понять ценность знаний в игровой форме.\n"
            "🎲 Предложить подборку развивающих игр, адаптированных под возраст вашего ребенка, которые сделают процесс обучения увлекательным.\n\n"
            "Расскажите, пожалуйста, с каким вопросом или проблемой вы столкнулись? И сколько лет вашему ребенку? 🤔"
        )
        await message.answer(welcome_message)

        # Логируем сообщение в Google Sheets
        try:
            if hasattr(message.bot, "sheets_logger") and message.bot.sheets_logger:
                await message.bot.sheets_logger.log_message(
                    user_name=message.from_user.full_name,
                    user_id=message.from_user.id,
                    message_text="/start",
                    is_user=True
                )
        except Exception as e:
            logger.error(f"Ошибка при логировании в Google Sheets: {str(e)}")

    except Exception as e:
        logger.error(f"Ошибка в start_router: {str(e)}")
        await message.answer("Извините, произошла ошибка. Пожалуйста, попробуйте позже.")
        raise

async def reset_dialog_handler(message: Message, user_data_manager=None):
    """Сброс диалога пользователя."""
    user_id = message.from_user.id

    try:
        # Очищаем диалог используя новую функцию
        from ds_utils import clear_dialog_history
        clear_dialog_history(user_id, message.bot)

        await message.answer("Диалог сброшен. Давайте начнем заново! 😊")
        logger.info(f"Диалог пользователя {user_id} сброшен")

    except Exception as e:
        logger.error(f"Ошибка при сбросе диалога пользователя {user_id}: {e}")
        await message.answer("Произошла ошибка при сбросе диалога.")

async def reload_prompts(message: Message, docs_loader_instance):
    """Обработчик команды /reload_prompts."""
    from m_prompts import load_all_prompts

    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("У вас нет прав для использования этой команды.")
        return
    try:
        await message.answer("🔄 Обновляю кешированные инструкции...")
        load_all_prompts(docs_loader_instance)
        await message.answer("✅ Кешированные инструкции успешно обновлены!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении кешированных инструкций: {e}")
        await message.answer("❌ Произошла ошибка при обновлении инструкций.")

async def show_prompt(message: Message, docs_loader_instance):
    """Обработчик команды /show_prompt."""
    from m_prompts import get_system_prompt_content

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    try:
        prompt = await get_system_prompt_content(docs_loader_instance)
        await send_long_message_safe(message, prompt, parse_mode=None)
    except Exception as e:
        logger.error(f"Ошибка при показе промпта: {e}")
        await message.answer("Произошла ошибка при получении промпта.")

async def cmd_user_info(message: Message, user_data_manager):
    """Обработчик команды /user_info."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /user_info <user_id>")
        return
    try:
        user_id = int(args[1])
        user_data = user_data_manager.get_user_data(user_id)
        info = (
            f"📊 Информация о пользователе {user_id}\n\n"
            f"🆕 Создан: {user_data['created_at']}\n"
            f"📚 Мануал отправлен: {'Да' if user_data['manual_sent'] else 'Нет'}\n"
        )
        if user_data['manual_sent']:
            info += f"📅 Дата отправки мануала: {user_data['manual_sent_at']}\n"
        info += f"⏰ Последнее взаимодействие: {user_data['last_interaction']}"
        await message.answer(info)
    except ValueError:
        await message.answer("Неверный формат ID пользователя. Используйте числовой ID.")
    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}")
        await message.answer("Произошла ошибка при получении информации о пользователе.")

async def cmd_all_users(message: Message, user_data_manager):
    """Обработчик команды /all_users."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    try:
        users_data = user_data_manager.get_all_users_data()
        if not users_data:
            await message.answer("Нет данных о пользователях.")
            return
        info = "📊 Список всех пользователей:\n\n"
        for user_id, data in users_data.items():
            info += (
                f"👤 ID: {user_id}\n"
                f"📚 Мануал: {'✅' if data['manual_sent'] else '❌'}\n"
                f"⏰ Последняя активность: {data['last_interaction']}\n\n"
            )
        await send_long_message_safe(message, info)
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        await message.answer("Произошла ошибка при получении списка пользователей.")

@router.message()
async def deepseek_router(message: Message, docs_loader_instance, sheets_logger_instance=None, user_data_manager=None, user_manager=None):
    """Обработчик сообщений для DeepSeek."""
    user_id = message.from_user.id
    logger.info(f"[ВХОДЯЩЕЕ_СООБЩЕНИЕ] От пользователя {user_id}: '{message.text}' (message_id: {message.message_id})")
    
    if user_data_manager:
        user_data_manager.update_last_interaction(user_id)
    logger.info(f"Получено сообщение от пользователя {user_id}: {message.text[:50]}...")
    try:
        await handle_deepseek_message(
            message=message,
            user_data_manager=user_data_manager,
            user_manager=user_manager,
            sheets_logger_instance=sheets_logger_instance,
            docs_loader_instance=docs_loader_instance
        )
    except Exception as e:
        logger.error(f"Ошибка в deepseek_router: {str(e)}")
        await message.answer("Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте позже.")
        raise