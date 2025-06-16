# heartbeat_server.py
from flask import Flask
import logging
import os
import signal
import sys
from dotenv import load_dotenv

load_dotenv()

# Настраиваем логирование для Flask-сервера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/heartbeat')
def heartbeat():
    """
    Эндпоинт для проверки состояния сервера.
    Возвращает "OK" и статус 200, если сервер доступен.
    """
    logger.info("Получен запрос на /heartbeat")
    return "OK", 200

if __name__ == '__main__':
    # Обработка сигналов для graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Получен сигнал {signum}. Завершение работы heartbeat сервера...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Используем порт из переменных окружения или по умолчанию 5000
    port = int(os.getenv("FLASK_PORT", 5001))
    host = os.getenv("FLASK_HOST", "0.0.0.0")

    logger.info(f"Запускаю Heartbeat Server на {host}:{port}/heartbeat")
    try:
        app.run(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        logger.info("Heartbeat сервер остановлен через KeyboardInterrupt.")
    except Exception as e:
        logger.critical(f"Ошибка при запуске Flask Heartbeat сервера: {e}", exc_info=True)
        exit(1)