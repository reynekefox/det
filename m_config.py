import os
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Отладочная информация о загрузке переменных
print(f"DEBUG: .env файл загружен")
print(f"DEBUG: TELEGRAM_TOKEN из os.getenv: {os.getenv('TELEGRAM_TOKEN')}")
print(f"DEBUG: Все переменные окружения с TELEGRAM: {[k for k in os.environ.keys() if 'TELEGRAM' in k]}")

# Создание директории для логов
os.makedirs('logs', exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/bot.log', encoding='utf-8')
    ]
)

# Создание логгера
logger = logging.getLogger(__name__)

# Константы
ADMIN_IDS = [int(os.getenv("ADMIN_TELEGRAM_ID", "236147307"))]
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_NAME = "Тест родительского ИИ"
BOT_USERNAME = "parrentstest_bot"

# Проверка наличия токена
if not TELEGRAM_TOKEN:
    logger.critical("TELEGRAM_TOKEN не установлен в переменных окружения! Бот не может быть запущен.")
    exit(1)