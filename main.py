import asyncio
import signal
import sys
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from m_config import logger, TELEGRAM_TOKEN
from m_handlers import (
    start_router,
    reset_dialog_handler,
    reload_prompts,
    show_prompt,
    cmd_user_info,
    cmd_all_users,
    deepseek_router
)
from broadcaster import broadcast_command_handler
from docs_loader import DocsLoader
from sheets_logger import SheetsLogger
from user_manager import UserManager
from user_data_manager import UserDataManager
from m_prompts import load_all_prompts
from m_utils import get_bot_info
from dialog_manager import DialogManager

# Глобальная переменная для бота
bot = None

async def main():
    """Основная функция запуска бота."""
    global bot

    if not TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN не установлен в переменных окружения! Бот не может быть запущен.")
        sys.exit(1)

    # Настройка обработки сигналов для graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        logger.info(f"🛑 Получен сигнал {sig}. Инициация graceful shutdown...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()
    router = Router()
    
    # Добавляем диагностическое логирование
    logger.info("🚀 Инициализация бота началась...")
    
    # Проверяем соединение с Telegram API с повторными попытками
    max_connection_attempts = 3
    for attempt in range(max_connection_attempts):
        try:
            bot_info = await bot.get_me()
            logger.info(f"✅ Соединение с Telegram API установлено. Бот: @{bot_info.username}")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка соединения с Telegram API (попытка {attempt + 1}/{max_connection_attempts}): {e}")
            if attempt == max_connection_attempts - 1:
                logger.critical("Не удалось установить соединение с Telegram API после всех попыток")
                await bot.session.close()
                sys.exit(1)
            await asyncio.sleep(5)

    try:
        # Инициализация компонентов
        docs_loader_instance = DocsLoader()
        load_all_prompts(docs_loader_instance)

        try:
            sheets_logger_instance = SheetsLogger()
            sheets_logger_instance.create_headers_if_needed()
        except Exception as e:
            logger.error(f"Не удалось инициализировать SheetsLogger: {e}. Логирование в Google Sheets будет недоступно.", exc_info=True)
            sheets_logger_instance = None

        user_manager = UserManager()
        user_data_manager = UserDataManager()
        dialog_manager = DialogManager()

        # Добавляем DialogManager в объект бота для доступа из других модулей
        bot.dialog_manager = dialog_manager

        # Регистрация обработчиков
        router.message.register(start_router, CommandStart())
        # Создаем обертки для обработчиков с зависимостями
        async def reset_handler_wrapper(message):
            await reset_dialog_handler(message, sheets_logger_instance)

        async def reload_prompts_wrapper(message):
            await reload_prompts(message, docs_loader_instance)

        async def show_prompt_wrapper(message):
            await show_prompt(message, docs_loader_instance)

        async def user_info_wrapper(message):
            await cmd_user_info(message, user_data_manager)

        async def all_users_wrapper(message):
            await cmd_all_users(message, user_data_manager)

        async def deepseek_wrapper(message):
            await deepseek_router(message, docs_loader_instance, sheets_logger_instance, user_data_manager, user_manager)

        router.message.register(reset_handler_wrapper, Command("reset"))
        router.message.register(reload_prompts_wrapper, Command("reload_prompts"))
        router.message.register(show_prompt_wrapper, Command("show_prompt"))
        router.message.register(user_info_wrapper, Command("user_info"))
        router.message.register(all_users_wrapper, Command("all_users"))

        # Регистрация команды broadcast
        async def broadcast_handler_wrapper(message):
            from m_config import ADMIN_IDS
            await broadcast_command_handler(
                message=message,
                bot=bot,
                sheets_logger_instance=sheets_logger_instance,
                user_manager=user_manager,
                ADMIN_IDS=ADMIN_IDS
            )

        router.message.register(broadcast_handler_wrapper, Command("broadcast"))
        router.message.register(deepseek_wrapper)

        dp.include_router(router)

        # Добавление данных в workflow
        dp.workflow_data.update({
            "sheets_logger_instance": sheets_logger_instance,
            "user_manager": user_manager,
            "user_data_manager": user_data_manager,
            "docs_loader_instance": docs_loader_instance
        })

        # Получение информации о боте
        bot_info = get_bot_info()
        logger.info(f"🤖 Запускается {bot_info['name']}...")

        # Настройка graceful shutdown
        async def on_shutdown():
            logger.info("🛑 Завершение работы бота...")
            try:
                await bot.session.close()
                logger.info("✅ Сессия бота закрыта")
            except Exception as e:
                logger.error(f"Ошибка при закрытии сессии бота: {e}")
            
        # Запускаем мониторинг состояния
        from health_checker import BotHealthChecker
        health_checker = BotHealthChecker(bot)
        health_task = asyncio.create_task(health_checker.start_monitoring())
        
        try:
            logger.info("🔄 Запуск polling...")
            
            # Создаем задачу для polling
            polling_task = asyncio.create_task(dp.start_polling(
                bot, 
                polling_timeout=20,  # Таймаут для long polling
                request_timeout=15,  # Таймаут для HTTP запросов
                skip_updates=True    # Пропускаем накопленные сообщения при перезапуске
            ))
            
            # Ждем либо завершения polling, либо сигнала остановки
            done, pending = await asyncio.wait(
                [polling_task, asyncio.create_task(shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Отменяем незавершенные задачи
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
            logger.info("📊 Polling остановлен")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в polling: {e}", exc_info=True)
            raise
        finally:
            # Останавливаем мониторинг
            health_task.cancel()
            try:
                await health_task
            except asyncio.CancelledError:
                pass
            
            await on_shutdown()

    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)

def run_bot():
    """Запускает бота."""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_bot()