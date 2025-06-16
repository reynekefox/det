import os
import json
import logging
import asyncio
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re

class SheetsLogger:
    def __init__(self):
        # Пытаемся получить учетные данные из переменной окружения
        google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        
        if google_creds_json:
            try:
                creds_data = json.loads(google_creds_json)
                logging.info("Используются учетные данные Google из переменной окружения")
            except json.JSONDecodeError as e:
                logging.error(f"Ошибка парсинга GOOGLE_CREDENTIALS_JSON: {e}")
                raise
        else:
            # Если переменная окружения не установлена, пытаемся загрузить из файла
            try:
                with open('gcreds.json', 'r') as f:
                    creds_data = json.load(f)
                logging.info("Используются учетные данные Google из файла gcreds.json")
            except FileNotFoundError:
                logging.error("Файл gcreds.json не найден и GOOGLE_CREDENTIALS_JSON не установлена.")
                raise

        self.credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )

        self.service = build('sheets', 'v4', credentials=self.credentials)
        self.sheet = self.service.spreadsheets()

        self.spreadsheet_id = os.getenv('GOOGLE_SHEET_ID')
        if not self.spreadsheet_id or self.spreadsheet_id == 'your_spreadsheet_id_here':
            logging.warning("Переменная окружения GOOGLE_SHEET_ID не установлена или содержит значение по умолчанию. Логирование в Google Sheets будет ограничено.")
            raise ValueError("GOOGLE_SHEET_ID не установлен или неверен.")

        self.user_columns = {}
        logging.info(f"SheetsLogger инициализирован с spreadsheet_id: {self.spreadsheet_id}")

    def get_user_column(self, user_name, user_id):
        user_key = f"{user_name} (ID: {user_id})"

        if user_key in self.user_columns:
            return self.user_columns[user_key]

        try:
            result = self.sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Sheet1!1:1' # Явно указываем лист и строку
            ).execute()

            headers = result.get('values', [[]])[0] if result.get('values') else []

            for i, header in enumerate(headers):
                if header == user_key:
                    self.user_columns[user_key] = i
                    logging.info(f"Найден существующий столбец для пользователя '{user_key}' в позиции {i}")
                    return i

            new_column = len(headers)
            self.user_columns[user_key] = new_column

            column_letter = self._get_column_letter(new_column)
            self.sheet.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'Sheet1!{column_letter}1', # Явно указываем лист, столбец и строку
                valueInputOption='RAW',
                body={'values': [[user_key]]}
            ).execute()
            logging.info(f"Создан новый столбец '{user_key}' в позиции {new_column} ({column_letter})")

            return new_column

        except HttpError as e:
            logging.error(f"Ошибка Google Sheets API при получении/создании столбца для пользователя: {e.content}", exc_info=True)
            return 0
        except Exception as e:
            logging.error(f"Непредвиденная ошибка при получении/создании столбца для пользователя: {e}", exc_info=True)
            return 0

    def _get_column_letter(self, column_number):
        letter = ""
        while column_number >= 0:
            letter = chr(column_number % 26 + ord('A')) + letter
            column_number = column_number // 26 - 1
        return letter

    def log_message(self, user_name, user_id, message_text, is_user=True):
        """Логирует сообщение в Google Sheets в столбец пользователя"""
        max_retries = 3
        retry_delay = 1  # секунд
        
        for attempt in range(max_retries):
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                sender = "👤" if is_user else "🤖"

                column_num = self.get_user_column(user_name, user_id)
                column_letter = self._get_column_letter(column_num)

                formatted_message = f"{timestamp} {sender} {message_text}"

                result = self.sheet.values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'Sheet1!{column_letter}:{column_letter}' # Явно указываем лист и диапазон столбца
                ).execute()

                values = result.get('values', [])
                next_row = len(values) + 1

                self.sheet.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'Sheet1!{column_letter}{next_row}', # Явно указываем лист, столбец и строку
                    valueInputOption='RAW',
                    body={'values': [[formatted_message]]}
                ).execute()

                logging.info(f"Записано сообщение в столбец {column_letter} строку {next_row} для пользователя {user_name}")
                return  # Успешно записали, выходим

            except (AttributeError, ConnectionError, OSError) as e:
                # Ошибки соединения, включая 'NoneType' object has no attribute 'read'
                if attempt < max_retries - 1:
                    logging.warning(f"Ошибка соединения при записи в Google Sheets (попытка {attempt + 1}/{max_retries}): {e}. Повторяем через {retry_delay} сек...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Увеличиваем задержку
                    continue
                else:
                    logging.error(f"Не удалось записать в Google Sheets после {max_retries} попыток: {e}")
                    
            except HttpError as e:
                logging.error(f"Ошибка Google Sheets API при логировании сообщения: {e.content}", exc_info=True)
                break  # Не повторяем для API ошибок
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Непредвиденная ошибка при записи в Google Sheets (попытка {attempt + 1}/{max_retries}): {e}. Повторяем...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    logging.error(f"Непредвиденная ошибка при логировании в Google Sheets: {e}", exc_info=True)

    async def log_message_async(self, user_name, user_id, message_text, is_user=True):
        """Асинхронно логирует сообщение в Google Sheets в столбец пользователя"""
        def _log_sync():
            return self.log_message(user_name, user_id, message_text, is_user)
        
        # Запускаем синхронную операцию в отдельном потоке
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _log_sync)

    def create_headers_if_needed(self):
        try:
            result = self.sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Sheet1!1:1' # Явно указываем лист и строку
            ).execute()

            values = result.get('values', [])

            if not values or not values[0]:
                logging.info("Электронная таблица пуста. Столбцы будут созданы по мере того, как пользователи начнут общаться.")
            else:
                logging.info("Заголовки таблицы уже существуют.")
                for i, header in enumerate(values[0]):
                    match = re.match(r'(.+) \(ID: (\d+)\)', header)
                    if match:
                        user_key = header
                        self.user_columns[user_key] = i
                logging.info("Кэш user_columns заполнен существующими заголовками.")

        except HttpError as e:
            logging.error(f"Ошибка Google Sheets API при проверке заголовков: {e.content}", exc_info=True)
        except Exception as e:
            logging.error(f"Непредвиденная ошибка при проверке электронной таблицы: {e}", exc_info=True)