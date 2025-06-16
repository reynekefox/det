import os
import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class DocsLoader:
    def __init__(self):
        # Пытаемся получить учетные данные из переменной окружения
        google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        
        if google_creds_json:
            try:
                creds_data = json.loads(google_creds_json)
                logger.info("Используются учетные данные Google из переменной окружения")
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга GOOGLE_CREDENTIALS_JSON: {e}")
                raise
        else:
            # Если переменная окружения не установлена, пытаемся загрузить из файла
            try:
                with open('gcreds.json', 'r') as f:
                    creds_data = json.load(f)
                logger.info("Используются учетные данные Google из файла gcreds.json")
            except FileNotFoundError:
                logger.error("Файл gcreds.json не найден и GOOGLE_CREDENTIALS_JSON не установлена.")
                raise

        self.credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=['https://www.googleapis.com/auth/documents.readonly']
        )

        self.service = build('docs', 'v1', credentials=self.credentials) # !!! ИЗМЕНЕНО С 'v4' НА 'v1' !!!

        self.default_document_id = os.getenv('GOOGLE_DOC_ID')
        if not self.default_document_id or self.default_document_id == 'your_document_id_here':
            logger.warning("Переменная окружения GOOGLE_DOC_ID не установлена или содержит значение по умолчанию. Используйте актуальный ID документа.")
            raise ValueError("GOOGLE_DOC_ID не установлен или неверен.")

        logger.info(f"DocsLoader инициализирован. Основной document_id: {self.default_document_id}")

    def get_document_content(self, document_id: str = None):
        doc_id_to_fetch = document_id if document_id else self.default_document_id

        if not doc_id_to_fetch:
            logger.warning("Не указан ID документа для загрузки и default_document_id не установлен.")
            return self._get_default_prompt()

        try:
            document = self.service.documents().get(documentId=doc_id_to_fetch).execute()
            content = []
            for element in document.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    for text_element in paragraph.get('elements', []):
                        if 'textRun' in text_element:
                            content.append(text_element['textRun']['content'])

            full_text = ''.join(content).strip()
            if not full_text:
                logger.warning(f"Google Doc (ID: {doc_id_to_fetch}) пуст или не содержит текста.")
                return "" if document_id else self._get_default_prompt() # Возвращаем "" для пустых тематических доков

            logger.info(f"Успешно загружено содержимое документа (ID: {doc_id_to_fetch}): {len(full_text)} символов")
            return full_text

        except Exception as e:
            logger.error(f"Ошибка загрузки документа из Google Docs (ID: {doc_id_to_fetch}): {e}", exc_info=True)
            return "" if document_id else self._get_default_prompt()

    def _get_default_prompt(self):
        logger.warning("Используется системный промпт по умолчанию.")
        return """Я - ассистент, специализирующийся на воспитании детей.
Моя цель - помочь родителям справиться с трудностями, связанными с воспитанием, обучением, мотивацией, дисциплиной и другими вещами.
Я даю практические советы, объясняю техники и приемы воспитания, составляю планы и использую все свои знания, чтобы помощь родителям в общении с ребенком."""