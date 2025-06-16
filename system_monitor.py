
#!/usr/bin/env python3
import psutil
import logging
import asyncio
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self, check_interval=300):  # 5 минут
        self.check_interval = check_interval
        
    async def start_monitoring(self):
        """Запускает мониторинг системных ресурсов."""
        logger.info("📊 Запуск мониторинга системных ресурсов")
        
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_resources()
            except asyncio.CancelledError:
                logger.info("🛑 Мониторинг ресурсов остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в мониторинге ресурсов: {e}")
                
    async def _check_resources(self):
        """Проверяет использование ресурсов."""
        try:
            # Проверяем использование памяти
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Проверяем процессы бота
            bot_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent', 'cpu_percent']):
                try:
                    if 'main.py' in ' '.join(proc.info['cmdline'] or []):
                        bot_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            logger.info(f"💾 Память: {memory.percent:.1f}% | CPU: {cpu_percent:.1f}% | Процессов бота: {len(bot_processes)}")
            
            # Предупреждения о высоком использовании ресурсов
            if memory.percent > 85:
                logger.warning(f"⚠️ Высокое использование памяти: {memory.percent:.1f}%")
            
            if cpu_percent > 80:
                logger.warning(f"⚠️ Высокое использование CPU: {cpu_percent:.1f}%")
                
            if len(bot_processes) > 3:
                logger.warning(f"⚠️ Слишком много процессов бота: {len(bot_processes)}")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке ресурсов: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    monitor = SystemMonitor()
    asyncio.run(monitor.start_monitoring())
