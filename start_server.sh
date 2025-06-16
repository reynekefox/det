
#!/bin/bash
# Скрипт для запуска бота на сервере с правильными переменными окружения

BOT_DIR="/home/reynekefox/det"
cd "$BOT_DIR"

echo "🔄 Останавливаем существующий процесс бота..."
pkill -f "$BOT_DIR/main.py" 2>/dev/null || true
sleep 2

# Создаем виртуальное окружение если его нет
echo "🐍 Настраиваем виртуальное окружение..."
if [ ! -d "$BOT_DIR/venv" ]; then
    python3 -m venv "$BOT_DIR/venv"
    echo "✅ Виртуальное окружение создано"
fi

echo "📦 Устанавливаем зависимости..."
source "$BOT_DIR/venv/bin/activate"
if [ -f "$BOT_DIR/requirements.txt" ]; then
    pip install -r "$BOT_DIR/requirements.txt" --upgrade
    echo "✅ Зависимости установлены из requirements.txt"
else
    echo "⚠️ Файл requirements.txt не найден, устанавливаем основные пакеты..."
    pip install aiogram google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib python-dotenv requests Flask --upgrade
fi

echo "🔧 Настраиваем переменные окружения..."
# Проверяем наличие файла с учетными данными
if [ ! -f "$BOT_DIR/gcreds.json" ]; then
    echo "❌ ОШИБКА: Файл gcreds.json не найден в $BOT_DIR"
    exit 1
fi

# Создаем скрипт запуска с переменными окружения и виртуальным окружением
cat > "$BOT_DIR/run_bot.sh" << 'EOF'
#!/bin/bash
cd /home/reynekefox/det
source /home/reynekefox/det/venv/bin/activate
export GOOGLE_CREDENTIALS_JSON=\$(cat /home/reynekefox/det/gcreds.json)
exec python /home/reynekefox/det/main.py
EOF

chmod +x "$BOT_DIR/run_bot.sh"
echo "✅ Скрипт запуска создан с переменными окружения"

echo "🚀 Запускаем бота..."
nohup "$BOT_DIR/run_bot.sh" > "$BOT_DIR/bot.log" 2>&1 &
BOT_PID=$!

echo "✅ Бот запущен с PID: $BOT_PID"
echo "📋 Для проверки логов используйте: tail -f $BOT_DIR/bot.log"

# Проверяем, что процесс запустился
sleep 3
if ps -p $BOT_PID > /dev/null 2>&1; then
    echo "🎉 Бот успешно работает!"
else
    echo "⚠️ Возможная проблема с запуском. Последние строки лога:"
    tail -10 "$BOT_DIR/bot.log"
fi
