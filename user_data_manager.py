import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class UserDataManager:
    def __init__(self, data_dir: str = "user_data"):
        """
        Инициализация менеджера данных пользователей
        
        Args:
            data_dir: Директория для хранения файлов с данными пользователей
        """
        self.data_dir = data_dir
        self._ensure_data_dir()
        
    def _ensure_data_dir(self) -> None:
        """Создает директорию для данных, если она не существует"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Создана директория для данных пользователей: {self.data_dir}")
    
    def _get_user_file_path(self, user_id: int) -> str:
        """Возвращает путь к файлу данных пользователя"""
        return os.path.join(self.data_dir, f"user_{user_id}.json")
    
    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Получает данные пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Dict с данными пользователя или пустой словарь, если данных нет
        """
        file_path = self._get_user_file_path(user_id)
        if not os.path.exists(file_path):
            return {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "manual_sent": False,
                "manual_sent_at": None,
                "last_interaction": datetime.now().isoformat()
            }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при чтении данных пользователя {user_id}: {e}")
            return {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "manual_sent": False,
                "manual_sent_at": None,
                "last_interaction": datetime.now().isoformat()
            }
    
    def save_user_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """
        Сохраняет данные пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            data: Словарь с данными пользователя
        """
        file_path = self._get_user_file_path(user_id)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Данные пользователя {user_id} успешно сохранены")
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных пользователя {user_id}: {e}")
    
    def mark_manual_sent(self, user_id: int) -> None:
        """
        Отмечает, что мануал был отправлен пользователю
        
        Args:
            user_id: ID пользователя в Telegram
        """
        data = self.get_user_data(user_id)
        data["manual_sent"] = True
        data["manual_sent_at"] = datetime.now().isoformat()
        self.save_user_data(user_id, data)
        logger.info(f"Отмечено, что мануал отправлен пользователю {user_id}")
    
    def update_last_interaction(self, user_id: int) -> None:
        """
        Обновляет время последнего взаимодействия с пользователем
        
        Args:
            user_id: ID пользователя в Telegram
        """
        data = self.get_user_data(user_id)
        data["last_interaction"] = datetime.now().isoformat()
        self.save_user_data(user_id, data)
    
    def get_all_users_data(self) -> Dict[int, Dict[str, Any]]:
        """
        Получает данные всех пользователей
        
        Returns:
            Словарь с данными всех пользователей
        """
        users_data = {}
        for filename in os.listdir(self.data_dir):
            if filename.startswith("user_") and filename.endswith(".json"):
                try:
                    user_id = int(filename[5:-5])  # Извлекаем ID из имени файла
                    users_data[user_id] = self.get_user_data(user_id)
                except Exception as e:
                    logger.error(f"Ошибка при чтении файла {filename}: {e}")
        return users_data 