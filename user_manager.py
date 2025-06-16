# user_manager.py

import json
import os
import logging

class UserManager:
    def __init__(self, file_path='user_ids.json'):
        self.file_path = file_path
        self.user_ids = self._load_user_ids()
        logging.info(f"UserManager инициализирован. Загружено {len(self.user_ids)} уникальных user_ids.")

    def _load_user_ids(self):
        """Загружает user_ids из JSON файла."""
        if not os.path.exists(self.file_path):
            return set()
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logging.info(f"DEBUG: Загружено из файла {self.file_path}: {data}")
                # Убедимся, что загружаем set, если в файле list
                result_set = set(data)
                logging.info(f"DEBUG: После конвертации в set: {result_set}")
                return result_set
        except json.JSONDecodeError:
            logging.error(f"Ошибка декодирования JSON из файла {self.file_path}. Файл будет перезаписан.")
            return set()
        except Exception as e:
            logging.error(f"Ошибка при загрузке user_ids из файла {self.file_path}: {e}", exc_info=True)
            return set()

    def save_user_ids(self):
        """Сохраняет user_ids в JSON файл."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                # Сохраняем set как list для JSON
                json.dump(list(self.user_ids), f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"Ошибка при сохранении user_ids в файл {self.file_path}: {e}", exc_info=True)

    def add_user(self, user_id: int):
        """Добавляет user_id в список, если его там нет."""
        if user_id not in self.user_ids:
            self.user_ids.add(user_id)
            self.save_user_ids()
            logging.info(f"Добавлен новый пользователь: {user_id}. Всего пользователей: {len(self.user_ids)}")
            return True
        return False

    def get_all_user_ids(self):
        """Возвращает все сохраненные user_ids."""
        result = list(self.user_ids)
        logging.info(f"DEBUG: get_all_user_ids() возвращает: {result}")
        logging.info(f"DEBUG: Текущий self.user_ids (set): {self.user_ids}")
        return result

    def remove_user(self, user_id: int):
        """Удаляет user_id из списка (например, если бот заблокирован)."""
        if user_id in self.user_ids:
            self.user_ids.remove(user_id)
            self.save_user_ids()
            logging.info(f"Удален пользователь: {user_id}. Всего пользователей: {len(self.user_ids)}")
            return True
        return False