
#!/bin/bash

# Скрипт для запуска бота с автоматическим перезапуском при падении
BOT_DIR="/home/reynekefox/det"
LOG_FILE="$BOT_DIR/bot_restart.log"
MAX_RESTARTS=10
RESTART_DELAY=5

cd "$BOT_DIR"

echo "🚀 Запуск бота с автоматическим перезапуском..." | tee -a "$LOG_FILE"
echo "📁 Рабочая директория: $BOT_DIR" | tee -a "$LOG_FILE"
echo "📝 Лог перезапусков: $LOG_FILE" | tee -a "$LOG_FILE"

# Активируем виртуальное окружение
source "$BOT_DIR/venv/bin/activate"

# Устанавливаем переменную окружения для Google Sheets
export GOOGLE_APPLICATION_CREDENTIALS="$BOT_DIR/gcreds.json"

restart_count=0

while [ $restart_count -lt $MAX_RESTARTS ]; do
    echo "$(date): Запуск бота (попытка $((restart_count + 1)))" | tee -a "$LOG_FILE"
    
    # Запускаем бота
    python "$BOT_DIR/main.py"
    
    exit_code=$?
    restart_count=$((restart_count + 1))
    
    echo "$(date): Бот завершился с кодом $exit_code" | tee -a "$LOG_FILE"
    
    if [ $exit_code -eq 0 ]; then
        echo "$(date): Бот завершился нормально" | tee -a "$LOG_FILE"
        break
    fi
    
    if [ $restart_count -lt $MAX_RESTARTS ]; then
        echo "$(date): Перезапуск через $RESTART_DELAY секунд..." | tee -a "$LOG_FILE"
        sleep $RESTART_DELAY
    else
        echo "$(date): Достигнуто максимальное количество перезапусков ($MAX_RESTARTS)" | tee -a "$LOG_FILE"
        break
    fi
done

echo "$(date): Скрипт завершен" | tee -a "$LOG_FILE"
