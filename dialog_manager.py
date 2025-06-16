
import json
import os
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DialogManager:
    def __init__(self, data_dir: str = "dialogs"):
        """
        Инициализация менеджера диалогов с постоянным хранением
        
        Args:
            data_dir: Директория для хранения файлов диалогов
        """
        self.data_dir = data_dir
        self._ensure_data_dir()
        self.dialogs_cache = {}  # Кэш диалогов в памяти для быстрого доступа
        self._load_all_dialogs()
        
    def _ensure_data_dir(self) -> None:
        """Создает директорию для диалогов, если она не существует"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Создана директория для диалогов: {self.data_dir}")
    
    def _get_dialog_file_path(self, user_id: int) -> str:
        """Возвращает путь к файлу диалога пользователя"""
        return os.path.join(self.data_dir, f"dialog_{user_id}.json")
    
    def _load_all_dialogs(self) -> None:
        """Загружает все существующие диалоги в кэш"""
        if not os.path.exists(self.data_dir):
            return
            
        for filename in os.listdir(self.data_dir):
            if filename.startswith("dialog_") and filename.endswith(".json"):
                try:
                    user_id = int(filename[7:-5])  # Извлекаем ID из имени файла
                    self.dialogs_cache[user_id] = self._load_dialog_from_file(user_id)
                except Exception as e:
                    logger.error(f"Ошибка при загрузке диалога из файла {filename}: {e}")
        
        logger.info(f"Загружено {len(self.dialogs_cache)} диалогов из файлов")
    
    def _load_dialog_from_file(self, user_id: int) -> Dict[str, Any]:
        """Загружает диалог пользователя из файла"""
        file_path = self._get_dialog_file_path(user_id)
        if not os.path.exists(file_path):
            return {"messages": []}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при чтении диалога пользователя {user_id}: {e}")
            return {"messages": []}
    
    def _save_dialog_to_file(self, user_id: int) -> None:
        """Сохраняет диалог пользователя в файл"""
        if user_id not in self.dialogs_cache:
            return
            
        file_path = self._get_dialog_file_path(user_id)
        try:
            dialog_data = self.dialogs_cache[user_id].copy()
            dialog_data["last_updated"] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(dialog_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Диалог пользователя {user_id} сохранен в файл")
        except Exception as e:
            logger.error(f"Ошибка при сохранении диалога пользователя {user_id}: {e}")
    
    def get_dialog(self, user_id: int) -> Dict[str, Any]:
        """Получает диалог пользователя"""
        if user_id not in self.dialogs_cache:
            self.dialogs_cache[user_id] = {"messages": []}
        return self.dialogs_cache[user_id]
    
    def add_message(self, user_id: int, role: str, content: str) -> None:
        """Добавляет сообщение в диалог пользователя"""
        if user_id not in self.dialogs_cache:
            self.dialogs_cache[user_id] = {"messages": []}
        
        message_data = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.dialogs_cache[user_id]["messages"].append(message_data)
        self._save_dialog_to_file(user_id)
        logger.debug(f"Добавлено сообщение в диалог пользователя {user_id}: {role} - {content[:50]}...")
    
    def clear_dialog(self, user_id: int) -> None:
        """Очищает диалог пользователя"""
        self.dialogs_cache[user_id] = {"messages": []}
        self._save_dialog_to_file(user_id)
        logger.info(f"Диалог пользователя {user_id} очищен")
    
    def get_messages(self, user_id: int) -> List[Dict[str, str]]:
        """Получает все сообщения диалога пользователя"""
        dialog = self.get_dialog(user_id)
        return dialog.get("messages", [])
    
    def get_all_users_with_dialogs(self) -> List[int]:
        """Возвращает список всех пользователей, у которых есть диалоги"""
        return list(self.dialogs_cache.keys())
    
    def backup_all_dialogs(self, backup_file: str = None) -> str:
        """Создает резервную копию всех диалогов"""
        if backup_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"dialogs_backup_{timestamp}.json"
        
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(self.dialogs_cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Создана резервная копия диалогов: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии: {e}")
            return None
