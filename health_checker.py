
import asyncio
import logging
import aiohttp
from datetime import datetime
from m_config import TELEGRAM_TOKEN

logger = logging.getLogger(__name__)

class BotHealthChecker:
    def __init__(self, bot):
        self.bot = bot
        self.last_successful_check = datetime.now()
        self.check_interval = 300  # 5 минут
        
    async def start_monitoring(self):
        """Запускает мониторинг состояния бота."""
        logger.info("🔍 Запуск мониторинга состояния бота")
        
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                logger.info("🛑 Мониторинг остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в мониторинге: {e}")
                
    async def _perform_health_check(self):
        """Выполняет проверку состояния."""
        try:
            # Проверяем соединение с Telegram API
            start_time = asyncio.get_event_loop().time()
            me = await self.bot.get_me()
            response_time = asyncio.get_event_loop().time() - start_time
            
            self.last_successful_check = datetime.now()
            logger.info(f"💚 Бот здоров: @{me.username} (время ответа: {response_time:.2f}с)")
            
            # Проверяем доступность внешних API
            await self._check_external_apis()
            
        except Exception as e:
            logger.error(f"💀 Проблема со здоровьем бота: {e}")
            
    async def _check_external_apis(self):
        """Проверяет доступность внешних API."""
        try:
            # Проверяем DeepSeek API
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.deepseek.com", timeout=10) as response:
                    if response.status in [200, 404]:  # 404 это нормально для корневого URL
                        logger.info("✅ DeepSeek API доступен")
                    else:
                        logger.warning(f"⚠️ DeepSeek API вернул статус {response.status}")
                        
        except Exception as e:
            logger.warning(f"⚠️ Проблема с доступностью DeepSeek API: {e}")
